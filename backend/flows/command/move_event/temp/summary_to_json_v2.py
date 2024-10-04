import json

# Function to determine the move type based on UCC coordinates
def get_move_type(src, dest):
    src_area = src.split(":")[0]
    dest_area = dest.split(":")[0]

    # Example UCC inference logic
    if src_area == "1.4" and dest_area == "1.4":
        return "Rack-to-Rack Move"
    if src_area == "1.4" and dest_area == "1.2":
        return "Rack-to-Deck Move"
    elif src_area == "1.3" and dest_area == "1.2":
        return "Tower-to-Deck Move"
    elif src_area == "1.2" and dest_area == "1.2":
        return "Deck-to-Deck Move"
    elif src_area == "1.4" and dest_area == "1.3":
        return "Rack-to-Tower Move"
    elif src_area == "1.1" and dest_area == "1.1":
        return "Workstation Move"
    else:
        return "Unknown Move"

# Function to convert status based on the description
def get_status(description):
    return "Success" if "Success" in description else "Failure"

# Initialize the list to store move data
move_data = []

# Read the file and process each line
input_file = './summary.txt'
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
            move_type = get_move_type(src, dest)

            # Add the move entry to the list
            move_data.append({
                "timestamp": timestamp,
                "src": src,
                "dest": dest,
                "status": status,
                "type": "Vertical" if src.split(".")[-1] != dest.split(".")[-1] else "Horizontal",
                "description": move_type
            })

# Output the result as JSON
output_json = {
    "moves": move_data
}

# Save the JSON to a file
output_file = "./generated_movesummary_ucc.json"
with open(output_file, "w") as outfile:
    json.dump(output_json, outfile, indent=4)

output_file
