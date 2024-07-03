import sqlite3

from kontakt_kreator.data_functions import fetch_road_groups
from kontakt_kreator.callbacks import ward_callback

from rich.progress import Console
from rich.table import Table, box
from rich import print
from typing import List, Optional
from typing_extensions import Annotated
import typer

app = typer.Typer()
console = Console()


@app.command()
def ls(
    ward: Annotated[
        Optional[List[str]],
        typer.Option(
            help="Ward name to list road groups for, eg 'Huntingdon North'.",
            callback=ward_callback,
        ),
    ] = None,
):
    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    road_group_tuples = fetch_road_groups(connection, ward)

    table = Table(show_header=True, box=box.HORIZONTALS)
    table.add_column("Ward")
    table.add_column("Road group")
    for road_group_tuple in road_group_tuples:
        table.add_row(
            road_group_tuple[1],
            road_group_tuple[0],
        )
    console.print(table)


if __name__ == "__main__":
    app()
