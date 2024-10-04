import io
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import tarfile
import nbformat as nbf
from prefect import flow, task
from prefect.artifacts import create_link_artifact
from nbconvert import HTMLExporter
from nbconvert.preprocessors import ExecutePreprocessor
from minio import Minio
from io import BytesIO
from pathlib import Path
import os

# Determine the directory where the script is located
script_dir = Path(__file__).resolve().parent

# Use the script directory to construct absolute paths
ANALYSIS_CELL_PATH = script_dir / "analysis_cells/relevel_analysis_cell.py"
ANALYSIS_CELL = open(ANALYSIS_CELL_PATH, 'r').read()

# MinIO client configuration
minio_client = Minio(
    f"{os.getenv('MINIO_HOSTNAME', 'localhost')}:9000",
    access_key="password",
    secret_key="password",
    secure=False
)

@task
def extract_from_minio(bucket_name, object_name):
    response = minio_client.get_object(bucket_name, object_name)
    data = response.read()
    
    # Write the CSV data to a disk file
    data_path = script_dir / object_name  # Save the CSV file using the object_name
    with open(data_path, 'wb') as f:
        f.write(data)
    
    return data_path  # Return the file path instead of a buffer

class NotebookAnalysisPackager:
    def __init__(self, analysis_cell_folder, data_path):
        self.analysis_cell_folder = script_dir / analysis_cell_folder
        self.data_path = script_dir / data_path
        self.notebook_path = script_dir / f"{os.path.splitext(data_path)[0]}-analysis.ipynb"
        self.analysis_path = script_dir / "analysis.py"
        self.tarball_path = script_dir / f"{os.path.splitext(data_path)[0]}-analysis.tar.gz"

    def get_cell_files(self):
        """Get all _analysis_cell.py files in the folder"""
        return list(self.analysis_cell_folder.glob("*_analysis_cell.py"))

    def get_analysis_files(self):
        """Get all _analysis.py files in the folder"""
        return list(self.analysis_cell_folder.glob("*_analysis.py"))

    def create_analysis(self):
        """Concatenate all _analysis.py files into a single analysis.py file"""
        analysis_files = self.get_analysis_files()
        with open(self.analysis_path, 'w') as analysis_file:
            for file_path in analysis_files:
                with open(file_path, 'r') as f:
                    analysis_file.write(f.read())
                    analysis_file.write("\n")  # Ensure there’s a new line between each file’s content

    def create_notebook(self):
        """Create a notebook with one cell for each _analysis_cell.py file"""
        nb = nbf.v4.new_notebook()
        cells = []
        cell_files = self.get_cell_files()

        for cell_file in cell_files:
            with open(cell_file, 'r') as f:
                cell_content = f.read()
                cells.append(nbf.v4.new_code_cell(cell_content))

        nb['cells'] = cells

        with open(self.notebook_path, 'w') as notebook_file:
            nbf.write(nb, notebook_file)

    def convert_notebook_to_html(self):
        """Convert the generated notebook to HTML"""
        with open(self.notebook_path, 'r') as notebook_file:
            notebook = nbf.read(notebook_file, as_version=4)

        ep = ExecutePreprocessor(timeout=600, kernel_name='python3')
        ep.preprocess(notebook, {'metadata': {'path': str(script_dir)}})

        html_exporter = HTMLExporter()
        html_exporter.exclude_input = True
        html_exporter.embed_images = True

        html_data, resources = html_exporter.from_notebook_node(notebook)

        with open(self.notebook_path.with_suffix('.html'), 'w') as html_file:
            html_file.write(html_data)

        return html_data.encode('utf-8')

    def create_tarball(self):
        """Create a tarball that includes the analysis.py, notebook, and data"""
        with tarfile.open(self.tarball_path, mode="w:gz") as tar:
            tar.add(self.notebook_path, arcname=self.notebook_path.name)
            tar.add(self.analysis_path, arcname=self.analysis_path.name)
            tar.add(self.data_path, arcname=self.data_path.name)

        with open(self.tarball_path, 'rb') as tar_file:
            tarball_data = tar_file.read()

        return tarball_data

    def run(self):
        """Run all the steps to create the notebook, analysis.py, and tarball"""
        self.create_analysis()
        self.create_notebook()
        tarball_data = self.create_tarball()
        html_data = self.convert_notebook_to_html()
        return html_data, tarball_data

@task
def prepare_analysis(data_path):
    packager = NotebookAnalysisPackager(
        analysis_cell_folder= script_dir / "analysis_cells", 
        data_path=data_path
    )

    # Return the frozen HTML page and tarball of the built analysis
    html_data, tarball_data = packager.run()
    return html_data, tarball_data

@task
def load_to_minio(data, bucket_name, object_name):
    minio_client.put_object(
        bucket_name,
        object_name,
        data=BytesIO(data),
        length=len(data),
        content_type='application/csv'
    )

@task
def create_etl_artifact(bucket_name, object_name, artifact_key_label):
    link = f"http://localhost:8000/get-object/{bucket_name}/{object_name}"
    create_link_artifact(
        key=artifact_key_label,
        link=link,
        description="## ETL Pipeline Output\n\nData has been successfully extracted from MinIO, transformed, and loaded back into MinIO."
    )

@flow
def controls_report_flow(source_bucket_name, source_object_name, target_bucket_name, target_object_name):
    csv_data_path = extract_from_minio(source_bucket_name, source_object_name)  # Now returns a file path
    html_data, tarball_data = prepare_analysis(csv_data_path)  # Pass file path instead of buffer

    tarball_obj_name = f"{os.path.splitext(source_object_name)[0]}-analysis.tar.gz"
    load_to_minio(tarball_data, target_bucket_name, tarball_obj_name)
    create_etl_artifact(target_bucket_name, tarball_obj_name, "ipynb-analysis")

    html_obj_name = f"{os.path.splitext(source_object_name)[0]}-report.html"
    load_to_minio(html_data, target_bucket_name, html_obj_name)
    create_etl_artifact(target_bucket_name, html_obj_name, "html-report")

if __name__ == "__main__":
    source_bucket_name = "alphabot-logs-bucket"
    source_object_name = "alphabot_000277_2024_07_08_11_43_59-data.csv"
    target_bucket_name = "plots"
    target_object_name = "relevel_analysis_log.html"
    controls_report_flow(source_bucket_name, source_object_name, target_bucket_name, target_object_name)
