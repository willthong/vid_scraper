from datetime import datetime
from fpdf import FPDF
from fpdf.table import TableSpan, FontFace
import os
import pprint
import pypdf
import re
import sqlite3
from data_functions import fetch_wards, fetch_road_groups


# Find list of PDFs, pulled from database (it'll print every road group in that PD)

# TODO: Selection options with numbers of voters in the selection


def dictionary_factory(cursor, row):
    dictionary = {}
    for index, column in enumerate(cursor.description):
        dictionary[column[0]] = row[index]
    return dictionary


class PDF(FPDF):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header_data = {
            "ward": "",
            "road": "",
            "road_group": "",
            "polling_district": "",
            "road": "",
        }

    def header(self):

        # Fonts
        self.add_font(
            "open-sans",
            style="",
            fname="fonts/OpenSans-Regular.ttf",
        )
        self.add_font(
            "segoe-ui-emoji",
            fname="fonts/SegoeUIEmoji.ttf",
        )

        page_data = (
            ("Constituency", "Huntingdon"),
            ("Ward", self.header_data["ward"]),
            ("Polling district", self.header_data["polling_district"]),
            ("Road group", self.header_data["road_group"]),
            ("Polling place", self.header_data["polling_station"]),
            ("Road", self.header_data["road"]),
        )

        # Title
        self.set_font("open-sans", "B", 20)
        self.set_xy(5, 5)
        self.cell(text="(Unauthorised) Voter ID")

        # Left table
        self.set_xy(5, 15)
        self.set_font("open-sans", "", 9)
        with self.table(
            width=100,
            col_widths=(23, 70),
            align="LEFT",
            first_row_as_headings=False,
            borders_layout="None",
            line_height=5,
        ) as table:
            for data_row in page_data[:3]:
                row = table.row()
                for datum in data_row:
                    row.cell(datum)

        # Middle table
        self.set_xy(60, 15)
        self.set_font("open-sans", "", 9)
        with self.table(
            width=150,
            col_widths=(23, 127),
            align="LEFT",
            first_row_as_headings=False,
            borders_layout="None",
            line_height=5,
        ) as table:
            for data_row in page_data[3:]:
                row = table.row()
                for datum in data_row:
                    row.cell(datum)

        question_data = (
            (
                "A",
                "Voting intention",
            ),
            (
                "B",
                "1-10 Labour likelihood?",
            ),
            ("C", "Wouldn't vote for?"),
        )

        # Right table
        self.set_xy(155, 15)
        self.set_font("open-sans", "", 9)
        with self.table(
            width=100,
            col_widths=(4, 70),
            align="LEFT",
            first_row_as_headings=False,
            borders_layout="None",
            line_height=5,
        ) as table:
            for data_row in question_data:
                row = table.row()
                for datum in data_row:
                    row.cell(datum)

    def footer(self):
        # Date
        self.set_font("open-sans", "", 7)
        self.set_xy(5, 290)
        self.cell(text=f"{datetime.today().strftime('%d/%m/%Y')}", align="R")

        # Imprint
        self.set_xy(61, 290)
        self.cell(
            text="Printed and promoted by R Jewell, 10A The Highway, Gt Staughton, PE19 5DA",
            align="C",
        )

        # VID lines
        self.line(159, 38, 159, 286)
        self.line(169, 38, 169, 286)
        self.line(179, 38, 179, 286)
        self.line(189, 38, 189, 286)


class NumberPDF(FPDF):
    def __init__(self, number_of_pages):
        super(NumberPDF, self).__init__()
        self.number_of_pages = number_of_pages

    def footer(self):

        self.add_font(
            "open-sans",
            style="",
            fname="fonts/OpenSans-Regular.ttf",
        )
        self.set_xy(198, 290)
        self.set_font("open-sans", "", 7)
        self.cell(text=f"{self.page_no()}/{self.number_of_pages}", align="L")


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
    if voter["last_vid"] == "Ukip/Brexit":
        return "Reform"
    if voter["last_vid"] == "Conservative":
        return "Tory"
    elif voter["last_vid"] == "Liberal Democrat":
        return "LibDem"
    elif voter["last_vid"] == "Don't know":
        return f"Dunno {voter.get('labour_scale', '')}"
    else:
        return voter["last_vid"]


