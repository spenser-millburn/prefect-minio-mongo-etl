#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
from pymongo import MongoClient

# pipeline configuration
from config import PIPELINE_CONFIGS, BUCKET_CONFIGS

logging.basicConfig(level=logging.INFO)

app = FastAPI()
minio_client = Minio(
    f"{os.getenv('MINIO_HOSTNAME', 'localhost')}:9000",
    access_key="password",
    secret_key="password",
    secure=False
)

from pymongo import MongoClient
mongo_client = MongoClient(f"mongodb://{os.getenv('MONGO_HOSTNAME', 'localhost')}:27017/")
db = mongo_client["loganalysis"]
collection = db["prescan"]

executor = ThreadPoolExecutor()

async def run_flow(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)

async def filter_runs(object_name):
    #check the mongo db record for the log, this was generated during prescan
    query = {"name": os.path.splitext(object_name)[0]}
    prescan_metadata = collection.find_one(query, sort=[("saved_timestamp", -1)])
    matching_pipelines = []

    # Iterate over pipeline configs and collect all matching pipelines
    for config in PIPELINE_CONFIGS:

        try:
            logging.warning(f"[ START CHECKS ] Starting run criteria checks for flow: ({config.prefect_flow.__name__})")

            fatal_fault = prescan_metadata.get("fatal_fault_code") if prescan_metadata else None

            # Validate object_name and regex pattern for any potential issues
            if not object_name or not config.regex_trigger:
                logging.error(f"[ ERROR ] Missing or invalid object_name or regex_trigger: object_name={object_name}, regex_trigger={config.regex_trigger}")
                continue

            # Guard to filter on type of file
            if not re.match(config.regex_trigger, object_name):
                logging.warning(f"[ END CHECKS ] not running flow: ({config.prefect_flow.__name__}) [{object_name}] does not match regex [{config.regex_trigger}]")
                continue

            logging.warning(f"[ GUARD ][{config.prefect_flow.__name__}] OBJ_NAME_REGEX_TRIGGER_MATCH: [{object_name}] matches [{config.regex_trigger}]")

            # Ensure os.path.splitext doesn't cause errors by checking object_name validity
            try:
                dest_obj_name = f"{os.path.splitext(object_name)[0]}{config.dest_obj_suffix}"
            except Exception as e:
                logging.error(f"[ ERROR ] Failed to parse object name: {object_name}, Error: {str(e)}")
                continue

            matching_pipelines.append((config.prefect_flow, config.src, object_name, config.dest, dest_obj_name))
        except Exception as e:
            logging.error(f"[ CRITICAL ERROR ] Exception occurred during run criteria checks: {str(e)}")
        return matching_pipelines

@app.post("/trigger-etl")
async def trigger_etl(request: Request):
    # collect metadata from minio bucket notify event
    event_data = await request.json()

    object_name = event_data.get('Records', [{}])[0].get('s3', {}).get('object', {}).get('key', 'Unknown')

    logging.info(f"EVENT_DATA: {event_data}")
    logging.info(f"EVENT_DATA_FILENAME: {object_name}")

    #check filters:
    matching_pipelines = await filter_runs(object_name=object_name)
    
    # Run all matching pipelines concurrently
    if matching_pipelines:
        await asyncio.gather(*(run_flow(flow, src, obj_name, dest, dest_obj_name) for flow, src, obj_name, dest, dest_obj_name in matching_pipelines))

    return {"message": f"{len(matching_pipelines)} ETL pipeline(s) triggered"}

@app.get("/get-object/{bucket_name}/{object_name}")
async def get_object(bucket_name: str, object_name: str):
    try:
        # get object from Minio
        response = await run_flow(minio_client.get_object, bucket_name, object_name)
        data = response.read()
        file_data = io.BytesIO(data)

        # return the file as a response
        return StreamingResponse(file_data, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={object_name}"})
    except S3Error as err:
        return {"error": str(err)}, 404

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
