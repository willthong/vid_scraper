from kontakt_kreator.data_functions import fetch_polling_districts

import re
import sqlite3
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
        if "Z" in value:
            raise typer.BadParameter("They can't both have voted and be a non-voter.")
        if "D" in value:
            raise typer.BadParameter(
                "They can't both have voted and not know how they voted."
            )
    return value


def ward_callback(ward_list: list):
    if ward_list is None or ward_list == ["all"]:
        return []
    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()
    for ward in ward_list:
        if not (
            cursor.execute(
                f"SELECT * FROM polling_districts WHERE ward = '{ward}'"
            ).fetchone()
        ):
            raise typer.BadParameter(f"Ward '{ward}' not found")
    if len(ward_list) == 1:
        ward_list += ["A placeholder value to make tuple work"]
    return ward_list


def road_group_callback(road_group_list: list):
    if road_group_list is None or road_group_list == ["all"]:
        return []
    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()
    for road_group in road_group_list:
        if not (
            cursor.execute(
                f"SELECT * FROM road_groups WHERE road_group_name = '{road_group}'"
            ).fetchone()
        ):
            raise typer.BadParameter(f"Road group '{road_group}' not found")
    if len(road_group_list) == 1:
        road_group_list += ["A placeholder value to make tuple work"]
    return road_group_list
