import json
import pandas as pd
import plotly.express as px

class SummaryParser:
    def __init__(self, summary_file):
        self.summary_file = summary_file
        self.data = []

    def get_move_type(self, src, dest):
        src_area = src.split(":")[0]
        dest_area = dest.split(":")[0]

        if src_area == dest_area:
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

    def get_status(self, description):
        return "Success" if "Success" in description else "Failure"

    def parse_summary(self):
        with open(self.summary_file, "r") as file:
            for line in file:
                if "->" in line:
                    parts = line.split()
                    timestamp = parts[0] + " " + parts[1]
                    src = parts[2]
                    dest = parts[4]
                    status = self.get_status(line)
                    move_type = self.get_move_type(src, dest)
                    self.data.append({
                        "timestamp": timestamp,
                        "src": src,
                        "dest": dest,
                        "status": status,
                        "type": "Vertical" if src.split(".")[-1] != dest.split(".")[-1] else "Horizontal",
                        "description": move_type
                    })

    def save_as_json(self, output_file):
        with open(output_file, "w") as outfile:
            json.dump({"moves": self.data}, outfile, indent=4)
        print(f"Saved JSON to {output_file}")

    def plot_data(self):
        df = pd.DataFrame(self.data)
        df['z_src'] = df['src'].apply(lambda x: int(x.split(".")[-1]))
        df['z_dest'] = df['dest'].apply(lambda x: int(x.split(".")[-1]))

        fig = px.scatter(df, x="timestamp", y="z_src", color="status", hover_data=["src", "dest", "description"])
        fig.update_layout(
            title="Move Events",
            xaxis_title="Timestamp",
            yaxis_title="Z Height",
            height=600,
            template='plotly_dark'
        )
        fig.show()

# Usage
summary_file = './summary.txt'
output_json = './generated_summary.json'

parser = SummaryParser(summary_file)
parser.parse_summary()
parser.save_as_json(output_json)
parser.plot_data()
