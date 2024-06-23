from datetime import datetime, timedelta
import os
import pdfplumber
import pprint
import re
import sqlite3

# Coordinates: (x-left, y-top, x-right, y-bottom)
METADATA_COORDINATES = (212, 41, 500, 115)
ROAD_NAME_COORDINATES = (13, 216, 400, 233)
VID_DATA_COORDINATES = (13, 233, 400, 745)

VID_VERTICAL_LINES = [20, 36, 50, 68, 219, 297, 360, 385]
METADATA_VERTICAL_LINES = [212, 430, 500]


def define_page_type(page):
    text = page.extract_text()
    if "Total in this roadgroup" in text:
        return "cover_sheet"
    elif "Doorstep Briefing Sheet" in text:
        return "briefing_sheet"
    elif "Voter id" in text:
        return "vid_sheet"
    else:
        return "other"


def extract_road_name(page):
    area = page.crop(ROAD_NAME_COORDINATES)
    return area.extract_text().title()


def extract_metadata(page):
    area = page.crop(METADATA_COORDINATES)
    text = area.extract_text().split("\n")
    ward = re.findall(
        r"\: (.*)",
        text[1],
    )[0].title()
    road_group = re.findall(
        r"\: (.*)",
        text[2],
    )[0]
    if "0E1lm5E DXrive" in text[4]:
        polling_district = "OE15X"
    else:
        try:
            polling_district = re.findall(
                r"\: (.*)",
                text[3],
            )[0].split(
                " "
            )[0]
        except IndexError:
            polling_district = text[4]
            polling_district = re.sub(r"[a-z]", "", polling_district).split(" ")[0]
            if polling_district in ["0G15AH", "0C15AH"]:
                polling_district = "015AH"
            if polling_district == "0N15AI":
                polling_district = "015AI"
            if polling_district in ["0R15AM", "0L15AM", "0W15A", "0G15A"]:
                polling_district = "015AM"
            if polling_district in ["0E15E"]:
                polling_district = "015ED"
    return ward, road_group, polling_district


def add_missing_space_before_road_name(line, road_name):
    if road_name.lower() not in line.lower():
        return line
    index = line.lower().find(road_name.lower())
    if line[index - 1] == " ":
        return line
    else:
        return line[:index] + " " + line[index:]


def fetch_vid(line, elector_number, name, vid_text):
    if line[5] == "-":
        return "", ""
    if "LIBERAL DEM" in line[5]:
        last_vid = "Liberal Democrat"
    elif "DON'T KNOW" in line[5]:
        last_vid = "Don't know"
    else:
        last_vid = line[5].title()
    try:
        last_vid_date = datetime.strptime(line[6], "%d/%m/%y")
    except (IndexError, ValueError):
        for line in vid_text:
            if elector_number not in line or name not in line:
                continue
            if "LIBERAL DEM" in line:
                index = line.find("LIBERAL DEM")
                date_string = line[index:]
                date = re.sub(r"[A-Z]", "", date_string).strip()
            else:
                date = re.findall(r"\d{1,2}\/\d{1,2}\/\d{2}", line)[0]
            last_vid_date = datetime.strptime(date, "%d/%m/%y")
    return last_vid, last_vid_date


def fetch_missing_elector_number(name, vid_text):
    for index, string in enumerate(vid_text):
        if name in string:
            print(f"Found errant eletor number {vid_text[index+1]}")
            return vid_text[index + 1]


def extract_voters(page, road_name):
    voters, two_line_elector = [], False
    area = page.crop(VID_DATA_COORDINATES)
    table = area.extract_table(
        table_settings={
            "horizontal_strategy": "text",
            "vertical_strategy": "explicit",
            "explicit_vertical_lines": VID_VERTICAL_LINES,
        }
    )
    vid_text = area.extract_text().split("\n")
    if not table:
        return None
    for line in table:
        if not line or len(line) == 0:
            continue
        if line[1] == "" and line[3] == "" and line[5] == "":
            continue
        # print(f"Current voter: {current_voter}")

        # Found house number
        if line[0]:
            property_voters, current_voter = [], {}
            property_number = line[0]
        # Found elector number
        if line[1]:
            if current_voter and not two_line_elector:
                property_voters.append(current_voter)
                current_voter = {}
            if re.search(r"/$", f"{line[1]}{line[2]}"):
                two_line_elector = True
            elif current_voter and two_line_elector:
                current_voter["elector_number"] += line[1]
                current_voter["elector_number"] += line[2]
                two_line_elector = False
                continue
            current_voter["elector_number"] = line[1] + line[2]
            current_voter["name"] = line[3]
            current_voter["selection_id"] = line[4]
            current_voter["last_vid"], current_voter["last_vid_date"] = fetch_vid(
                line,
                current_voter["elector_number"],
                current_voter["name"],
                vid_text,
            )
        else:
            line = "".join(line)
            # Found date of majority
            if "DOM:" in line:
                # Probably won't work in Scotland lol
                date_of_majority = datetime.strptime(line.split()[1], "%d/%m/%Y")
                current_voter["date_of_birth"] = date_of_majority - timedelta(days=6570)
            # Found note
            elif "§" in line:
                if "Member" in line:
                    current_voter["is_member"] = True
                else:
                    current_voter["note"] = line.replace("§", "").strip()
            # Found address
            elif "Current Postal Voter" in line:
                current_voter["has_postal"] = True
            elif "POSTER" in line:
                pass
            elif "Lab Scale:" in line:
                current_voter["last_vid_labour_scale"] = re.findall(
                    r"Lab Scale\: *(\d+)", line
                )[0]

            elif "," in line:
                property_voters.append(current_voter)
                line = add_missing_space_before_road_name(line, road_name)
                address = line.split(",")
                address = address[0:-1]
                for index, text in enumerate(address[0:-1]):
                    address[index] = text.title()
                address = ",".join(address)
                for voter in property_voters:
                    voter["property_number"] = property_number
                    voter["address"] = address
                    voter["road_name"] = road_name
                voters = voters + property_voters
    return voters


