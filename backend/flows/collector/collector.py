from prefect import task, flow
from prefect.artifacts import create_link_artifact
from prefect import get_run_logger
from minio import Minio
from minio.error import S3Error
import pandas as pd
import json
import io
import os
import shutil
from pathlib import Path
import subprocess
import data_to_csvs
from datetime import datetime, timedelta

# MinIO client configuration
minio_client = Minio(
    f"{os.getenv('MINIO_HOSTNAME', 'localhost')}:9000",
    access_key="password",
    secret_key="password",
    secure=False
)

# Buckets
ALPHABOT_LOGS_MINIO_BUCKET = "alphabot-logs-bucket"

# Dirs
LF_OUTPUT_DIR = Path('logfisher_output')
OUTPUT_DATA_DIR = Path('alphabot_data_files')

# Query
KQL_QUERY_FILE= Path('./query.kql')

# In-memory buffers
output_csv_buffer = io.StringIO()
output_json_buffer = io.StringIO()

@task
def check_fatals():
    logger = get_run_logger()
    logger.info("Starting check_fatals task")
    command = ["adxloginexecute", "--kql-file", "./query.kql", "--output-file", "/dev/stdout"]
    result = subprocess.run(command, capture_output=True, text=True)
    output_csv_buffer.write(result.stdout)
    logger.info("Completed check_fatals task")

@task
def csv_to_grid_id_ts():
    logger = get_run_logger()
    logger.info("Starting csv_to_grid_id_ts task")
    output_csv_buffer.seek(0)
    df = pd.read_csv(output_csv_buffer)
    grid_id_timestamp = df[['__grid_id', 'timestamp']]
    grid_id_timestamp_dict = grid_id_timestamp.set_index('__grid_id').to_dict()['timestamp']
    grid_id_timestamp_json = json.dumps(grid_id_timestamp_dict, indent=4)
    output_json_buffer.write(grid_id_timestamp_json)
    logger.info("Completed csv_to_grid_id_ts task")

@task
def collect_logs_from_lf_output():
    logger = get_run_logger()
    logger.info("Starting collect_logs_from_lf_output task")
    OUTPUT_DATA_DIR.mkdir(exist_ok=True)
    LF_OUTPUT_DIR.mkdir(exist_ok=True)
    for file in LF_OUTPUT_DIR.rglob('alphabot_*txt'):
        if not file.name.startswith('stdout_alphabot_'):
            destination_file = OUTPUT_DATA_DIR / file.name
            if destination_file.exists():
                destination_file.unlink()
            shutil.copy2(file, OUTPUT_DATA_DIR)
    logger.info("All alphabot txt files have been copied to the alphabot_txt_files directory.")
    logger.info("Completed collect_logs_from_lf_output task")

@task
def cleanup():
    logger = get_run_logger()
    logger.info("Starting cleanup task")
    if LF_OUTPUT_DIR.exists():
        shutil.rmtree(LF_OUTPUT_DIR)
    if OUTPUT_DATA_DIR.exists():
        shutil.rmtree(OUTPUT_DATA_DIR)
    LF_OUTPUT_DIR.mkdir(exist_ok=True)
    output_csv_buffer.truncate(0)
    output_csv_buffer.seek(0)
    output_json_buffer.truncate(0)
    output_json_buffer.seek(0)
    logger.info("Completed cleanup task")

@task
def copy_to_minio():
    OUTPUT_DATA_DIR.mkdir(exist_ok=True)
    LF_OUTPUT_DIR.mkdir(exist_ok=True)
    logger = get_run_logger()
    logger.info("Starting copy_to_minio task")
    try:
        for filename in os.listdir(OUTPUT_DATA_DIR):
            file_path = os.path.join(OUTPUT_DATA_DIR, filename)
            minio_client.fput_object(ALPHABOT_LOGS_MINIO_BUCKET, filename, file_path)
            logger.info(f"Uploaded {filename} to {ALPHABOT_LOGS_MINIO_BUCKET}")
    except S3Error as e:
        logger.error(f"An error occurred: {e}")
    logger.info("Completed copy_to_minio task")

@task
def pull_logs_with_logfisher():
    logger = get_run_logger()
    logger.info("Starting pull_logs_with_logfisher task")
    output_json_buffer.seek(0)
    data = json.load(output_json_buffer)
    LF_OUTPUT_DIR.mkdir(exist_ok=True)

    for bot, timestamp in data.items():
        # Parse the timestamp and calculate the start and end dates
        start_date = datetime.strptime(timestamp.split(' ')[0], "%Y-%m-%d")
        end_date = start_date + timedelta(days=2)
        
        # Format the dates for the lf command
        start = start_date.strftime("%Y-%m-%d")
        end = end_date.strftime("%Y-%m-%d")

        # Construct the lf command with --start and --end
        command = f"lf --bot {bot} --start {start} --end {end} --no-prompt --dir {LF_OUTPUT_DIR}"
        logger.info(f"Executing command: {command}")
        subprocess.run(command, shell=True)

        collect_logs_from_lf_output()
        data_to_csvs.convert_all_datalogs_to_csv(directory=OUTPUT_DATA_DIR, remove_source_files=True)
        copy_to_minio()
        cleanup() 

@flow
def fatal_collector():
    logger = get_run_logger()
    logger.info("Starting fatal_collector flow")
    cleanup()
    check_fatals()
    csv_to_grid_id_ts()
    pull_logs_with_logfisher()
    logger.info("Completed fatal_collector flow")

if __name__ == "__main__":
    fatal_collector()
