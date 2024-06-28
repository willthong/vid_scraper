import csv


polling_stations = []
with open("input/polling_stations.csv", newline="") as file:
    csv_reader = csv.reader(file)
    for row in csv_reader:
        for code in row[1].split(","):
            polling_stations.append((code, row[2]))
print(polling_stations)

# Put it into the polling_district table
