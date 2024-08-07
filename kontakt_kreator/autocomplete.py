import sqlite3

import typer
from typing_extensions import Annotated

from kontakt_kreator.data_functions import fetch_road_groups, fetch_wards


def complete_wards(incomplete: str):
    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    completion = []
    wards = [ward_tuple[0] for ward_tuple in fetch_wards(connection)]
    for ward in wards:
        if ward.startswith(incomplete):
            completion.append(ward)
    return wards


def complete_road_groups(incomplete: str):
    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    completion = []
    road_groups = [
        road_group_tuple[0] for road_group_tuple in fetch_road_groups(connection)
    ]
    for road_group in road_groups:
        if road_group.startswith(incomplete):
            completion.append(road_group)
    return completion
