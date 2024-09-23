import logging
from fastapi import FastAPI, Request
from flows.minio_to_mongo import etl_pipeline as minio_to_mongo_pipeline
from flows.minio_to_minio import etl_pipeline as minio_to_minio_pipeline

logging.basicConfig(level=logging.INFO)

app = FastAPI()

@app.post("/trigger-etl")
async def trigger_etl(request: Request):
    event_data = await request.json()
    logging.info(f"EVENT_DATA: {event_data}")
    bucket_name = "alphabot-logs-bucket"
    object_name = event_data.get('Records', [{}])[0].get('s3', {}).get('object', {}).get('key', 'Unknown')
    logging.info(f"EVENT_DATA_FILENAME: {object_name}")
    
    minio_to_minio_pipeline(bucket_name, object_name)
    minio_to_mongo_pipeline(bucket_name, object_name)
    
    return {"message": "ETL pipeline triggered"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
