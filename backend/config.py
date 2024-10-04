import sys
sys.path.append('./flows/')

from collections import namedtuple
from flows.templates.minio_csv_to_minio import minio_csv_to_minio
from flows.templates.minio_txt_to_minio import minio_txt_to_minio
from flows.templates.minio_to_mongo import minio_to_mongo
from flows.instability.instability import motor_fault_detection_flow
from flows.collector.prescan import prescan_flow
from command.move_event_flow import logfisher_summary_to_move_events_plot_flow
from snapstat import snapstat_fingerprints
from controls_report import controls_report

from logfisher_summary_flow import alphabot_log_to_logfisher_summary_flow

import subprocess
import sys
from minio import Minio
from minio.error import S3Error
import os

ALIAS_NAME = "myminio"
MINIO_URL = os.getenv('MINIO_URL', "http://localhost:9000")
ACCESS_KEY = "password"
SECRET_KEY = "password"

# Initialize MinIO client
client = Minio(
    MINIO_URL.replace("http://", ""),
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY,
    secure=False
)

# Define the namedtuple for pipeline configuration
PipelineConfig = namedtuple('PipelineConfig', ['desc', 'src', 'dest', 'dest_obj_suffix', 'prefect_flow', 'regex_trigger', 'faults_trigger'])

# Define the configurations for the pipelines directly
PIPELINE_CONFIGS = [
    PipelineConfig(
        desc="Generate logfisher summary from alphabot logs",
        src="alphabot-logs-bucket",
        dest="logfisher-summaries",
        dest_obj_suffix="_summary.txt",
        prefect_flow=alphabot_log_to_logfisher_summary_flow,
        regex_trigger=r'alphabot_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*.txt',
        faults_trigger="*",
    ),
    PipelineConfig(
        desc="Generate move events plot from logfisher summary",
        src="logfisher-summaries",
        dest="plots",
        dest_obj_suffix="_move_events.html",
        prefect_flow=logfisher_summary_to_move_events_plot_flow,
        regex_trigger=r'.*_summary.txt',
        faults_trigger="*",
    ),
    PipelineConfig(
        desc="Generate controls report from logs",
        src="alphabot-logs-bucket",
        dest="plots",
        dest_obj_suffix="_controls_report.html",
        prefect_flow=controls_report.controls_report_flow,
        regex_trigger=r'alphabot_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*-data.csv',
        faults_trigger=["05_12_00"," 05_0E_00"],
    ),
    PipelineConfig(
        desc="Generate instability plot from logs",
        src="alphabot-logs-bucket",
        dest="plots",
        dest_obj_suffix="_instability_plot.png",
        prefect_flow=motor_fault_detection_flow,
        regex_trigger=r'alphabot_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*-data.csv',
        faults_trigger=["0C_0B_00"],
    ),
    PipelineConfig(
        desc="Transform TXT logs and store in summary bucket",
        src="alphabot-logs-bucket",
        dest="alphabot-logs-summary-bucket",
        dest_obj_suffix="_transformed.txt",
        prefect_flow=minio_txt_to_minio,
        regex_trigger=r'alphabot_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*.txt',
        faults_trigger="*",
    ),
    PipelineConfig(
        desc="Prescan TXT logs and store metadata in MongoDB",
        src="alphabot-logs-bucket",
        dest="mongo", dest_obj_suffix="none", prefect_flow=prescan_flow, regex_trigger=r'alphabot_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*.txt',
        faults_trigger="*",
    ),
    PipelineConfig(
        desc="Transform CSV logs and store in MongoDB",
        src="alphabot-logs-bucket",
        dest="mongo",
        dest_obj_suffix="none",
        prefect_flow=minio_to_mongo,
        regex_trigger=r'alphabot_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*-data.csv',
        faults_trigger=["disabled, template"],
    ),
    PipelineConfig(
        desc="Transform CSV logs and store in summary bucket",
        src="alphabot-logs-bucket",
        dest="alphabot-logs-s-bucket",
        dest_obj_suffix="_transformed.csv",
        prefect_flow=minio_csv_to_minio,
        regex_trigger=r'alphabot_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*_[0-9]*-data.csv',
        faults_trigger=["disabled, template"],
    ),
    PipelineConfig(
        desc="Generate snapstat fingerprints from logs",
        src="alphabot-logs-bucket",
        dest="alphabot-logs-summary-bucket",
        dest_obj_suffix="_snapstat_fingerprints.txt",
        prefect_flow=snapstat_fingerprints,
        regex_trigger=r'alphabot_snapstat.*.txt',
        faults_trigger=["05_0E_00", "05_12_00"],
    ),
]


