from prefect import task, flow
from prefect.artifacts import create_link_artifact
from minio import Minio
from minio.error import S3Error
import pandas as pd
import json
import os
import shutil
from pathlib import Path
import subprocess
import data_to_csvs

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

@task
def check_fatals():
    command = ["adxloginexecute", "--kql-file", "./fatal_all_sites_between_2_and_3_days_ago.kql", "--output-file", "./output.csv"]
    subprocess.run(command)

@task
def csv_to_grid_id_ts():
    df = pd.read_csv('output.csv')
    grid_id_timestamp = df[['__grid_id', 'timestamp']]
    grid_id_timestamp_dict = grid_id_timestamp.set_index('__grid_id').to_dict()['timestamp']
    grid_id_timestamp_json = json.dumps(grid_id_timestamp_dict, indent=4)
    with open('output.json', 'w') as file:
        file.write(grid_id_timestamp_json)

@task
def collect_logs_from_lf_output():
    OUTPUT_DATA_DIR.mkdir(exist_ok=True)
    LF_OUTPUT_DIR.mkdir(exist_ok=True)
    for file in LF_OUTPUT_DIR.rglob('alphabot_*-data*txt'):
        if not file.name.startswith('stdout_alphabot_'):
            destination_file = OUTPUT_DATA_DIR / file.name
            if destination_file.exists():
                destination_file.unlink()
            shutil.copy2(file, OUTPUT_DATA_DIR)
    print("All alphabot txt files have been copied to the alphabot_txt_files directory.")

@task
def cleanup():
    if LF_OUTPUT_DIR.exists():
        shutil.rmtree(LF_OUTPUT_DIR)
    if OUTPUT_DATA_DIR.exists():
        shutil.rmtree(OUTPUT_DATA_DIR)
    LF_OUTPUT_DIR.mkdir(exist_ok=True)
    for file_name in ["./output.json", "./output.csv"]:
        if os.path.exists(file_name):
            os.remove(file_name)

@task
def copy_to_minio():
    try:
        for filename in os.listdir(OUTPUT_DATA_DIR):
            file_path = os.path.join(OUTPUT_DATA_DIR, filename)
            minio_client.fput_object(ALPHABOT_LOGS_MINIO_BUCKET, filename, file_path)
            print(f"Uploaded {filename} to {ALPHABOT_LOGS_MINIO_BUCKET}")
    except S3Error as e:
        print(f"An error occurred: {e}")

@task
def pull_logs_with_logfisher():
    with open('output.json', 'r') as file:
        data = json.load(file)
    LF_OUTPUT_DIR.mkdir(exist_ok=True)
    for bot, timestamp in data.items():
        date = timestamp.split(' ')[0]
        command = f"lf --bot {bot} --date {date} --no-prompt --dir {LF_OUTPUT_DIR}"
        print(command)
        subprocess.run(command, shell=True)
        collect_logs_from_lf_output()
        data_to_csvs.convert_all_datalogs_to_csv(OUTPUT_DATA_DIR)
        copy_to_minio()
        cleanup()

@flow
def azure_blob_to_csv_to_minio():
    cleanup()
    check_fatals()
    csv_to_grid_id_ts()
    pull_logs_with_logfisher()

if __name__ == "__main__":
    main_flow()
