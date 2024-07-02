import old_cli
import vid
import voter
import typer

from rich import print

app = typer.Typer()

app.add_typer(vid.app, name="vid")
app.add_typer(voter.app, name="voter")
app.add_typer(old_cli.app, name="old_cli")

if __name__ == "__main__":
    app()
