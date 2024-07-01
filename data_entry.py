from data_functions import fetch_wards, fetch_polling_districts, write_vid_data
import datetime
import re
import sqlite3
from tabulate import tabulate


def select_polling_district():
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

    polling_districts = fetch_polling_districts(selected_ward)
    while True:
        print("Polling districts in this ward:")
        for index, polling_district in enumerate(polling_districts):
            print(f"{index + 1}) {polling_district[0]}")
        try:
            selected_pd_id = input(
                "\nSelect one of the above polling districts by number:"
            )
            selected_pd_id = int(selected_pd_id.replace(")", "")) - 1
        except ValueError:
            print("Sorry - you need to enter a number.")
            continue
        if selected_pd_id < 0 or selected_pd_id > len(polling_districts) - 1:
            print("Please select a valid polling district from the list.\n")
        else:
            break
    selected_polling_district = polling_districts[selected_pd_id][0]
    print(f"You selected {selected_polling_district}.")
    return selected_polling_district


def select_date():
    while True:
        month = input("Enter a month number or type Q to quit")
        if month == "q":
            break
        try:
            month = int(month)
        except ValueError:
            continue
        if month > 12 or month < 1:
            print("Please enter a valid month number.\n")
            continue
        else:
            break
    while True:
        day = input("Enter a day number or type Q to quit")
        if month == "q":
            break
        try:
            day = int(day)
        except ValueError:
            continue
        if month > 31 or month < 1:
            print("Please enter a valid day number.\n")
            continue
        else:
            break
    return datetime.datetime(year=2024, month=month, day=day)


def convert_code_to_vid(code):
    vid, vs = {}, False
    for character in code:
        if character == "V":
            vid["vid_has_voted"] = True
        if character == "L":
            if not vs:
                vid["vid"] = "Labour"
            else:
                vid["vid_will_not_vote_for"] = "Labour"
        if character == "T":
            if not vs:
                vid["vid"] = "Conservative"
            else:
                vid["vid_will_not_vote_for"] = "Conservative"
        if character == "R":
            if not vs:
                vid["vid"] = "Reform"
            else:
                vid["vid_will_not_vote_for"] = "Reform"
        if character == "G":
            if not vs:
                vid["vid"] = "Green"
            else:
                vid["vid_will_not_vote_for"] = "Green"
        if character == "S":
            if not vs:
                vid["vid"] = "Liberal Democrats"
            else:
                vid["vid_will_not_vote_for"] = "Liberal Democrats"
        if character == "D":
            vid["vid"] = "Don't know"
        if character == "X":
            vid["vid"] = "Won't say"
        if character == "Z":
            vid["vid"] = "Non-voter"
        if character in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            vid["vid_labour_scale"] = character
        if character == "/":
            vs = True
    return vid


def select_elector_number(polling_district):
    while True:
        elector_number = input("Enter an elector number or type Q to quit")
        if elector_number.lower() == "q":
            voter_intention_data_entry()
        elif re.search(r"[a-zA-Z]", elector_number):
            print("Please enter a valid elector number.\n")
            continue
        else:
            break
    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()
    query = f"""
        SELECT
            *
        FROM
            voters
        WHERE
            (voters.polling_district = '{polling_district}' AND voters.elector_number = '{elector_number}')
    """
    data = cursor.execute(query)
    return data.fetchone()


def voter_intention_enter_single_voter(voter, polling_district, date):
    while True:
        print(
            f"\nYou are about to enter data for {voter[2]} ({polling_district}-{voter[1]}). Enter (optionally) a V prefix, the VI code (V, L, T, S, G, R, D, X, Z), (optionally) a number and (optionally) a slashed code (eg '/T') to indicate anyone they wouldn't vote for. Type Q to select a new voter."
        )
        vid = {}
        data_to_enter = input("Type the voter response:")
        data_to_enter = data_to_enter.upper()
        if data_to_enter == "q":
            voter_intention_enter_single_voter(voter, polling_district, date)
        elif re.search(r"[^VLTSGRDXZ0-9/]", data_to_enter):
            print("Please enter a valid voter intention")
            continue
        else:
            vid = convert_code_to_vid(data_to_enter)
            vid["polling_district"] = polling_district
            vid["elector_number"] = voter[1]
            vid["vid_date"] = date
            if "vid" in vid.keys():
                break
    while True:
        print(
            f"\nYou are still entering data for {voter[2]} ({polling_district}-{voter[1]}). Type any custom notes, or leave blank if there are no notes."
        )
        note = input("Type a custom note or leave blank:")
        break

    while True:
        table_data = (
            ("Name", voter[2]),
            ("Voted?", "True" if "vid_has_voted" in vid.keys() else "False"),
            ("Voter intention", vid["vid"]),
        )
        if "vid_labour_scale" in vid.keys():
            table_data += (("Labour likelihood", vid["vid_labour_scale"]),)
        if "vid_will_not_vote_for" in vid.keys():
            table_data += (("Won't vote for", vid["vid_will_not_vote_for"]),)
        print("\n")
        print(tabulate(table_data))
        cancel = input("Hit Enter to confirm, or x to cancel")
        if not cancel:
            vids = [vid]
            connection = sqlite3.connect(
                "voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES
            )
            write_vid_data(vids, connection)
            print("Record written!")
            break
        else:
            print("Data entry cancelled!")
            voter_intention_enter_single_voter(voter, polling_district, date)


def voter_intention_data_entry():
    polling_district = select_polling_district()
    date = select_date()
    while True:
        voter = select_elector_number(polling_district)
        if not voter:
            print("Voter not found")
            continue
        else:
            voter_intention_enter_single_voter(voter, polling_district, date)
            continue


def voter_intention_data_entry_session():
    while True:
        voter_intention_data_entry()


if __name__ == "__main__":
    voter_intention_data_entry_session()
