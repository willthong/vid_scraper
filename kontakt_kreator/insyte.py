from kontakt_kreator.autocomplete import complete_wards
from kontakt_kreator.callbacks import ward_callback
from kontakt_kreator.data_functions import fetch_postal_vids

from datetime import datetime, timedelta
import sqlite3
from typing import List, Optional
from typing_extensions import Annotated


from rich import print, box
from rich.progress import Console
from rich.table import Table
import typer

app = typer.Typer()
console = Console()


def dictionary_factory(cursor, row):
    dictionary = {}
    for index, column in enumerate(cursor.description):
        dictionary[column[0]] = row[index]
    return dictionary


def fetch_voter_data(connection, selected_ward):
    cursor = connection.cursor()
    cursor.row_factory = dictionary_factory
    query = """
        SELECT 
            road_group_name as road_group, 
            voters.polling_district,
            voters.elector_number,
            vids.voter_intention as last_vid,
            vids.date as last_vid_date,
            polling_districts.ward as ward
        FROM voters 
        INNER JOIN roads ON roads.road_id = voters.road_id 
        INNER JOIN road_groups ON roads.road_group_id = road_groups.road_group_id 
        INNER JOIN polling_districts ON road_groups.polling_district_id = polling_districts.polling_district_id
        LEFT JOIN vids ON (vids.polling_district + vids.elector_number) = (voters.polling_district + voters.elector_number)
        AND vids.date = (
            SELECT MAX(vids_inner.date) FROM vids AS vids_inner
            WHERE vids_inner.polling_district = voters.polling_district AND 
            vids_inner.elector_number = voters.elector_number
        )
    """
    if len(selected_ward) > 0:
        query += f"WHERE polling_districts.ward IN {tuple(selected_ward)}"
    query += """
    ORDER BY
        road_group
    """
    data = cursor.execute(query).fetchall()
    return data


def print_postal_vote_stats(data, sort_column):
    road_groups = sorted(set([voter["road_group"] for voter in data]))
    voter_counts, contacted_counts, labour_promises = {}, {}, {}
    for road_group in road_groups:
        voter_counts[road_group] = 0
        contacted_counts[road_group] = 0
        labour_promises[road_group] = 0

    for voter in data:
        voter_counts[voter["road_group"]] += 1
        if voter["last_vid_date"]:
            last_vid_date = datetime.strptime(
                voter["last_vid_date"], "%Y-%m-%d %H:%M:%S"
            )
            if last_vid_date + timedelta(days=1825) >= datetime.today():
                contacted_counts[voter["road_group"]] += 1
                if voter["last_vid"] == "Labour":
                    labour_promises[voter["road_group"]] += 1

    table = []
    for road_group in road_groups:
        table.append(
            [
                road_group[:33],
                voter_counts[road_group],
                contacted_counts[road_group],
                round(contacted_counts[road_group] / voter_counts[road_group] * 100, 1),
                labour_promises[road_group],
                round(labour_promises[road_group] / voter_counts[road_group] * 100, 1),
            ]
        )

    if sort_column == "Contact rate":
        table.sort(key=lambda x: x[3], reverse=True)
    elif sort_column == "Net promises":
        table.sort(key=lambda x: x[4], reverse=True)
    elif sort_column == "Promise rate":
        table.sort(key=lambda x: x[5], reverse=True)


    console_table = Table(show_header=True, box=box.HORIZONTALS)
    console_table.add_column("Road group")
    console_table.add_column("Voters", justify="right")
    console_table.add_column("Contacts", justify="right")
    console_table.add_column("%", justify="right")
    console_table.add_column("Promises", justify="right")
    console_table.add_column("%", justify="right")
    for row in table:
        console_table.add_row(
            row[0],
            str(row[1]),
            str(row[2]),
            str(row[3]),
            str(row[4]),
            str(row[5]),
        )
    console.print(console_table)


