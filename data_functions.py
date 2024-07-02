import sqlite3

def fetch_wards():
    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()
    data = cursor.execute(
        """
        SELECT DISTINCT
            ward
        FROM polling_districts 
        ORDER BY
            ward
        """
    ).fetchall()
    return data

def fetch_polling_districts(selected_ward=None):
    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()
    query = f"""
        SELECT DISTINCT polling_district
        FROM polling_districts 
    """
    if selected_ward:
        query += "WHERE ward = '{selected_ward}'"
    data = cursor.execute(query).fetchall()
    return data

def fetch_road_groups(selected_ward):
    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()
    data = cursor.execute(
        f"""
        SELECT DISTINCT road_group_name, ward 
        FROM road_groups 
        JOIN polling_districts ON road_groups.polling_district_id = polling_districts.polling_district_id 
        WHERE ward = '{selected_ward}'
        """
    ).fetchall()
    return data


def write_vid_data(vids, connection):
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS vids (
            vid_id INTEGER PRIMARY KEY,
            polling_district TEXT,
            elector_number TEXT,
            voter_intention TEXT,
            labour_scale TEXT,
            date TEXT,
            will_not_vote_for TEXT,
            has_voted INT,
            FOREIGN KEY (polling_district, elector_number) 
            REFERENCES voters(polling_district, elector_number)
        )
        """
    )
    insert_query = """
        INSERT OR IGNORE INTO vids
        (polling_district, elector_number, voter_intention, labour_scale, date, will_not_vote_for, has_voted)
        VALUES 
        (?, ?, ?, ?, ?, ?, ?)
        """
    tuples = []
    for vid in vids:
        vid_tuple = (
            vid["polling_district"],
            vid["elector_number"],
            vid.get("vid", ""),
            vid.get("vid_labour_scale", ""),
            vid.get("vid_date", ""),
            vid.get("vid_will_not_vote_for", ""),
            vid.get("vid_has_voted", ""),
        )
        tuples += [vid_tuple]
    cursor.executemany(insert_query, tuples)
    connection.commit()
    return


def fetch_voter(connection, polling_district, elector_number):
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


def delete_voter(connection, voter):
    cursor = connection.cursor()
    query = f"""
        DELETE FROM voters
        WHERE
            (voters.polling_district = '{voter[0]}' AND voters.elector_number = '{voter[1]}')
    """
    data = cursor.execute(query)
    return data