def add_note_to_name(voter):
    name = voter["name"]
    if voter["note"] and not voter["date_of_birth"]:
        note = voter["note"]
        return f"{name} ({note})"
    else:
        age = (
            datetime.today()
            - datetime.strptime(voter["date_of_birth"], "%Y-%m-%d %H:%M:%S")
        ).days / 365.25
        if not voter["note"]:
            return f"{name} ({age:.0f})"
        else:
            note = voter["note"]
            return f"{name} ({age:.0f}; {note})"


def fetch_voter_data(selected_ward, selected_road_group):
    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()
    cursor.row_factory = dictionary_factory
    query = f"""
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
            date_of_birth,
            note,
            voters.polling_district,
            polling_districts.polling_station as polling_station
        FROM voters 
        INNER JOIN roads ON roads.road_id = voters.road_id 
        INNER JOIN road_groups ON roads.road_group_id = road_groups.road_group_id 
        INNER JOIN polling_districts ON road_groups.polling_district_id = polling_districts.polling_district_id
        LEFT JOIN vids ON (vids.polling_district + vids.elector_number) = (voters.polling_district + voters.elector_number)
        AND vids.date = (
            SELECT MAX(vids_inner.date)
            from vids AS vids_inner
            WHERE (vids_inner.polling_district + vids_inner.elector_number) = (voters.polling_district + voters.elector_number)
        )
        WHERE polling_districts.ward = '{selected_ward}'
        """
    if selected_road_group:
        query += f"""
            AND 
                road_group = '{selected_road_group}' 
        """
    query += """
        ORDER BY
            road_group,
            road,
            voters.elector_number
        """
    data = cursor.execute(query).fetchall()
    return data


def split_into_houses(road_voters):
    this_property, output_road_voters = [], []
    for voter in road_voters:
        if len(this_property) == 0:
            this_property += [voter]
        elif voter["address"] == this_property[0]["address"]:
            this_property += [voter]
        else:
            output_road_voters += [this_property]
            this_property = [voter]
    if this_property:
        output_road_voters += [this_property]
    return output_road_voters


def print_cover_sheet(cover_sheet, selected_ward, road_group, a_voter):
    pdf = PDF()
    pdf.add_font(
        "open-sans",
        style="B",
        fname="fonts/OpenSans-Bold.ttf",
    )
    pdf.set_margins(0.5, 100, 10)
    pdf.b_margin = pdf.b_margin / 2
    # Update header
    pdf.header_data = {
        "ward": selected_ward,
        "road": "(Cover sheet)",
        "road_group": road_group,
        "polling_district": a_voter["polling_district"],
        "polling_station": a_voter["polling_station"],
    }
    pdf.add_page()
    pdf.set_font("open-sans", "", 12)
    pdf.set_fallback_fonts(["segoe-ui-emoji"], exact_match=False)

    table_data = (("Road", "Properties", "Voters"),)
    for road in cover_sheet:
        # Address line
        table_data += (
            (
                road["road_name"],
                str(road["property_count"]),
                str(road["voter_count"]),
            ),
        )
    table_data += (
        (
            "Total",
            str(sum([road["property_count"] for road in cover_sheet])),
            str(sum([road["voter_count"] for road in cover_sheet])),
        ),
    )

    pdf.set_xy(5, 35)
    pdf.set_line_width(0.1)
    with pdf.table(
        width=140,
        col_widths=(70, 30, 30),
        align="LEFT",
        text_align="LEFT",
        first_row_as_headings=True,
        borders_layout="NONE",
        line_height=8,
        padding=0,
    ) as table:
        shaded = False
        for data_row in table_data:
            if shaded:
                shaded = False
            else:
                shaded = True
            shaded_row = FontFace(fill_color=(220, 220, 220))
            unshaded_row = FontFace(fill_color=(255, 255, 255))
            if shaded:
                row = table.row(style=shaded_row)
            else:
                row = table.row(style=unshaded_row)
            for datum in data_row:
                row.cell(datum)

    pdf.output(f"output_cover_{road_group}.pdf")
    return f"output_cover_{road_group}.pdf"


