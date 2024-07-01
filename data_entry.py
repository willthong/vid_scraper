from data_functions import fetch_wards, fetch_polling_districts
import re
import sqlite3


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


def convert_code_to_vi(code):
    if "L" in code:
        return "Labour"
    elif "T" in code:
        return "Conservative"
    elif "S" in code:
        return "Liberal Democrats"
    elif "G" in code:
        return "Green"
    elif "R" in code:
        return "Reform"
    elif "D" in code:
        return "Don't know"
    elif "X" in code:
        return "Won't say"
    elif "Z" in code:
        return "Non-voter"


def voter_intention_data_entry():
    polling_district = select_polling_district()
    while True:
        elector_number = input("Enter an elector number or type Q to quit")
        if elector_number == "q":
            break
        if re.search(r"[a-zA-Z]", elector_number):
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
    voter = data.fetchone()
    while True:
        print(
            f"You are about to enter data for {voter[2]} ({polling_district}-{elector_number}). Enter (optionally) a V prefix, the VI code (V, L, T, S, G, R, D, X, Z), (optionally) a number and (optionally) a slashed code (eg '/T') to indicate anyone they wouldn't vote for."
        )
        data_to_enter = input("Type the voter response:")
        data_to_enter = data_to_enter.upper()
        if data_to_enter == "q":
            break
        elif re.search(r"[^VLTSGRDXZ0-9/]", data_to_enter):
            print("Please enter a valid voter intention")
            continue
        else:
            has_voted = True if "P" in data_to_enter else False
            # Use re.search to match the pattern
            slash_split = re.search(r"^(.*?)\/(.*?)$", data_to_enter)
            if slash_split.group(1):
                will_not_vote_for = convert_code_to_vi(slash_split.group(1))
            voter_intention = convert_code_to_vi(slash_split.group(0))
            labour_scale = slash_split.group(0)

            # Enter the data


def voter_intention_data_entry_session():
    while True:
        voter_intention_data_entry()


if __name__ == "__main__":
    voter_intention_data_entry_session()
