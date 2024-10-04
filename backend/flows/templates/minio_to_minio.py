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
    data = response.read()
    df = pd.read_csv(BytesIO(data))
    return df

@task
def transform_data(df):
    # Perform any data transformation here
    # df['new_column'] = df['existing_column'] * 2  # Example transformation
    return df

@task
def load_to_minio(df, bucket_name, object_name):
    csv_data = df.to_csv(index=False).encode('utf-8')
    minio_client.put_object(
        bucket_name,
        object_name,
        data=BytesIO(csv_data),
        length=len(csv_data),
        content_type='application/csv'
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
def minio_to_minio(source_bucket_name, source_object_name, target_bucket_name, target_object_name):
    print("FLOW","minio_to_minio_template", "BUCKET", source_bucket_name,"OBJECT",  source_object_name) 
    df = extract_from_minio(source_bucket_name, source_object_name)
    transformed_df = transform_data(df)
    load_to_minio(transformed_df, target_bucket_name, target_object_name)
    create_etl_artifact(target_bucket_name, target_object_name)

if __name__ == "__main__":
    source_bucket_name = "alphabot-logs-bucket"
    source_object_name = "cars.csv"
    target_bucket_name = "alphabot-logs-summary-bucket"
    target_object_name = "cars_transformed.csv"
    minion_to_minio(source_bucket_name, source_object_name, target_bucket_name, target_object_name)
