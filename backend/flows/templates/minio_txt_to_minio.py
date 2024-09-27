from prefect import task, flow
from prefect.artifacts import create_link_artifact
from minio import Minio
import pandas as pd
from io import BytesIO
import os

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
    lines = response.read()
    return lines

@task
def transform_data(lines):
    # Perform any data transformation here
    return lines

@task
def load_to_minio(lines, bucket_name, object_name):
    minio_client.put_object(
        bucket_name,
        object_name,
        data=BytesIO(lines),
        length=len(lines),
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
def minio_txt_to_minio(source_bucket_name, source_object_name, target_bucket_name, target_object_name):
    print("BUCKET", source_bucket_name,"OBJECT",  source_object_name) 
    lines = extract_from_minio(source_bucket_name, source_object_name)
    transformed_lines = transform_data(lines)
    load_to_minio(transformed_lines, target_bucket_name, target_object_name)
    create_etl_artifact(target_bucket_name, target_object_name)

if __name__ == "__main__":
    source_bucket_name = "alphabot-logs-bucket"
    source_object_name = ""
    target_bucket_name = "alphabot-logs-summary-bucket"
    target_object_name = ""
    minio_txt_to_minio(source_bucket_name, source_object_name, target_bucket_name, target_object_name)