# Define the namedtuple for bucket configuration
Bucket = namedtuple('Bucket', ['name', 'notify_webhooks'])

# Example bucket configurations
BUCKET_CONFIGS = [
    Bucket(
        name="alphabot-logs-bucket",
        notify_webhooks=["http://flowsapi:8000/trigger-etl","http://flowsapi:8000/trigger-etl2"]
    ),
    Bucket(
        name="alphabot-logs-summary-bucket",
        notify_webhooks=[""]
    ),
    Bucket(
        name="plots",
        notify_webhooks=[""]
    ),
    Bucket(
        name="logfisher-summaries",
        notify_webhooks=["http://flowsapi:8000/trigger-etl"]
    ),
]

def restart_minio_server():
    try:
        subprocess.run(["mc", "admin", "service", "restart", "myminio"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"Failed to restart service: {e}")
        # Add additional logging or error handling here


def reset_webhooks():
    def get_webhook_configs():
        # Run the mc admin config get command and capture the output
        result = subprocess.run(
            ["mc", "admin", "config", "get", "myminio/", "notify_webhook"],
            capture_output=True,
            text=True
        )
        return result.stdout

    def extract_webhook_names(config_output):
        # Extract webhook names from the config output
        webhook_names = []
        for line in config_output.splitlines():
            if line.startswith("notify_webhook:"):
                webhook_name = line.split()[0].split(":")[1]
                webhook_names.append(webhook_name)
        return webhook_names

    def reset_webhook_configs(webhook_names):
        # Reset each webhook configuration
        for name in webhook_names:
            subprocess.run(["mc", "admin", "config", "reset", "myminio", f"notify_webhook:{name}"])
            print(f"Reset webhook configuration: {name}")
        restart_minio_server()

    config_output = get_webhook_configs()
    webhook_names = extract_webhook_names(config_output)
    reset_webhook_configs(webhook_names)

def configure():

    def set_mc_alias():
        command = ["mc", "alias", "set", ALIAS_NAME, MINIO_URL, ACCESS_KEY, SECRET_KEY]
        result = subprocess.run(command, capture_output=True, text=True)
        print("Alias set successfully." if result.returncode == 0 else f"Failed to set alias.\nError: {result.stderr}")

    set_mc_alias()
    reset_webhooks()
    for config in BUCKET_CONFIGS:
        bucket_name = config.name

        # Check if the bucket already exists
        try:
            if not client.bucket_exists(bucket_name):
                # Create the bucket if it does not exist
                client.make_bucket(bucket_name)
                print(f"Bucket {bucket_name} created.")
            else:
                print(f"Bucket {bucket_name} already exists.")
        except S3Error as err:
            print(f"Error checking/creating bucket {bucket_name}: {err}")

        # Configure webhook for each bucket
        try:
            notify_webhooks = config.notify_webhooks
            if notify_webhooks == [""]:
                continue

            subprocess.run(["mc", "event", "remove", f"{ALIAS_NAME}/{bucket_name}", "--force"])

            # Check existing webhook configuration
            result = subprocess.run(
                ["mc", "admin", "config", "get", f"{ALIAS_NAME}/", f"notify_webhook:{bucket_name}"],
                capture_output=True, text=True
            )
            current_config = result.stdout

            # Set all new webhooks at once
            for i, url in enumerate(config.notify_webhooks):
                subprocess.run([
                    "mc", "admin", "config", "set", f"{ALIAS_NAME}/",
                    f"notify_webhook:{bucket_name}_{i}",
                    f"endpoint={url}",
                    "auth_token=", "queue_limit=0", "queue_dir=",
                    "client_cert=", "client_key="
                ])
                restart_minio_server()
                subprocess.run([
                    "mc", "event", "add", f"{ALIAS_NAME}/{bucket_name}",
                    f"arn:minio:sqs::{bucket_name}_{i}:webhook", "--event", "put"
                ])
                print(f"Webhook configured for bucket {bucket_name}.")
        except Exception as e:
            print(f"Error configuring webhook for bucket {bucket_name}: {e}")

    # Restart MinIO service
    restart_minio_server()
    print("MinIO service restarted.")

    # Set Prefect concurrency limit
    subprocess.run(["prefect", "gcl", "create", "my-concurrency-limit", "--limit", "10", "--slot-decay-per-second", "1.0"])
    print("Prefect concurrency limit set to 10.")

if __name__ == "__main__":
    configure()

