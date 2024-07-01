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

def fetch_polling_districts(selected_ward):
    connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = connection.cursor()
    data = cursor.execute(
        f"""
        SELECT DISTINCT polling_district
        FROM polling_districts 
        WHERE ward = '{selected_ward}'
        """
    ).fetchall()
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

