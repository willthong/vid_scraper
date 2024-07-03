from kontakt_kreator.scrape_vid import vid_sheet_import
from kontakt_kreator.import_polling_stations import import_polling_stations
from rich import print
import typer

app = typer.Typer()


def select_import():
    while True:
        selected_output = input(
            """Would you like to import 
    (V)ID sheets;
    (P)olling stations; or 
    (A)bsent voters?
    (Q)uit
"""
        )
        selected_output = selected_output.lower()
        if selected_output not in ["v", "p", "a", "q"]:
            print("Please select one of the options")
            continue
        else:
            break

    if selected_output == "v":
        vid_sheet_import()
    if selected_output == "p":
        import_polling_stations()
    if selected_output == "a":
        vid_sheet_import()
    if selected_output == "q":
        return


@app.command()
def menu():
    while True:
        selected_output = input(
            "Would you like to (I)mport data, (E)xport data, perform (D)ata entry, (V)iew stats or (Q)uit?"
        )
        selected_output = selected_output.lower()
        if selected_output not in ["i", "e", "q"]:
            print("Please select one of the options")
            continue
        else:
            break
    if selected_output == "i":
        select_import()
    elif selected_output == "q":
        exit()

if __name__ == "__main__":
    app()
