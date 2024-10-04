# ETL Pipelines

## Overview
This project is an ETL (Extract, Transform, Load) pipeline built using FastAPI, MinIO, and MongoDB. It processes log files stored in MinIO, applies various transformations, and stores the results in different destinations such as MinIO buckets or MongoDB. The pipeline is triggered by events from MinIO and uses Prefect for flow management.

## Components
- **prefect.io**: Manages the execution of ETL flows.
- **FastAPI**: Serves as the web server to handle incoming requests and trigger ETL processes.
- **MinIO**: Acts as the object storage for log files and transformed data. When files are deposited into minio buckets, pipelines are started on them via webhooks.
- **MongoDB**: Stores metadata and processed data.

## Features
- **Event-Driven**: Uses MinIO bucket notifications to trigger ETL processes.
- **Concurrency**: Flows are executed asynchronousy and can run on distributed infrastructure. 
- **Declarative Configuration**: Allows easy configuration of ETL pipelines and triggers, see config.py

## Setup Instructions

### Prerequisites
- Docker and Docker Compose 

### Installation
1. **Clone the Repository**
   ```
   git clone git@gitlab.com:alertinnovation/embd/internal-tools/etl-pipelines.git 
   cd etl-pipelines
   ```
1. **Start the System**
   ```
   docker compose up
   ```
3. **Configure MinIO and Webhooks**
   Run the configuration script to set up buckets + webhooks:
   ```
   python config.py
   ```
4. **Open the Prefect Dashboard**
- [http://localhost:4200](http://localhost:4200)

4. **Kick off a job**
```
mc cp alphabot_000107_2024_08_13_23_23_07.txt myminio/alphabot-logs-bucket
```
- Pipelines will automatically begin processing, navigate through the prefect UI to download the built artifact or copy down via CLI with `mc`

### Running the Application
1. **Start FastAPI Server**

2. **Trigger ETL Process**
   Send a POST request to `/trigger-etl` with the appropriate event data to start the ETL process.

### Usage
- **Trigger ETL**: use `mc cp log.txt myminio/alphabot-logs-bucket` to kick off pipelines for that log. 

### Configuration
- **Pipeline Configurations**: Modify `PIPELINE_CONFIGS` in the script to add or update ETL pipelines.
- **Bucket Configurations**: Modify `BUCKET_CONFIGS` to manage MinIO bucket settings and webhooks.

### Author 
- spenser millburn - made with love. 

