import json
from datetime import datetime

# Path to the summary file
input_file = "./summary.txt"

# Initialize the list to store move data
move_data = []

# Function to convert status based on the description
def get_status(description):
    return "Success" if "Success" in description else "Failure"

# Read the file and process each line
with open(input_file, "r") as file:
    for line in file:
        # Check if the line contains move data (ignores faults)
        if "->" in line:
            # Split the line by spaces and extract relevant parts
            parts = line.split()
            timestamp = parts[0] + " " + parts[1]
            src = parts[2]
            dest = parts[4]
            status = get_status(line)
            type_move = "Vertical" if src.split(":")[2] != dest.split(":")[2] else "Horizontal"
            description = "Rack-to-Rack Move" if "Rack" in line else "Deck-to-Deck Move"

            # Add the move entry to the list
            move_data.append({
                "timestamp": timestamp,
                "src": src,
                "dest": dest,
                "status": status,
                "type": type_move,
                "description": description
            })

# Output the result as JSON
output_json = {
    "moves": move_data
}

# Save the JSON to a file
output_file = "./generated_movesummary.json"
with open(output_file, "w") as outfile:
    json.dump(output_json, outfile, indent=4)

print(f"Generated JSON has been saved to {output_file}")
