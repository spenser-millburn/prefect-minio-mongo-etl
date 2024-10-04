from prefect import task, flow
from minio import Minio
from pymongo import MongoClient
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
collection = db["prescan"]

@task
def query_mongodb_for_fault():
    # Query the MongoDB collection for records with a specific fatal fault code
    records = collection.find({"fatal_fault_code": "0C_05_00"})
    return [record["name"] for record in records]

@task
def transfer_log_to_minio(source_bucket, dest_bucket, object_name):
    # Get the object from the source bucket
    response = minio_client.get_object(source_bucket, object_name)
    data = response.read()

    # Put the object into the destination bucket
    minio_client.put_object(dest_bucket, object_name, data, len(data))

@flow
def from_prescan_to_mongo_flow(source_bucket, dest_bucket):
    # Query MongoDB for logs with the specified fault code
    object_names = query_mongodb_for_fault()

    # Transfer each log from the source bucket to the destination bucket
    for object_name in object_names:
        transfer_log_to_minio(source_bucket, dest_bucket, object_name)

if __name__ == "__main__":
    source_bucket = "staging-bucket"
    dest_bucket = "alphabot_logs_bucket"
    from_prescan_to_mongo_flow(source_bucket, dest_bucket)
