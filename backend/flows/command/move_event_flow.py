from prefect import task, flow
from prefect.artifacts import create_link_artifact
from minio import Minio
import pandas as pd
import plotly.express as px
from io import BytesIO, StringIO
import os

# MinIO client configuration
minio_client = Minio(
    f"{os.getenv('MINIO_HOSTNAME', 'localhost')}:9000",
    access_key="password",
    secret_key="password",
    secure=False
)

class SummaryParser:
    def __init__(self, summary_data):
        self.summary_data = summary_data
        self.data = []
        self.fatal_faults = {}

    def get_move_type(self, src, dest):
        src_area = src.split(":")[0]
        dest_area = dest.split(":")[0]

        if src_area == dest_area:
            return "Rack-to-Rack Move"
        if src_area == "1.4" and dest_area == "1.2":
            return "Rack-to-Deck Move"
        elif src_area == "1.4" and dest_area == "1.2":
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
        for line in self.summary_data.splitlines():
            lines_buffer.append(line.strip())
            if len(lines_buffer) > 10:
                lines_buffer.pop(0)

            if "[FAULT]" in line and "fatal" in line.lower():
                fault_code = line.split()[3]
                self.fatal_faults[fault_code] = lines_buffer[:]

    def parse_summary(self):
        """Parse the summary data and populate data with move events."""
        self.data = []  # Ensure the data is reset for a new parse
        for line in self.summary_data.splitlines():
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

        # Define color mapping for status
        color_discrete_map = {"Success": "green", "Failure": "red"}

        fig = px.scatter(df, x="timestamp", y="z_src", color="status", hover_data=["src", "dest", "description"],
                         color_discrete_map=color_discrete_map)

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
        return fig

@task
def extract_from_minio(bucket_name, object_name):
    response = minio_client.get_object(bucket_name, object_name)
    lines = response.read().decode('utf-8')
    return lines

@task
def transform_data(lines):
    return lines

@task
def create_plot_artifact(summary_data):
    parser = SummaryParser(summary_data)
    parser.extract_fatal_faults()
    parser.parse_summary()
    fig = parser.plot_data()
    buffer = StringIO()
    fig.write_html(buffer)
    buffer.seek(0)
    return buffer

@task
def upload_plot_to_minio(plot_buffer, bucket_name, object_name):
    plot_buffer.seek(0)
    data = plot_buffer.getvalue().encode('utf-8')  # Encode the string to bytes
    minio_client.put_object(
        bucket_name,
        object_name,
        data=BytesIO(data),  # Pass the buffer directly
        length=len(data),  # Use the length of the encoded data
        content_type='text/html'
    )

@task
def create_plot_artifact_link(bucket_name, object_name):
    link = f"http://localhost:8000/get-object/{bucket_name}/{object_name}"
    create_link_artifact(
        key="plot-output",
        link=link,
        description="## Plot Output\n\nThe plot has been successfully created and uploaded to MinIO."
    )

@flow
def logfisher_summary_to_move_events_plot_flow(source_bucket_name, source_object_name, target_bucket_name, target_object_name):
    lines = extract_from_minio(source_bucket_name, source_object_name)
    summary_data = transform_data(lines)
    plot_buffer = create_plot_artifact(summary_data)
    upload_plot_to_minio(plot_buffer, target_bucket_name, target_object_name)
    create_plot_artifact_link(target_bucket_name, target_object_name)

if __name__ == "__main__":
    source_bucket_name = "logfisher-summaries"
    source_object_name = "alphabot_000050_2024_08_09_08_15_26_summary.txt"
    target_bucket_name = "plots"
    target_object_name = "alphabot_000050_2024_08_09_08_15_26_move_events.html"
    logfisher_summary_to_move_events_plot_flow(source_bucket_name, source_object_name, target_bucket_name, target_object_name)
