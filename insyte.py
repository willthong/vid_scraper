from data_functions import fetch_wards
from datetime import datetime, timedelta
import sqlite3
from tabulate import tabulate


def dictionary_factory(cursor, row):
    dictionary = {}
    for index, column in enumerate(cursor.description):
        dictionary[column[0]] = row[index]
    return dictionary


def fetch_voter_data(selected_ward):
    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()
    cursor.row_factory = dictionary_factory
    query = f"""
        SELECT 
            road_group_name as road_group, 
            voters.polling_district,
            voters.elector_number,
            vids.voter_intention as last_vid,
            vids.date as last_vid_date
        FROM voters 
        INNER JOIN roads ON roads.road_id = voters.road_id 
        INNER JOIN road_groups ON roads.road_group_id = road_groups.road_group_id 
        INNER JOIN polling_districts ON road_groups.polling_district_id = polling_districts.polling_district_id
        LEFT JOIN vids ON (vids.polling_district + vids.elector_number) = (voters.polling_district + voters.elector_number)
        AND vids.date = (
            SELECT MAX(vids_inner.date)
            from vids AS vids_inner
            WHERE (vids_inner.polling_district + vids_inner.elector_number) = (voters.polling_district + voters.elector_number)
        )
        WHERE polling_districts.ward = '{selected_ward}'
        ORDER BY
            road_group,
            roads.road_name,
            voters.elector_number
        """
    data = cursor.execute(query).fetchall()
    return data


def print_stats(data):

    road_groups = sorted(set([voter["road_group"] for voter in data]))
    voter_counts, contacted_counts, labour_promises = {}, {}, {}
    for road_group in road_groups:
        voter_counts[road_group] = 0
        contacted_counts[road_group] = 0
        labour_promises[road_group] = 0

    for voter in data:
        voter_counts[voter["road_group"]] += 1
        if voter["last_vid_date"]:
            last_vid_date = datetime.strptime(
                voter["last_vid_date"], "%Y-%m-%d %H:%M:%S"
            )
            if last_vid_date + timedelta(days=365) >= datetime.today():
                contacted_counts[voter["road_group"]] += 1
                if voter["last_vid"] == "Labour":
                    labour_promises[voter["road_group"]] += 1

    table = []
    for road_group in road_groups:
        table.append(
            [
                road_group[:33],
                voter_counts[road_group],
                contacted_counts[road_group],
                round(contacted_counts[road_group] / voter_counts[road_group] * 100, 1),
                labour_promises[road_group],
                round(labour_promises[road_group] / voter_counts[road_group] * 100, 1),
            ]
        )

    headers = ["Road group", "Voters", "Contacts", "Contact %", "Promises", "Promise %"]
    table.sort(key=lambda x: x[3], reverse=True)
    print(tabulate(table, headers=headers))


def insyte():
    wards = fetch_wards()
    while True:
        print("Wards in this constituency:")
        for index, ward in enumerate(wards):
            print(f"{index + 1}) {ward[0]}")
        try:
            selected_ward_id = input("\nSelect one of the above wards by number:")
            selected_ward_id = int(selected_ward_id.replace(")", "")) - 1
        except ValueError:
            print("Sorry - you need to enter a number.")
            continue
        if selected_ward_id < 0 or selected_ward_id > len(wards) - 1:
            print("Please select a valid ward number from the list.\n")
        else:
            break
    selected_ward = wards[selected_ward_id][0]
    print(f"You selected {selected_ward}.")
    data = fetch_voter_data(selected_ward)
    print_stats(data)


if __name__ == "__main__":
    insyte()
