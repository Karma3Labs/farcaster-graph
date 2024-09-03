import os
import csv
import re

# Specify the directory containing the CSV files
directory = 'backup/'

# Specify the output file
output_file = 'combined_dataset.csv'

# Function to extract numeric offset from filename
def extract_offset(filename):
    match = re.search(r'offset_(\d+)', filename)
    return int(match.group(1)) if match else 0

# Get list of files sorted by numeric offset
files = sorted(
    (f for f in os.listdir(directory) if f.startswith('karma3-labs.dataset_k3l_cast_localtrust_offset_') and f.endswith('.csv')),
    key=extract_offset
)

# Initialize a flag to handle headers
header_saved = False

# Open the output file in write mode
with open(output_file, 'w', newline='') as outfile:
    csv_writer = csv.writer(outfile)

    # Iterate over each sorted file
    for filename in files:
        file_path = os.path.join(directory, filename)

        # Open each CSV file in read mode
        with open(file_path, 'r') as infile:
            csv_reader = csv.reader(infile)

            # Iterate over the rows in the input file
            for i, row in enumerate(csv_reader):
                # Write the header only once
                if i == 0:
                    if not header_saved:
                        csv_writer.writerow(row)
                        header_saved = True
                else:
                    # Skip empty rows
                    if any(cell.strip() for cell in row):
                        csv_writer.writerow(row)

print(f'Combined CSV file saved as {output_file}')