def duplicate_check(voters_tuples):

    tracker, duplicates = {}, []
    for voter in voters_tuples:
        polling_district = voter[0]
        elector_number = voter[1]
        key = (polling_district, elector_number)
        if key in tracker:
            duplicates.append(voter)
        else:
            tracker[key] = voter
    if duplicates:
        print("Found duplicate voters:")
        for duplicate in duplicates:
            print(duplicate)
    else:
        print("No duplicates found")
    return


def load_pdf(filename):
    print(f"Opening file: {filename}")
    with pdfplumber.open(filename) as file:
        all_voters = []
        for index, page in enumerate(file.pages):
            page_type = define_page_type(page)
            if page_type == "vid_sheet":
                road_name = extract_road_name(page)
                ward, road_group, polling_district = extract_metadata(page)
                voters = extract_voters(page, road_name)
                if not voters:
                    continue
                for voter in voters:
                    voter["ward"] = ward
                    voter["road_group"] = road_group
                    voter["polling_district"] = polling_district
                    voter["road_name"] = road_name
                # pprint.pprint(voters)
                all_voters += voters
                print(f"Found {len(voters)} voters on page {index+1}")
            else:
                continue
        return all_voters


def split_vids(voters):
    vids = []
    for voter in voters:
        if not voter["last_vid"]:
            continue
        vid = {
            "elector_id": voter["polling_district"] + voter["elector_number"],
            "vid": voter["last_vid"],
            "vid_labour_scale": voter["last_vid_labour_scale"],
            "vid_date": voter["last_vid_date"],
        }
        vids.append(vid)
    return vids


def adapt_time_object(time_object):
    # https://stackoverflow.com/questions/27640857/best-way-to-store-python-datetime-time-in-a-sqlite3-column
    return datetime.strftime(time_object, "%Y-%m-%d")


def write_voter_data(all_voters, cursor):
    connection = sqlite3.connect("voter_data.db")
    cursor = connection.cursor()
    create_query = """
        CREATE TABLE voters (
            polling_district TEXT,
            elector_number TEXT,
            name TEXT,
            property_number TEXT,
            address TEXT,
            selection_id TEXT,
            is_member INTEGER,
            has_postal INTEGER
            note TEXT,
            PRIMARY KEY (polling_district, elector_number)
        )
    """
    cursor.execute(create_query)
    insert_query = """
        INSERT INTO voters
        (
            polling_district, 
            elector_number, 
            name, 
            property_number,
            address, 
            selection_id, 
            last_vid, 
            last_vid_labour_scale,
            last_vid_date, 
            is_member, 
            has_postal,
            note
        )
        VALUES 
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
    voters_tuples = []
    for voter in all_voters:
        voter_tuple = (
            voter.get("polling_district", ""),
            voter.get("elector_number", ""),
            voter.get("name", ""),
            voter.get("property_number", ""),
            voter.get("address", ""),
            voter.get("selection_id", ""),
            voter.get("is_member", ""),
            voter.get("has_postal", ""),
            voter.get("note", ""),
        )
        voters_tuples = voters_tuples + [voter_tuple]

    duplicate_check(voters_tuples)
    cursor.executemany(insert_query, voters_tuples)
    connection.commit()
    return


def write_vid_data(vids, cursor):
    cursor.execute(
        """
        CREATE TABLE vids (
            elector_id TEXT,
            voter_intention TEXT,
            labour_scale TEXT,
            date TEXT,
            PRIMARY KEY (polling_district, elector_number)
        )
        """
    )
    insert_query = """
        INSERT INTO vids
        (elector_id, voter_intention, labour_scale, date)
        VALUES 
        (?, ?, ?, ?)
        """
    tuples = []
    for vid in vids:
        vid_tuple = (
            vid.get("elector_id", ""),
            vid.get("voter_intention", ""),
            vid.get("labour_scale", ""),
            vid.get("date", ""),
        )
        tuples += [vid_tuple]
    cursor.executemany(insert_query, tuples)
    connection.commit()
    return


all_voters = []
for file in os.listdir("input"):
    filename = os.fsdecode(file)
    if filename.endswith(".pdf"):
        all_voters += load_pdf("input/" + filename)
vids = split_vids(all_voters)

connection = sqlite3.connect("voter_data.db")
cursor = connection.cursor()
sqlite3.register_adapter(datetime.time, adapt_time_object)
write_voter_data(all_voters, cursor)
write_vid_data(vids, cursor)

print(f"All {len(all_voters)} voters scraped")
