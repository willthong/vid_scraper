from kontakt_kreator.data_functions import fetch_wards

from rich import print
from rich.progress import Console
import typer

app = typer.Typer()
console = Console()


@app.command()
def ls():
    wards = fetch_wards()
    for ward in wards:
        print(ward[0])


if __name__ == "__main__":
    app()
