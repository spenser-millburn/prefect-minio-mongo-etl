from prefect import task, flow
from prefect.artifacts import create_link_artifact
from minio import Minio
from pymongo import MongoClient
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

# MongoDB client configuration
mongo_client = MongoClient(f"mongodb://{os.getenv('MONGO_HOSTNAME', 'localhost')}:27017/")
db = mongo_client["loganalysis"]
collection = db["loganalysis_collection"]

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
def load_to_mongodb(df):
    records = df.to_dict(orient='records')
    collection.insert_many(records)

@task
def create_etl_artifact(bucket_name, object_name):
    link = f"https://{os.getenv('MINIO_HOSTNAME', 'localhost')}:9000/{bucket_name}/{object_name}"
    create_link_artifact(
        key="etl-output",
        link=link,
        description="## ETL Pipeline Output\n\nData has been successfully extracted from MinIO, transformed, and loaded into MongoDB."
    )

@flow
def etl_pipeline(bucket_name, object_name):
    df = extract_from_minio(bucket_name, object_name)
    transformed_df = transform_data(df)
    load_to_mongodb(transformed_df)
    create_etl_artifact(bucket_name, object_name)

if __name__ == "__main__":
    test_bucket_name = "alphabot-logs-bucket"
    test_object_name = "13.csv"
    etl_pipeline(test_bucket_name, test_object_name)