def print_contact_rate_stats(data, sort_column):
    road_groups = sorted(set([(voter["road_group"],voter["ward"]) for voter in data]))
    voter_counts, contacted_counts, labour_promises = {}, {}, {}
    for road_group in road_groups:
        voter_counts[road_group[0]] = 0
        contacted_counts[road_group[0]] = 0
        labour_promises[road_group[0]] = 0

    for voter in data:
        voter_counts[voter["road_group"]] += 1
        if voter["last_vid_date"]:
            last_vid_date = datetime.strptime(
                voter["last_vid_date"], "%Y-%m-%d %H:%M:%S"
            )
            if last_vid_date + timedelta(days=1825) >= datetime.today():
                contacted_counts[voter["road_group"]] += 1
                if voter["last_vid"] == "Labour":
                    labour_promises[voter["road_group"]] += 1

    table = []
    for road_group in road_groups:
        table.append(
            [
                road_group[1], # Ward
                road_group[0][:33],
                voter_counts[road_group[0]],
                contacted_counts[road_group[0]],
                round(contacted_counts[road_group[0]] / voter_counts[road_group[0]] * 100, 1),
                labour_promises[road_group[0]],
                round(labour_promises[road_group[0]] / voter_counts[road_group[0]] * 100, 1),
            ]
        )

    if sort_column == "contact_rate":
        table.sort(key=lambda x: x[3], reverse=True)
    elif sort_column == "net_promises":
        table.sort(key=lambda x: x[4], reverse=True)
    elif sort_column == "promise_rate":
        table.sort(key=lambda x: x[5], reverse=True)

    console_table = Table(show_header=True, box=box.HORIZONTALS)
    console_table.add_column("Ward")
    console_table.add_column("Road group")
    console_table.add_column("Voters", justify="right")
    console_table.add_column("C", justify="right")
    console_table.add_column("%", justify="right")
    console_table.add_column("P", justify="right")
    console_table.add_column("%", justify="right")
    for row in table:
        console_table.add_row(
            row[0],
            row[1],
            str(row[2]),
            str(row[3]),
            str(row[4]),
            str(row[5]),
            str(row[6]),
        )
    console.print(console_table)



@app.command()
def postal_votes(date: datetime):
    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    data = fetch_postal_vids(connection, date)
    postal_vote_count = len(data)
    wont_say_postal_count = len(
        [record for record in data if record.get("voter_intention") == "Won't say"]
    )
    will_say_postal_count = postal_vote_count - wont_say_postal_count
    labour_postal_count = len(
        [record for record in data if record.get("voter_intention") == "Labour"]
    )
    tory_postal_count = len(
        [record for record in data if record.get("voter_intention") == "Conservative"]
    )
    libdem_postal_count = len(
        [record for record in data if record.get("voter_intention") == "Liberal Democrat"]
    )
    independent_postal_count = len(
        [record for record in data if record.get("voter_intention") == "Independent"]
    )
    green_postal_count = len(
        [record for record in data if record.get("voter_intention") == "Green"]
    )
    against_postal_count = len(
        [record for record in data if record.get("voter_intention") == "Against"]
    )
    console_table = Table(show_header=False, box=box.HORIZONTALS)
    console_table.add_row("Have voted", str(postal_vote_count))
    console_table.add_row("    Won't say", str(wont_say_postal_count))
    console_table.add_row("    Will say", str(will_say_postal_count))
    console_table.add_row("        Labour", str(labour_postal_count))
    console_table.add_row("        Conservative", str(tory_postal_count))
    console_table.add_row("        Liberal Democrat", str(libdem_postal_count))
    console_table.add_row("        Independent", str(independent_postal_count))
    console_table.add_row("        Green", str(green_postal_count))
    console_table.add_row("        Against (other)", str(against_postal_count))
    print(f"Have postal voted so far according to canvassing since {date}:")
    console.print(console_table)


@app.command()
def contact_and_promise_rates(
    ward: Annotated[
        Optional[List[str]], 
        typer.Option(
            help="Ward name to view rates for, eg 'Huntingdon North'.",
            callback=ward_callback,
            autocompletion=complete_wards,
        )
    ] = [],
    sort: Annotated[
        Optional[str], 
        typer.Option(help="One of 'contact_rate', 'net_promises' or 'promise_rate'.")
    ] = "promise_rate",
):
    
    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    with console.status("[bold green]Fetching voter data...") as status:
        data = fetch_voter_data(connection, ward)
    print_contact_rate_stats(data, sort)


if __name__ == "__main__":
    app()
