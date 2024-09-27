#!/usr/bin/env/ python
import logging
from fastapi import FastAPI, Request
import os
from minio import Minio
from minio.error import S3Error
from fastapi.responses import StreamingResponse
import io
import asyncio
from concurrent.futures import ThreadPoolExecutor
import re

#pipelines
from flows.templates.minio_to_mongo import minio_to_mongo 
from flows.templates.minio_csv_to_minio import minio_csv_to_minio 
from flows.templates.minio_txt_to_minio import minio_txt_to_minio 

logging.basicConfig(level=logging.INFO)

app = FastAPI()
minio_client = Minio(
    f"{os.getenv('MINIO_HOSTNAME', 'localhost')}:9000",
    access_key="password",
    secret_key="password",
    secure=False
)

executor = ThreadPoolExecutor()

async def run_in_threadpool(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)

@app.post("/trigger-etl")
async def trigger_etl(request: Request):

    event_data = await request.json()

    bucket_name = "alphabot-logs-bucket"
    object_name = event_data.get('Records', [{}])[0].get('s3', {}).get('object', {}).get('key', 'Unknown')

    logging.info(f"EVENT_DATA: {event_data}")
    logging.info(f"EVENT_DATA_FILENAME: {object_name}")
    

    # data pipelines
    if(bool(re.match(r'alphabot.*.csv', object_name))):
        target_bucket_name = "alphabot-logs-summary-bucket"
        target_object_name = f"{os.path.splitext(object_name)[0]}_transformed.csv"
        await run_in_threadpool(minio_csv_to_minio, bucket_name, object_name, target_bucket_name, target_object_name)
        await run_in_threadpool(minio_to_mongo, bucket_name, object_name)

    # unstructured/text pipelines
    if(bool(re.match(r'alphabot_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*.txt', object_name))):
        target_bucket_name = "alphabot-logs-summary-bucket"
        target_object_name = f"{os.path.splitext(object_name)[0]}_transformed.txt"
        await run_in_threadpool(minio_txt_to_minio, bucket_name, object_name, target_bucket_name, target_object_name)
    
    return {"message": "ETL pipeline triggered"}

@app.get("/get-object/{bucket_name}/{object_name}")
async def get_object(bucket_name: str, object_name: str):
    try:
        # Get object from Minio
        response = await run_in_threadpool(minio_client.get_object, bucket_name, object_name)
        data = response.read()
        file_data = io.BytesIO(data)

        # Return the file as a response
        return StreamingResponse(file_data, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={object_name}"})
    except S3Error as err:
        return {"error": str(err)}, 404

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

