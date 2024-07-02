import csv
from datetime import datetime
from pathlib import Path
import re
import sqlite3
from typing import Optional

from rich import print, box
from rich.console import Console
from rich.table import Table
import typer
from typing_extensions import Annotated

from callbacks import (
    polling_district_callback,
    elector_number_callback,
    vid_code_callback,
)
from data_functions import write_vid_data, fetch_voter


app = typer.Typer()


def convert_code_to_vid(code):
    vid, vs = {}, False
    seen_nv_code = False
    for index, character in enumerate(code):
        if character == "N" and code[index + 1] == "V":
            seen_nv_code = True
            vid["vid"] = "Non-voter"
        elif not seen_nv_code and character == "V":
            vid["vid_has_voted"] = True
        elif character == "L":
            if not vs:
                vid["vid"] = "Labour"
            else:
                vid["vid_will_not_vote_for"] = "Labour"
        elif character == "T":
            if not vs:
                vid["vid"] = "Conservative"
            else:
                vid["vid_will_not_vote_for"] = "Conservative"
        elif character == "R":
            if not vs:
                vid["vid"] = "Reform"
            else:
                vid["vid_will_not_vote_for"] = "Reform"
        elif character == "G":
            if not vs:
                vid["vid"] = "Green"
            else:
                vid["vid_will_not_vote_for"] = "Green"
        elif character == "S":
            if not vs:
                vid["vid"] = "Liberal Democrats"
            else:
                vid["vid_will_not_vote_for"] = "Liberal Democrats"
        elif character == "I":
            if not vs:
                vid["vid"] = "Independent"
            else:
                vid["vid_will_not_vote_for"] = "Independent"
        elif character in ["D", "U"]:
            vid["vid"] = "Don't know"
        elif character == "A":
            vid["vid"] = "Against"
        elif character == "X":
            vid["vid"] = "Won't say"
        elif character == "Z":
            vid["vid"] = "Non-voter"
        elif character in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            vid["vid_labour_scale"] = character
        elif character == "/":
            vs = True
    return vid


@app.command()
def add(
    date: datetime,
    polling_district: Annotated[
        str,
        typer.Argument(
            help="The polling district, eg 015CN", callback=polling_district_callback
        ),
    ],
    elector_number: Annotated[
        str,
        typer.Argument(
            help="The elector number, eg 102/3", callback=elector_number_callback
        ),
    ],
    vid_code: Annotated[
        str,
        typer.Argument(
            help="The Voter ID code, eg 'VL/S' or 'D9/T'", callback=vid_code_callback
        ),
    ],
):

    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    voter = fetch_voter(connection, polling_district, elector_number)
    if not voter:
        raise Exception("Voter not found.")

    vid = convert_code_to_vid(vid_code)
    vid["polling_district"] = polling_district
    vid["elector_number"] = elector_number
    vid["vid_date"] = date

    table = Table(show_header=False, box=box.HORIZONTALS)
    table.add_row("Name", voter[2])
    table.add_row("Voted?", "True" if "vid_has_voted" in vid.keys() else "False")
    table.add_row("Voter intention", vid["vid"])
    if "vid_labour_scale" in vid.keys():
        table.add_row("Labour likelihood", vid["vid_labour_scale"])
    if "vid_will_not_vote_for" in vid.keys():
        table.add_row("Won't vote for", vid["vid_will_not_vote_for"])

    console = Console()
    console.print(table)

    typer.confirm("Are you sure you want to add this record?", abort=True)

    vids = [vid]
    write_vid_data(vids, connection)
    print("Record written!")


@app.command()
def import_file(
    file: Annotated[
        Path, typer.Argument(exists=True, file_okay=True, dir_okay=False, readable=True)
    ],
    date: datetime,
):

    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)

    with file.open("r", encoding="utf-8") as file_object:
        reader = csv.reader(file_object)
        header_row = next(reader)
        header_indices = {}
        for cell_index, cell in enumerate(header_row):
            if cell in ["polling_district", "elector_number", "code"]:
                header_indices[cell] = cell_index
            else:
                raise Exception(f"Unknown column: '{cell}'")
        invalid_rows, vids, extra_information = [], [], []
        for row in reader:
            voter = fetch_voter(
                connection,
                row[header_indices["polling_district"]],
                row[header_indices["elector_number"]],
            )
            if not voter:
                invalid_rows.append(row)
                continue

            code = row[header_indices["code"]].upper().strip()
            if re.search(r"[^VILTSGRADXZNU0-9/]", code):
                invalid_rows.append(code)
            elif "V" in code:
                if "X" in code:
                    invalid_rows.append(code)
                if "D" in code:
                    invalid_rows.append(code)
            vid = convert_code_to_vid(code)
            vid["polling_district"] = row[header_indices["polling_district"]]
            vid["elector_number"] = row[header_indices["elector_number"]]
            vid["vid_date"] = date
            vids.append(vid)
            # (Name, code)
            extra_information.append((voter[2], code))

    valid_vids_table = Table(show_header=True, box=box.HORIZONTALS)
    valid_vids_table.add_row(
        "Name",
        "Code",
        "Voted?",
        "Voter intention",
        "Labour likelihood",
        "Won't vote for",
    )
    for index, vid in enumerate(vids):
        valid_vids_table.add_row(
            extra_information[index][1],
            extra_information[index][1],
            "True" if "vid_has_voted" in vid.keys() else "False",
            vid["vid"],
            str(vid.get("vid_labour_scale", "")),
            vid.get("vid_will_not_vote_for", ""),
        )

    console = Console()
    console.print(valid_vids_table)


if __name__ == "__main__":
    app()
