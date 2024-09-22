from prefect import task, flow
from minio import Minio
from pymongo import MongoClient
import pandas as pd
from io import BytesIO
from fastapi import FastAPI, Request

# MinIO client configuration
minio_client = Minio(
    "minio:9000",
    access_key="password",
    secret_key="password",
    secure=False
)

# MongoDB client configuration
mongo_client = MongoClient("mongodb://mongo:27017/")
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

@flow
def etl_pipeline(bucket_name, object_name):
    df = extract_from_minio(bucket_name, object_name)
    transformed_df = transform_data(df)
    load_to_mongodb(transformed_df)

app = FastAPI()

@app.post("/trigger-etl")
async def trigger_etl(request: Request):
    event_data = await request.json()
    print(f"EVENT_DATA: {event_data}")
    bucket_name = "alphabot-logs-bucket"
    object_name= event_data.get('Records', [{}])[0].get('s3', {}).get('object', {}).get('key', 'Unknown')
    print(f"EVENT_DATA_FILENAME: {object_name}")
    etl_pipeline(bucket_name,object_name )
    return {"message": "ETL pipeline triggered"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
