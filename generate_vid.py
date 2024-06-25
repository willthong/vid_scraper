from fpdf import FPDF
import pprint
import re
import sqlite3

# Find list of PDs, pulled from database (it'll print every road group in that PD)

# Selection options with numbers of voters in the selection

# Default: all PDs
polling_district = "015AD"


def dictionary_factory(cursor, row):
    dictionary = {}
    for index, column in enumerate(cursor.description):
        dictionary[column[0]] = row[index]
    return dictionary


class PDF(FPDF):
    def header(self):

        # Fonts
        self.add_font(
            "open-sans",
            style="",
            fname="fonts/OpenSans-Regular.ttf",
        )
        self.add_font(
            "open-sans",
            style="B",
            fname="fonts/OpenSans-Bold.ttf",
        )

        # Data
        connection = sqlite3.connect(
            "voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES
        )
        cursor = connection.cursor()
        cursor.row_factory = dictionary_factory
        data = cursor.execute(
            """
            SELECT ward, road_group_name, voters.polling_district FROM voters 
            INNER JOIN roads ON roads.road_id = voters.road_id 
            INNER JOIN road_groups ON roads.road_group_id = road_groups.road_group_id 
            WHERE road_groups.polling_district = '015AD'
            LIMIT 1
            """
        ).fetchone()

        page_data = (
            ("Constituency", "Huntingdon"),
            ("Ward", data["ward"]),
            ("Road group", data["road_group_name"]),
            ("Polling district", data["polling_district"]),
            ("Polling place", "Ugh Will hasn't built this yet"),
        )

        # Title
        self.set_font("open-sans", "B", 20)
        self.set_xy(5, 5)

        # Header data
        self.cell(text="(Unauthorised) Voter ID")
        self.set_xy(5, 15)
        self.set_font("open-sans", "", 9)
        with pdf.table(
            width=100,
            col_widths=(30, 70),
            align="LEFT",
            first_row_as_headings=False,
            borders_layout="None",
            line_height=5,
        ) as table:
            for data_row in page_data:
                row = table.row()
                for datum in data_row:
                    row.cell(datum)


pdf = PDF()
pdf.add_page()

connection = sqlite3.connect("voter_data.db", detect_types=sqlite3.PARSE_DECLTYPES)
cursor = connection.cursor()
cursor.row_factory = dictionary_factory
data = cursor.execute(
    """
    SELECT 
        road_group_name as road_group, 
        voter_name as name, address, 
        road_name as road,
        elector_number,
        property_number
    FROM voters 
    INNER JOIN roads ON roads.road_id = voters.road_id 
    INNER JOIN road_groups ON roads.road_group_id = road_groups.road_group_id 
    WHERE road_groups.polling_district = '015AD'
    ORDER BY
        road_group,
        road,
        elector_number
    """
).fetchall()

def order_road_voters(properties: list):
    no_number_properties = [
        voter
        for voter in properties
        if not voter["property_number"]
    ]
    numbered_properties = [
        voter for voter in properties 
        if voter["property_number"]
    ]
    if numbered_properties:
        for property in numbered_properties:
                property["property_just_numbers"] = "".join(
                    re.findall(r'\d*', property["property_number"])
                )
                property["property_text"] = "".join(
                    re.findall(r'[a-z][A-Z]*', property["property_number"])
                )
        numbered_properties.sort(key=lambda x: x.get("property_text", ""))
        numbered_properties.sort(key=lambda x: int(x.get("property_just_numbers", 0)))
    if no_number_properties:
        no_number_properties.sort(key=lambda x: x["address"])
    if not numbered_properties:
        properties = no_number_properties
    elif not no_number_properties:
        properties = numbered_properties
    else:
        properties = no_number_properties + numbered_properties
    return properties

    
road_groups = sorted(set([voter["road_group"] for voter in data]))
for road_group in road_groups:
    roads = sorted(set([voter["road"] for voter in data]))
    for road in roads:
        road_voters = [voter for voter in data if voter["road"] == road]
        road_voters = order_road_voters(road_voters)
        # pprint.pprint([voter["address"] for voter in road_voters])
        # print("\n")

# for voter in data:
#     print(voter["name"], voter["address"])

# pdf.set_font("open-sans", "", 16)
# pdf.cell(40, 10, "Hello World!")

pdf.output("output.pdf")

# Get list of RGs
# Sort streets within that RG alphabetically
# For each street:
# Start a new page