def print_road(road_voters, selected_ward):
    pdf = PDF()
    pdf.add_font(
        "open-sans",
        style="B",
        fname="fonts/OpenSans-Bold.ttf",
    )
    # pdf.r_margin = pdf.r_margin / 100000
    pdf.set_margins(0.5, 100, 10)
    pdf.b_margin = pdf.b_margin / 2
    # Update header
    pdf.header_data = {
        "ward": selected_ward,
        "road": road_voters[0][0]["road"],
        "road_group": road_voters[0][0]["road_group"],
        "polling_district": road_voters[0][0]["polling_district"],
        "polling_station": road_voters[0][0]["polling_station"],
    }
    pdf.add_page()
    pdf.set_font("open-sans", "", 9)
    pdf.set_fallback_fonts(["segoe-ui-emoji"], exact_match=False)

    table_data = [
        (
            "",
            "Name",
            "Selection",
            "Last VID",
            TableSpan.COL,
            "💌",
            "🌹",
            "A",
            "B",
            "C",
            "No",
        ),
    ]
    for property_group in road_voters:
        # Address line
        table_data += [
            (
                property_group[0]["address"],
                TableSpan.COL,
                TableSpan.COL,
                TableSpan.COL,
                TableSpan.COL,
                TableSpan.COL,
                TableSpan.COL,
                TableSpan.COL,
                TableSpan.COL,
                TableSpan.COL,
                TableSpan.COL,
            )
        ]
        for voter in property_group:
            voter_tuple = (
                voter["property_number"],
                (
                    voter["name"]
                    if not voter["date_of_birth"] and not voter["note"]
                    else add_note_to_name(voter)
                ),
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

    pdf.set_xy(5, 30)
    pdf.set_line_width(0.1)
    with pdf.table(
        col_widths=(5, 23, 10, 7, 8, 4, 4, 4, 4, 4, 5),
        align="LEFT",
        text_align="LEFT",
        first_row_as_headings=True,
        borders_layout="HORIZONTAL_LINES",
        line_height=8,
        padding=0,
    ) as table:
        shaded = False
        for data_row in table_data:
            if data_row[1] == TableSpan.COL:
                if shaded:
                    shaded = False
                else:
                    shaded = True
            shaded_row = FontFace(fill_color=(220, 220, 220))
            unshaded_row = FontFace(fill_color=(255, 255, 255))
            if shaded:
                row = table.row(style=shaded_row)
            else:
                row = table.row(style=unshaded_row)
            for datum in data_row:
                row.cell(datum)

    pdf.output(f"output_{road_voters[0][0]['road']}.pdf")
    return f"output_{road_voters[0][0]['road']}.pdf"


def merge_pdfs(generated_files):
    merger = pypdf.PdfMerger()
    for pdf in generated_files:
        merger.append(pdf)
        os.remove(pdf)
    merger.write("output_unnumbered.pdf")
    merger.close()
    return


def number_pdf(input_file_location, output_file_location):
    print("Numbering PDF...")
    input_file = pypdf.PdfReader(input_file_location)
    temp_number_file = NumberPDF(len(input_file.pages))
    for page in range(len(input_file.pages)):
        temp_number_file.add_page()
    temp_number_file.output("temp_numbering.pdf")
    merge_file = pypdf.PdfReader("temp_numbering.pdf")
    merge_writer = pypdf.PdfWriter()
    for page_index, page in enumerate(merge_file.pages):
        input_page = input_file.pages[page_index]
        input_page.merge_page(page)
        merge_writer.add_page(input_page)
    os.remove("temp_numbering.pdf")
    with open(output_file_location, "wb") as file:
        merge_writer.write(file)
    os.remove(input_file_location)


def generate_polling_district():
    wards = fetch_wards()
    while True:
        print("Wards in this constituency:")
        for index, ward in enumerate(wards):
            print(f"{index + 1}) {ward[0]}")
        try:
            selected_ward_id = input("\nSelect one of the above wards by number:")
            selected_ward_id = int(selected_ward_id.replace(")", "")) - 1
        except ValueError:
            print("Sorry - you need to enter a number.")
            continue
        if selected_ward_id < 0 or selected_ward_id > len(wards) - 1:
            print("Please select a valid ward number from the list.\n")
        else:
            break
    selected_ward = wards[selected_ward_id][0]
    print(f"You selected {selected_ward}.")
    road_groups = fetch_road_groups(selected_ward)
    while True:
        print("Road groups in :")
        for index, road_group in enumerate(road_groups):
            print(f"{index + 1}) {road_groups[index][0]}")
        try:
            selected_road_group_id = input(
                "Which road group would you like to output? Or leave blank to output all road groups."
            )
            if selected_road_group_id == "":
                break
            selected_road_group_id = int(selected_road_group_id.replace(")", "")) - 1
        except ValueError:
            print("Sorry - you need to enter a number.")
            continue
        if selected_road_group_id < 0 or selected_road_group_id > len(road_groups) - 1:
            print("Please make a valid selection.\n")
        else:
            break
    selected_road_group = (
        road_groups[selected_road_group_id][0] if selected_road_group_id else None
    )
    if selected_road_group:
        print(f"You selected {selected_road_group}.\n")
    else:
        print("You selected all road groups.\n")
    while True:
        selected_output = input(
            "Would you like (V)ID sheets, (W)ARP sheets or (C)SV output?"
        )
        selected_output = selected_output.lower()
        if selected_output not in ["v", "w", "c"]:
            print("Please type V, W or C")
            continue
        else:
            break

    data = fetch_voter_data(selected_ward, selected_road_group)

    # Put it into the polling_district table
    road_groups = sorted(set([voter["road_group"] for voter in data]))
    all_pdfs, vid_sheet_pdfs = [], []

    for road_group_index, road_group in enumerate(road_groups):
        cover_sheet = []
        roads = sorted(
            set([voter["road"] for voter in data if voter["road_group"] == road_group])
        )
        # Generate cover sheet

        for road in roads:

            road_voters = [voter for voter in data if voter["road"] == road]
            this_road_counts = {"road_name": road}
            this_road_counts["voter_count"] = len(road_voters)
            road_voters = order_road_voters(road_voters)
            road_voters = split_into_houses(road_voters)
            this_road_counts["property_count"] = len(road_voters)
            print(this_road_counts)
            cover_sheet += [this_road_counts]
            print(
                f"Printing road group {road_voters[0][0]['road_group']} ({road_group_index+1} of {len(road_groups)})"
            )

            file_name = print_road(road_voters, selected_ward)
            vid_sheet_pdfs += [file_name]

        file_name = print_cover_sheet(
            cover_sheet, selected_ward, road_group, road_voters[0][0]
        )
        all_pdfs += [file_name]
        all_pdfs += [pdf for pdf in vid_sheet_pdfs]

    merge_pdfs(all_pdfs)

    if not selected_road_group:
        output_filename = selected_ward.lower().replace(" ", "_") + ".pdf"
    else:
        output_filename = (
            selected_ward.lower().replace(" ", "_")
            + "_"
            + selected_road_group.lower().replace(" ", "_")
            + ".pdf"
        )
    number_pdf("output_unnumbered.pdf", output_filename)
    print(f"Successfully exported as {output_filename}")


if __name__ == "__main__":
    generate_polling_district()
