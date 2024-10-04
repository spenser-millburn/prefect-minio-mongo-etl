import io
from prefect import task, flow
from prefect.artifacts import create_link_artifact
from minio import Minio
import pandas as pd
from io import BytesIO
import os
from logfisher_summary_flow.parse_logs import generate_summary_for_single_file
from prefect import get_run_logger#logger = get_run_logger()

# MinIO client configuration
minio_client = Minio(
    f"{os.getenv('MINIO_HOSTNAME', 'localhost')}:9000",
    access_key="password",
    secret_key="password",
    secure=False
)

@task
def extract_from_minio(bucket_name, object_name):
    logger = get_run_logger()
    response = minio_client.get_object(bucket_name, object_name)

    data = response.read().decode('utf-8')
    return data

@task
def transform_data(data):
   logger = get_run_logger()

   lines = generate_summary_for_single_file(
       log_file=io.StringIO(data),
    )

   summary_file= io.StringIO()

   summary_file.writelines(line + "\n" for line in sorted(lines))

   return summary_file.getvalue()

@task
def load_to_minio(data, bucket_name, object_name):

    logger = get_run_logger()
    # logger.info(data) 
    # logger.info("READING NOW") 
    minio_client.put_object(
        bucket_name,
        object_name,
        data=BytesIO(data.encode()),
        length=len(data),
        content_type='application/octet_stream'
    )

@task
def create_etl_artifact(bucket_name, object_name):
    link = f"http://localhost:8000/get-object/{bucket_name}/{object_name}"
    create_link_artifact(
        key="etl-output",
        link=link,
        description="## ETL Pipeline Output\n\nData has been successfully extracted from MinIO, transformed, and loaded back into MinIO."
    )

@flow
def alphabot_log_to_logfisher_summary_flow(source_bucket_name, source_object_name, target_bucket_name, target_object_name):
    data = extract_from_minio(source_bucket_name, source_object_name)
    transformed_data = transform_data(data)
    load_to_minio(transformed_data, target_bucket_name, target_object_name)
    create_etl_artifact(target_bucket_name, target_object_name)

if __name__ == "__main__":
    source_bucket_name = "alphabot-logs-bucket"
    source_object_name = "alphabot_000107_2024_08_13_23_23_07.txt"
    target_bucket_name = "alphabot-logs-summary-bucket"
    target_object_name = "alphabot_000107_2024_08_13_23_23_07_summary.txt"
    alphabot_log_to_logfisher_summary_flow(source_bucket_name, source_object_name, target_bucket_name, target_object_name)
