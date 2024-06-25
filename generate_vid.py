from datetime import datetime
from fpdf import FPDF
import pprint
import re
import sqlite3

# Find list of PDs, pulled from database (it'll print every road group in that PD)

# Selection options with numbers of voters in the selection

# Default: all PDs
polling_district = "015AD"


def dictionary_factory(cursor, row):
    dictionary = {}
    for index, column in enumerate(cursor.description):
        dictionary[column[0]] = row[index]
    return dictionary


class PDF(FPDF):
    def header(self):

        # Fonts
        self.add_font(
            "open-sans",
            style="",
            fname="fonts/OpenSans-Regular.ttf",
        )

        # Data
        connection = sqlite3.connect(
            "voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES
        )
        cursor = connection.cursor()
        cursor.row_factory = dictionary_factory
        data = cursor.execute(
            """
            SELECT ward, road_group_name, voters.polling_district FROM voters 
            INNER JOIN roads ON roads.road_id = voters.road_id 
            INNER JOIN road_groups ON roads.road_group_id = road_groups.road_group_id 
            WHERE road_groups.polling_district = '015AD'
            LIMIT 1
            """
        ).fetchone()

        page_data = (
            ("Constituency", "Huntingdon"),
            ("Ward", data["ward"]),
            ("Road group", data["road_group_name"]),
            ("Polling district", data["polling_district"]),
            ("Polling place", "Ugh Will hasn't built this yet"),
        )

        # Title
        self.set_font("open-sans", "B", 20)
        self.set_xy(5, 5)
        self.cell(text="(Unauthorised) Voter ID")

        # Left header
        self.set_xy(5, 15)
        self.set_font("open-sans", "", 9)
        with pdf.table(
            width=100,
            col_widths=(30, 70),
            align="LEFT",
            first_row_as_headings=False,
            borders_layout="None",
            line_height=5,
        ) as table:
            for data_row in page_data:
                row = table.row()
                for datum in data_row:
                    row.cell(datum)

        question_data = (
            (
                "Question A",
                "Are you planning to vote in the General Election? Who will you be voting for?",
            ),
            (
                "Question B",
                "On a scale of 1-10, how likely would you be to vote Labour?",
            ),
            ("Question C", "Is there anyone you definitely wouldn't vote for?"),
        )

        # Left header
        self.set_xy(100, 15)
        self.set_font("open-sans", "", 9)
        with pdf.table(
            width=100,
            col_widths=(16, 70),
            align="LEFT",
            first_row_as_headings=False,
            borders_layout="None",
            line_height=5,
        ) as table:
            for data_row in question_data:
                row = table.row()
                for datum in data_row:
                    row.cell(datum)


pdf = PDF()

connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
cursor = connection.cursor()
cursor.row_factory = dictionary_factory
data = cursor.execute(
    """
    SELECT 
        road_group_name as road_group, 
        voter_name as name, 
        address, 
        road_name as road,
        voters.elector_number,
        property_number,
        selection_id,
        vids.voter_intention as last_vid,
        vids.labour_scale as last_labour_scale,
        vids.date as last_vid_date,
        is_member,
        has_postal,
        date_of_birth
    FROM voters 
    INNER JOIN roads ON roads.road_id = voters.road_id 
    INNER JOIN road_groups ON roads.road_group_id = road_groups.road_group_id 
    LEFT JOIN vids ON (vids.polling_district + vids.elector_number) = (voters.polling_district + voters.elector_number)
    AND vids.date = (
        SELECT MIN(vids_inner.date)
        from vids AS vids_inner
        WHERE (vids_inner.polling_district + vids_inner.elector_number) = (voters.polling_district + voters.elector_number)
    )
    WHERE road_groups.polling_district = '015AD'
    ORDER BY
        road_group,
        road,
        voters.elector_number
    """
).fetchall()


