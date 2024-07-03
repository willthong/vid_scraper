from datetime import datetime, timedelta
from enum import Enum
import os
import re
import sqlite3
from typing import List, Optional
from typing_extensions import Annotated

from kontakt_kreator.autocomplete import complete_road_groups
from kontakt_kreator.callbacks import ward_callback, road_group_callback
from kontakt_kreator.data_functions import fetch_voter_data

from fpdf import FPDF
from fpdf.table import TableSpan, FontFace
import pypdf
from rich import print
from rich.progress import Console
import typer

app = typer.Typer()
console = Console()
connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)

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
        if self.board_type == "vid":
            self.cell(text="(Unauthorised) Voter ID")
        elif self.board_type == "warp":
            self.cell(text="(Unauthorised) WARP")

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

        self.set_font("open-sans", "", 9)
        self.set_xy(155, 15)
        if self.board_type == "vid":
            # Right table
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
        elif self.board_type == "warp":
            with self.table(
                width=40,
                col_widths=(40),
                align="LEFT",
                first_row_as_headings=False,
                borders_layout="None",
                line_height=5,
            ) as table:
                row = table.row()
                row.cell(
                    """Enter current time (eg '3' for 3pm) in header row. Use first blank row."""
                )

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


def fetch_warp_voters(connection, selected_wards=None):
    cursor = connection.cursor()
    cursor.row_factory = dictionary_factory
    query = """
        WITH recent_vids AS (
            SELECT 
                vids.polling_district,
                vids.elector_number,
                vids.voter_intention as last_vid,
                vids.labour_scale as last_labour_scale,
                vids.has_voted as last_has_voted,
                vids.date as last_vid_date
            FROM vids
            INNER JOIN (
                SELECT 
                    polling_district, 
                    elector_number, 
                    MAX(date) as max_date
                FROM vids
                GROUP BY polling_district, elector_number
            ) max_vids ON 
                vids.polling_district = max_vids.polling_district AND 
                vids.elector_number = max_vids.elector_number AND 
                vids.date = max_vids.max_date
            WHERE vids.voter_intention NOT IN ("Conservative", "Won't say", "Won'T Say", "Against", "Reform", "Non-voter", "Non Voter")
            AND vids.has_voted != 1
        )
        SELECT 
            road_group_name as road_group, 
            voter_name as name, 
            address, 
            road_name as road,
            voters.elector_number,
            property_number,
            selection_id,
            last_vid,
            last_labour_scale,
            last_vid_date,
            is_member,
            has_postal,
            date_of_birth,
            note,
            voters.polling_district,
            polling_districts.polling_station as polling_station,
            polling_districts.ward as ward
        FROM voters 
        INNER JOIN roads ON roads.road_id = voters.road_id 
        INNER JOIN road_groups ON roads.road_group_id = road_groups.road_group_id 
        INNER JOIN polling_districts ON road_groups.polling_district_id = polling_districts.polling_district_id
        LEFT JOIN recent_vids ON 
            recent_vids.polling_district = voters.polling_district AND 
            recent_vids.elector_number = voters.elector_number
        WHERE (
            (selection_id NOT IN ('Topup', 'Squeeze', 'Others in hh', 'Hero', 'MTPV', 'Squeeze')) OR 
            (recent_vids.last_vid = "Labour") OR 
            (recent_vids.last_vid = "Don't know" AND last_labour_scale >= 6)
        )
    """
    if selected_wards:
        query += f"AND ward IN {tuple(selected_wards)}"
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


