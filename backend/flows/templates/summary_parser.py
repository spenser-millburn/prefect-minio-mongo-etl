import pandas as pd
import plotly.express as px

class SummaryParser:
    def __init__(self, summary_file):
        self.summary_file = summary_file
        self.data = []
        self.fatal_faults = {}

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

    def extract_fatal_faults(self):
        """Extract fatal faults and their fault codes."""
        lines_buffer = []
        with open(self.summary_file, 'r') as file:
            for line in file:
                lines_buffer.append(line.strip())
                if len(lines_buffer) > 10:
                    lines_buffer.pop(0)

                if "[FAULT]" in line and "fatal" in line.lower():
                    fault_code = line.split()[3]
                    self.fatal_faults[fault_code] = lines_buffer[:]

    def parse_summary(self):
        """Parse the summary file and populate data with move events."""
        self.data = []  # Ensure the data is reset for a new parse
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

    def plot_data(self):
        """Plot the parsed data and annotate any fatal faults."""
        df = pd.DataFrame(self.data)
        df['z_src'] = df['src'].apply(lambda x: int(x.split(".")[-1]))
        df['z_dest'] = df['dest'].apply(lambda x: int(x.split(".")[-1]))

        fig = px.scatter(df, x="timestamp", y="z_src", color="status", hover_data=["src", "dest", "description"])

        # Annotate fatal faults if they exist
        for i, row in df.iterrows():
            for fault_code, logs in self.fatal_faults.items():
                if row['timestamp'] in logs[0]:
                    fig.add_annotation(
                        x=row['timestamp'],
                        y=row['z_src'],
                        text=f"Fault: {fault_code}",
                        arrowhead=1,
                        yshift=0  # Adjust the position of the annotation
                    )

        fig.update_layout(
            title="Move Events with Z Height and Fault Annotations",
            xaxis_title="Timestamp",
            yaxis_title="Z Height",
            height=600,
            template='plotly_dark'
        )
        fig.show()

# Usage
summary_file = './summary.txt'

parser = SummaryParser(summary_file)
parser.extract_fatal_faults()  # Extract fatal faults first
parser.parse_summary()  # Parse the summary
parser.plot_data()  # Plot the data with annotations for fatal faults
