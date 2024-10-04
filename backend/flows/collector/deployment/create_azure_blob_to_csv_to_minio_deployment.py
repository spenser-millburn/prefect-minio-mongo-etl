from prefect import flow
from fatal_collector import fatal_collector

if __name__ == "__main__":
    fatal_collector.deploy(
        name="poll_azure_blobs",
        work_pool_name="work-pool-alpha", # Work pool target
        cron="*/5 * * * *", # Cron schedule (every 5 minutes)
    )

