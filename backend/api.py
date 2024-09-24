import logging
from fastapi import FastAPI, Request
from flows.minio_to_mongo import etl_pipeline as minio_to_mongo_pipeline
from flows.minio_to_minio import etl_pipeline as minio_to_minio_pipeline
import os

logging.basicConfig(level=logging.INFO)

app = FastAPI()

@app.post("/trigger-etl")
async def trigger_etl(request: Request):
    event_data = await request.json()
    bucket_name = "alphabot-logs-bucket"
    object_name = event_data.get('Records', [{}])[0].get('s3', {}).get('object', {}).get('key', 'Unknown')

    logging.info(f"EVENT_DATA: {event_data}")
    logging.info(f"EVENT_DATA_FILENAME: {object_name}")
    
    #Pulling data from minio transforming and putting into a mongo db
    minio_to_mongo_pipeline(bucket_name, object_name)

    #Pulling data from minio transforming and putting into a different minio bucket
    target_bucket_name = "alphabot-logs-summary-bucket"
    target_object_name = f"{os.path.splitext(object_name)[0]}_transformed.csv"
    minio_to_minio_pipeline(bucket_name, object_name, target_bucket_name, target_object_name)
    
    return {"message": "ETL pipeline triggered"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
