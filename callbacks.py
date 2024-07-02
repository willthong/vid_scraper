from data_functions import fetch_polling_districts
import re
import typer

def polling_district_callback(value: str):
    polling_districts = fetch_polling_districts()
    polling_districts = [polling_district[0] for polling_district in polling_districts]
    value = value.upper().strip()
    if value not in polling_districts:
        raise typer.BadParameter("Polling district not found.")
    return value


def elector_number_callback(value: str):
    value = value.upper().strip()
    if re.search(r"[a-zA-Z]", value):
        raise typer.BadParameter("Please enter a valid elector number.")
    return value

def vid_code_callback(value: str):
    value = value.upper().strip()
    if re.search(r"[^VILTSGRADXZ0-9/]", value):
        raise typer.BadParameter(
            """
            Please enter a valid Voter ID code. Allowed characters: (V)oted, (L)abour,
            (T)ory, (S)DP aka Lib Dems, (G)reen, (R)eform, (A)gainst, (D)on't Know, (X)
            / Won't Say, (Z) / Non-Voter, (0-9) / Likelihood of voting Labour, (/) / all
            subsequent parties are those the voter definitely wouldn't vote for.
        """
        )
    if "V" in value:
        if "X" in value:
            raise typer.BadParameter("They can't both have voted and be a non-voter.")
        if "D" in value:
            raise typer.BadParameter(
                "They can't both have voted and not know how they voted."
            )
    return value
