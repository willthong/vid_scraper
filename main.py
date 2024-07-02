import old_cli
import vids
import voter
import typer

from rich import print

app = typer.Typer()

app.add_typer(vids.app, name="vid")
app.add_typer(voter.app, name="voter")
app.add_typer(old_cli.app, name="old_cli")

if __name__ == "__main__":
    app()
