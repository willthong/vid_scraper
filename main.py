from generate_vid import generate_polling_district
from scrape_vid import vid_sheet_import
from import_polling_stations import import_polling_stations


def select_import():
    while True:
        selected_output = input(
            """Would you like to import 
    (V)ID sheets;
    (P)olling stations; or 
    (A)bsent voters?
    (Q)uit
"""
        )
        selected_output = selected_output.lower()
        if selected_output not in ["v", "p", "a", "q"]:
            print("Please select one of the options")
            continue
        else:
            break

    if selected_output == "v":
        vid_sheet_import()
    if selected_output == "p":
        vid_sheet_import()
    if selected_output == "a":
        vid_sheet_import()
    if selected_output == "q":
        return


def kontacts_kreated():
    while True:
        selected_output = input(
            "Would you like to (I)mport data, (E)xport data, (V)iew stats or (Q)uit?"
        )
        selected_output = selected_output.lower()
        if selected_output not in ["i", "e", "v", "q"]:
            print("Please select one of the options")
            continue
        else:
            break

    if selected_output == "i":
        select_import()
    elif selected_output == "e":
        generate_polling_district()
    elif selected_output == "v":
        view_stats()
    elif selected_output == "q":
        exit()


if __name__ == "__main__":
    while True:
        kontacts_kreated()
