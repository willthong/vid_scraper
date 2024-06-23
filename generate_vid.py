from fpdf import FPDF
import sqlite3

# Find list of wards, pulled from database (it'll print every road group in that ward)

# Selection options with numbers of voters in the selection


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

        # Title
        self.set_font("open-sans", "B", 20)
        self.set_x(10)
        self.set_y(10)
        self.cell(text="(Unauthorised) Voter ID")

        # Page details
        self.set_y(20)
        self.set_font("open-sans", "", 9)
        connection = sqlite3.connect("voter_data.db")
        connection.row_factory = dictionary_factory
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM voters WHERE road_group = *")

        page_data = (
            ("Constituency", "Huntingdon"),
            ("Ward", "cursor.fetchone()['ward']"),
            ("Road group", "cursor.fetchone()['road_group']"),
            ("Polling district", "cursor.fetchone()['polling_district']"),
            ("Polling place", "Ugh Will hasn't built this yet"),
        )

        with pdf.table(
            width=100, col_widths=(30, 70), first_row_as_headings=False
        ) as table:
            for data_row in page_data:
                row = table.row()
                for datum in data_row:
                    row.cell(datum)


pdf = PDF()
pdf.add_page()

# pdf.set_font("open-sans", "", 16)
# pdf.cell(40, 10, "Hello World!")

pdf.output("output.pdf")