def print_cover_sheet(cover_sheet, road_group, a_voter, board_type):
    pdf = PDF()
    pdf.board_type = board_type
    pdf.add_font(
        "open-sans",
        style="B",
        fname="fonts/OpenSans-Bold.ttf",
    )
    pdf.set_margins(0.5, 100, 10)
    pdf.b_margin = pdf.b_margin / 2
    # Update header
    pdf.header_data = {
        "ward": a_voter["ward"],
        "road": "(Cover sheet)",
        "road_group": road_group,
        "polling_district": a_voter["polling_district"],
        "polling_station": a_voter["polling_station"],
    }
    pdf.add_page()
    pdf.set_font("open-sans", "", 12)
    pdf.set_fallback_fonts(["segoe-ui-emoji"], exact_match=False)

    table_data = (("Road", "Properties", "Voters", "L + VL"),)
    for road in cover_sheet:
        # Address line
        table_data += (
            (
                road["road_name"],
                str(road["property_count"]),
                str(road["voter_count"]),
                str(road["labour_promise_count"]),
            ),
        )
    table_data += (
        (
            "Total",
            str(sum([road["property_count"] for road in cover_sheet])),
            str(sum([road["voter_count"] for road in cover_sheet])),
            str(sum([road["labour_promise_count"] for road in cover_sheet])),
        ),
    )

    pdf.set_xy(5, 35)
    pdf.set_line_width(0.1)
    with pdf.table(
        width=199,
        col_widths=(70, 20, 20, 20),
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

    try:
        pdf.output(f"output_cover_{road_group}.pdf")
    except FileNotFoundError:
        pass
    return f"output_cover_{road_group}.pdf"


def print_road(road_voters, board_type):
    pdf = PDF()
    pdf.board_type = board_type
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
        "ward": road_voters[0][0]["ward"],
        "road": road_voters[0][0]["road"],
        "road_group": road_voters[0][0]["road_group"],
        "polling_district": road_voters[0][0]["polling_district"],
        "polling_station": road_voters[0][0]["polling_station"],
    }
    pdf.add_page()
    pdf.set_font("open-sans", "", 9)
    pdf.set_fallback_fonts(["segoe-ui-emoji"], exact_match=False)

    if board_type == "vid":
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
    elif board_type == "warp":
        table_data = [
            (
                "",
                "Name",
                "Selection",
                "Last VID",
                TableSpan.COL,
                "💌",
                "🌹",
                "",
                "",
                "",
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

    pdf.output(
        f"output_{road_voters[0][0]['polling_district']}_{road_voters[0][0]['road']}.pdf"
    )
    return f"output_{road_voters[0][0]['polling_district']}_{road_voters[0][0]['road']}.pdf"


def merge_pdfs(generated_files):
    merger = pypdf.PdfMerger()
    for pdf in generated_files:
        try:
            merger.append(pdf)
        except FileNotFoundError:
            pass
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


class BoardTypes(str, Enum):
    vid = "vid"
    warp = "warp"


@app.command()
def generate(
    board_type: Annotated[
        BoardTypes,
        typer.Argument(
            help="Choose whether to output a VID sheet ('vid') or WARP sheet ('warp')."
        ),
    ],
    ward: Annotated[
        Optional[List[str]],
        typer.Option(
            help="Ward name to generate boards for, eg 'Huntingdon North'.",
            callback=ward_callback,
        ),
    ] = ["all"],
    road_groups: Annotated[
        Optional[List[str]],
        typer.Option(
            help="Road group to generate boards for, eg '015BZ - Hemingord Abbots Village + Farm'.",
            callback=road_group_callback,
            autocompletion=complete_road_groups,
        ),
    ] = ["all"],
):
    """
    Generate VID or WARP sheets for campaigning.
    """
    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    if len(ward) == 1:
        ward += ["foobar"]
    if board_type == "vid":
        with console.status("[bold green]Fetching voter data...") as status:
            data = fetch_voter_data(connection, ward, road_groups)
    elif board_type == "warp":
        with console.status("[bold green]Fetching voter data...") as status:
            data = fetch_warp_voters(connection, ward)

    # Put it into the polling_district table
    road_groups = sorted(set([voter["road_group"] for voter in data]))
    all_pdfs = []

    for road_group_index, road_group in enumerate(road_groups):
        cover_sheet = []
        roads = sorted(
            set([voter["road"] for voter in data if voter["road_group"] == road_group])
        )
        # Generate cover sheet

        road_group_pdfs = []
        for road in roads:
            road_voters = [voter for voter in data if voter["road"] == road]
            this_road_counts = {"road_name": road}
            this_road_counts["voter_count"] = len(road_voters)
            this_road_counts["labour_promise_count"] = len(
                [
                    voter["last_vid"]
                    for voter in road_voters
                    if voter["last_vid"] == "Labour"
                    and (
                        datetime.strptime(voter["last_vid_date"], "%Y-%m-%d %H:%M:%S")
                        + timedelta(days=1825)
                        >= datetime.today()
                    )
                ]
            )
            road_voters = order_road_voters(road_voters)
            road_voters = split_into_houses(road_voters)
            this_road_counts["property_count"] = len(road_voters)
            cover_sheet += [this_road_counts]
            print(
                f"Printing road group {road_voters[0][0]['road_group']} ({road_group_index+1} of {len(road_groups)})"
            )

            file_name = print_road(road_voters, board_type)
            road_group_pdfs += [file_name]

        cover_sheet_file = print_cover_sheet(
            cover_sheet, road_group, road_voters[0][0], board_type
        )
        all_pdfs.append(cover_sheet_file)
        all_pdfs += [pdf for pdf in road_group_pdfs]

    with console.status(f"[bold green]Merging {len(all_pdfs)} PDFs...") as status:
        merge_pdfs(all_pdfs)

    if board_type == "warp":
        output_filename = "warp_sheets.pdf"
    elif not road_groups:
        output_filename = data[0]["ward"].lower().replace(" ", "_") + ".pdf"
    elif not ward:
        output_filename = (
            data[0]["road_group"].lower().replace(" ", "_")
            + ".pdf"
        )
    with console.status(f"[bold green]Numbering PDFs...") as status:
        number_pdf("output_unnumbered.pdf", output_filename)
    os.remove("output_unnumbered.pdf")
    print(f"Successfully exported as {output_filename}")
    for pdf in all_pdfs:
        try:
            os.remove(pdf)
        except:
            print(pdf + " is missing.")


if __name__ == "__main__":
    app()