def order_road_voters(properties: list):
    no_number_properties = [
        voter for voter in properties if not voter["property_number"]
    ]
    numbered_properties = [voter for voter in properties if voter["property_number"]]
    if numbered_properties:
        for property in numbered_properties:
            property["property_just_numbers"] = "".join(
                re.findall(r"\d*", property["property_number"])
            )
            property["property_text"] = "".join(
                re.findall(r"[a-z][A-Z]*", property["property_number"])
            )
        numbered_properties.sort(key=lambda x: x.get("property_text", ""))
        numbered_properties.sort(key=lambda x: int(x.get("property_just_numbers", 0)))
    if no_number_properties:
        no_number_properties.sort(key=lambda x: x["address"])
    if not numbered_properties:
        properties = no_number_properties
    elif not no_number_properties:
        properties = numbered_properties
    else:
        properties = no_number_properties + numbered_properties
    return properties


def extract_vid(voter):
    if voter["last_vid"] == "Conservative":
        return "Tory"
    elif voter["last_vid"] == "Liberal Democrat":
        return "LibDem"
    elif voter["last_vid"] == "Don't know":
        return f"Dunno {voter.get('labour_scale', '')}"
    else:
        return voter["last_vid"]


def add_age_to_name(voter):
    name = voter["name"]
    age = (
        datetime.today()
        - datetime.strptime(voter["date_of_birth"], "%Y-%m-%d %H:%M:%S")
    ).days / 365.25
    return f"{name} ({age:.0f})"


road_groups = sorted(set([voter["road_group"] for voter in data]))

pdf.add_font(
    "open-sans",
    style="B",
    fname="fonts/OpenSans-Bold.ttf",
)

for road_group in road_groups:
    roads = sorted(set([voter["road"] for voter in data]))
    pdf.r_margin = pdf.r_margin / 10
    pdf.add_page()
    for road in roads:
        road_voters = [voter for voter in data if voter["road"] == road]
        road_voters = order_road_voters(road_voters)

        # Print heading
        pdf.set_font("open-sans", "B", 9)
        pdf.set_xy(5, 45)
        pdf.cell(text=road_voters[0]["road"])
        pdf.add_page()

        pdf.add_font(
            "segoe-ui-emoji",
            fname="fonts/SegoeUIEmoji.ttf",
        )
        pdf.set_font("open-sans", "", 9)
        pdf.set_fallback_fonts(["segoe-ui-emoji"], exact_match=False)

        table_data = [
            (
                "",
                "Name",
                "Selection",
                "Last VID",
                "",
                "💌",
                "🌹",
                "A",
                "B",
                "C",
                "No",
            ),
        ]
        for voter in road_voters:
            voter_tuple = (
                voter["property_number"],
                voter["name"] if not voter["date_of_birth"] else add_age_to_name(voter),
                voter["selection_id"],
                extract_vid(voter),
                (
                    ""
                    if not voter["last_vid_date"]
                    else datetime.strftime(
                        datetime.strptime(voter["last_vid_date"], "%Y-%m-%d %H:%M:%S"),
                        "%d/%m/%Y",
                    )
                ),
                "💌" if voter["has_postal"] == 1 else "",
                "🌹" if voter["is_member"] == 1 else "",
                "",
                "",
                "",
                voter["elector_number"],
            )
            table_data.append(voter_tuple)

        pdf.set_xy(5, 50)
        pdf.set_line_width(0.1)
        with pdf.table(
            col_widths=(5, 23, 10, 6, 8, 4, 4, 4, 4, 4, 5),
            align="LEFT",
            text_align="LEFT",
            first_row_as_headings=True,
            borders_layout="HORIZONTAL_LINES",
            line_height=8,
            padding=0,
        ) as table:
            for row_index, data_row in enumerate(table_data):
                row = table.row()
                for col_index, datum in enumerate(data_row):
                    row.cell(datum)


pdf.output("output.pdf")

# #TODO Addresses
# #TODO For each street:
# #TODO Start a new page

# Printed and promoted by R Jewell, 10A The Highway, Gt Staughton, PE19 5DA
