from callbacks import polling_district_callback, elector_number_callback
from data_functions import delete_voter, fetch_voter

import re
import sqlite3
import typer
from typing_extensions import Annotated

app = typer.Typer()



@app.command()
def rm(
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
):

    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    voter = fetch_voter(connection, polling_district, elector_number)
    if not voter:
        raise Exception("Voter not found.")

    typer.confirm(f"Are you sure you want to delete {voter[2]} from the database?", abort=True)

    delete_voter(connection, voter)
    connection.commit()
    print("Voter successfully deleted!")

if __name__ == "__main__":
    app()
