import sqlite3
from rich import print

def dictionary_factory(cursor, row):
    dictionary = {}
    for index, column in enumerate(cursor.description):
        dictionary[column[0]] = row[index]
    return dictionary

def fetch_wards(connection, ward=None):
    cursor = connection.cursor()
    query = """
        SELECT DISTINCT
            ward
        FROM polling_districts 
        ORDER BY
            ward
        """
    if ward and len(ward) > 0:
        query += f"WHERE ward in {tuple(ward)}"
    data = cursor.execute(query).fetchall()
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

def fetch_road_groups(connection, selected_wards=None):
    cursor = connection.cursor()
    query = f"""
        SELECT DISTINCT road_group_name, ward 
        FROM road_groups 
        JOIN polling_districts ON road_groups.polling_district_id = polling_districts.polling_district_id 
        """
    if selected_wards and len(selected_wards) > 0:
        query += f"WHERE polling_districts.ward IN {tuple(selected_wards)}"
    data = cursor.execute(query).fetchall()
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


def fetch_voter_data(connection, selected_ward, road_groups):
    cursor = connection.cursor()
    cursor.row_factory = dictionary_factory
    query = f"""
        SELECT 
            road_group_name as road_group, 
            voter_name as name, 
            address, 
            road_name as road,
            voters.elector_number,
            property_number,
            selection_id,
            vids.voter_intention as last_vid,
            vids.labour_scale as last_labour_scale,
            vids.date as last_vid_date,
            is_member,
            has_postal,
            date_of_birth,
            note,
            voters.polling_district,
            polling_districts.polling_station as polling_station,
            polling_districts.ward as ward
        FROM voters 
        INNER JOIN roads ON roads.road_id = voters.road_id 
        INNER JOIN road_groups ON roads.road_group_id = road_groups.road_group_id 
        INNER JOIN polling_districts ON road_groups.polling_district_id = polling_districts.polling_district_id
        LEFT JOIN vids ON (vids.polling_district = voters.polling_district AND vids.elector_number = voters.elector_number)
        AND vids.date = (
            SELECT MAX(vids_inner.date) FROM vids AS vids_inner
            WHERE (
                vids_inner.polling_district = voters.polling_district AND 
                vids_inner.elector_number = voters.elector_number
            )
        )
        """
    if selected_ward:
        query +=f"WHERE polling_districts.ward = '{selected_ward}'"
    if len(road_groups) > 0:
        query += f"""WHERE 
            road_group IN {tuple(road_groups)} 
        """
    query += """
        ORDER BY
            road_group,
            road,
            voters.elector_number
        """
    data = cursor.execute(query).fetchall()
    return data

def delete_voter(connection, voter):
    cursor = connection.cursor()
    query = f"""
        DELETE FROM voters
        WHERE
            (voters.polling_district = '{voter[0]}' AND voters.elector_number = '{voter[1]}')
    """
    data = cursor.execute(query)
    return data

def fetch_postal_vids(connection, date):
    cursor = connection.cursor()
    cursor.row_factory = dictionary_factory
    data = cursor.execute(
        f"""
        SELECT * 
        FROM vids 
        WHERE date >= '{date}' AND has_voted = '1'
        """
    ).fetchall()
    return data
