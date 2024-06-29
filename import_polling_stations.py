import csv
import sqlite3


def import_polling_stations():
    polling_stations = []
    with open("input/polling_stations.csv", newline="") as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            for code in row[1].split(","):
                polling_stations.append((code, row[2]))

    print(polling_stations)

    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()
    for polling_station in polling_stations:
        cursor.execute(
            f"""
            UPDATE polling_districts
            SET polling_station = '{polling_station[1]}'
            WHERE
                polling_district = '015{polling_station[0]}'
        """
        )
    connection.commit()
    return

    # Put it into the polling_district table


if __name__ == "__main.py__":
    import_polling_stations()
