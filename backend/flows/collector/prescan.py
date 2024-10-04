from datetime import datetime
from prefect import task, flow
from prefect.artifacts import create_link_artifact
from minio import Minio
from pymongo import MongoClient
import os
import json
from io import BytesIO
import re

# MinIO client configuration
minio_client = Minio(
    f"{os.getenv('MINIO_HOSTNAME', 'localhost')}:9000",
    access_key="password",
    secret_key="password",
    secure=False
)

# MongoDB client configuration
mongo_client = MongoClient(f"mongodb://{os.getenv('MONGO_HOSTNAME', 'localhost')}:27017/")
db = mongo_client["loganalysis"]
collection = db["prescan"]

@task 
def extract_from_minio(bucket_name, object_name):
    response = minio_client.get_object(bucket_name, object_name)
    data = response.read().decode('utf-8')
    return data

@task
def process_file_with_fatal_fault(file_content, object_name):
    alphabot_version_pattern = re.compile(r'ALPHABOT_VERSION="([^"]+)"')
    command_line_pattern = re.compile(r'COMMAND_LINE="([^"]+)"')
    grid_id_pattern = re.compile(r'GRID_ID=([A-Za-z0-9]+)')  # Covers both letters and numbers
    os_boot_count_pattern = re.compile(r'OS_BOOT_COUNT=([A-Za-z0-9]+)')
    ts_pattern = re.compile(r'SYSTEM_CORRELATED_US=(\d+)')
    fatal_fault_code_pattern = re.compile(r'id:(\w+)')
    # loop through the first 25 lines for alphabot_version, command_line, grid_id, and os_boot_count
    data = {}
    lines  = file_content.splitlines()
    for line in lines[:25]:
        if "MAIN1 ALPHABOT_VERSION" in line:
            # search for the precompiled patterns in the line
            match_version = alphabot_version_pattern.search(line)
            match_command = command_line_pattern.search(line)
            match_grid = grid_id_pattern.search(line)
            match_ts = ts_pattern.search(line)
            match_boot_count = os_boot_count_pattern.search(line)



            if match_version:
                data["alphabot_version"] = match_version.group(1).strip()
            if match_command:
                data["command_line"] = match_command.group(1).strip()
            if match_grid:
                data["grid_id"] = match_grid.group(1).strip()
            if match_ts:
                data["start_timestamp"] = match_ts.group(1).strip()
            else:
                print("GRID_ID not found or null")
            if match_boot_count:
                data["os_boot_count"] = match_boot_count.group(1).strip()
            else:
                print("OS_BOOT_COUNT not found or null")


    # loop through all lines to find the fatal fault code
    for line in lines:
        if 'Type:Fatal' in line:
            print("found in: ", line)
            match_fault_code = fatal_fault_code_pattern.search(line)
            if match_fault_code:
                print("match: ", match_fault_code)
                data["fatal_fault_code"] = match_fault_code.group(1).strip().strip("fault_")
            break
    data["name"] = os.path.splitext(object_name)[0]
    data ["saved_timestamp"] = datetime.now()
    return data


@task
def load_to_mongodb(record):
    if record:
        collection.insert_one(record)

@task
def create_etl_artifact(bucket_name, object_name):
    link = f"https://{os.getenv('MINIO_HOSTNAME', 'localhost')}:9000/{bucket_name}/{object_name}"
    create_link_artifact(
        key="etl-output",
        link=link,
        description="## ETL Pipeline Output\n\nData has been successfully extracted from MinIO, processed, and loaded into MongoDB."
    )

@flow
def prescan_flow(source_bucket_name, source_object_name, target_bucket_name, target_object_name):
    file_content = extract_from_minio(source_bucket_name, source_object_name)
    record = process_file_with_fatal_fault(file_content, source_object_name)
    load_to_mongodb(record)
    create_etl_artifact(source_bucket_name, source_object_name)

if __name__ == "__main__":
    test_bucket_name = "alphabot-logs-bucket"
    test_object_name = "alphabot_001103_2024_08_10_09_16_52.txt"
    prescan_flow(test_bucket_name, test_object_name, "", "")
