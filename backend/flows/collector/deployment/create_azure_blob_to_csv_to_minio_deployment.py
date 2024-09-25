from prefect import flow
from azure_blob_to_csv_to_minio import azure_blob_to_csv_to_minio

if __name__ == "__main__":
    azure_blob_to_csv_to_minio.deploy(
        name="poll_azure_blobs",
        work_pool_name="work-pool-alpha", # Work pool target
        cron="*/5 * * * *", # Cron schedule (every 5 minutes)
    )

