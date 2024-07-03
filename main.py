from kontakt_kreator import (
    board,
    insyte,
    old_cli,
    road_group,
    vid,
    voter,
    ward,
)


import typer

app = typer.Typer()

app.add_typer(insyte.app, name="insyte")
app.add_typer(vid.app, name="vid")
app.add_typer(voter.app, name="voter")
app.add_typer(board.app, name="board")
app.add_typer(road_group.app, name="road_group")
app.add_typer(ward.app, name="ward")
app.add_typer(old_cli.app, name="old_cli")

if __name__ == "__main__":
    app()
