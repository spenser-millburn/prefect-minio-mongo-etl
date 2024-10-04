import numpy as np
import matplotlib.pyplot as plt
from prefect import flow, task, get_run_logger 
from prefect.artifacts import create_link_artifact
from minio import Minio
from io import BytesIO
import os
from pathlib import Path

# Constants
TIME_WINDOW = 1.0  # sliding window size in seconds
SAMPLE_RATE = 100  # 100 samples per second
MAX_CURRENT = 10.0  # Max motor current (amps)
POSITIVE_THRESHOLD = 9.0  # Threshold for positive limit
NEGATIVE_THRESHOLD = -9.0  # Threshold for negative limit
WINDOW_SIZE = int(TIME_WINDOW * SAMPLE_RATE)

# MinIO client configuration
minio_client = Minio(
    f"{os.getenv('MINIO_HOSTNAME', 'localhost')}:9000",
    access_key="password",
    secret_key="password",
    secure=False
)

# ----------------------------- Tasks -----------------------------

@task
def generate_motor_current_data(duration=10):
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE))
    motor_current = 2 * np.sin(2 * np.pi * 2 * t) + 2 * np.sin(2 * np.pi * 8 * t)
    
    # Add instability: simulate oscillation railing at max limit
    unstable_region = (t > 4) & (t < 6)
    motor_current[unstable_region] = MAX_CURRENT * np.sign(np.sin(10 * np.pi * t[unstable_region]))
    
    return t, motor_current

@task
def count_zero_crossings(data):
    crossings = np.diff(np.sign(data))
    return np.convolve(np.abs(crossings) > 0, np.ones(WINDOW_SIZE), mode='valid')

@task
def count_limit_crossings(data):
    pos_limit_crossings = np.convolve((data >= POSITIVE_THRESHOLD), np.ones(WINDOW_SIZE), mode='valid')
    neg_limit_crossings = np.convolve((data <= NEGATIVE_THRESHOLD), np.ones(WINDOW_SIZE), mode='valid')
    return pos_limit_crossings, neg_limit_crossings

@task
def plot_data(t, motor_current, zero_crossings, pos_crossings, neg_crossings):
    fig, ax = plt.subplots(3, 1, figsize=(10, 8))
    
    # Plot motor current
    ax[0].plot(t, motor_current, label="Motor Current")
    ax[0].set_title("Motor Current Over Time")
    ax[0].set_ylabel("Current (A)")
    ax[0].legend()

    # Plot zero crossings count
    ax[1].plot(t[:len(zero_crossings)], zero_crossings, label="Zero Crossings Count", color='orange')
    ax[1].set_title("Zero Crossings in Sliding Window")
    ax[1].set_ylabel("Count")
    ax[1].legend()

    # Plot limit crossings count
    ax[2].plot(t[:len(pos_crossings)], pos_crossings, label="Positive Limit Crossings", color='green')
    ax[2].plot(t[:len(neg_crossings)], neg_crossings, label="Negative Limit Crossings", color='red')
    ax[2].set_title("Limit Crossings in Sliding Window")
    ax[2].set_ylabel("Count")
    ax[2].set_xlabel("Time (s)")
    ax[2].legend()

    plt.tight_layout()
    return fig

@task
def save_plot(fig, filename='motor_fault_detection_plot.png'):
    fig.savefig(filename)
    return filename

@task
def load_to_minio(file, bucket_name, object_name):
    data = BytesIO(Path(file).read_bytes())
    length = data.getbuffer().nbytes
    minio_client.put_object(
        bucket_name,
        object_name,
        data=data,
        length=length,
        content_type='application/octet_stream'
    )

@task
def create_etl_artifact(bucket_name, object_name):
    link = f"http://localhost:8000/get-object/{bucket_name}/{object_name}"
    create_link_artifact(
        key="etl-output",
        link=link,
        description="## ETL Pipeline Output\n\nData has been successfully extracted from MinIO, transformed, and loaded back into MinIO."
    )

# ----------------------------- Flow -----------------------------

@flow
def motor_fault_detection_flow():
    # Step 1: Generate motor current data
    t, motor_current = generate_motor_current_data()

    # Step 2: Apply detection metrics
    zero_crossings = count_zero_crossings(motor_current)
    pos_crossings, neg_crossings = count_limit_crossings(motor_current)

    # Step 3: Plot results
    fig = plot_data(t, motor_current, zero_crossings, pos_crossings, neg_crossings)

    # Step 4: Save plot
    PLOT_FILE_NAME = "motor_fault_detection_plot.png"
    save_plot(fig, PLOT_FILE_NAME)

    # Step 5: Load saved plot to MinIO
    BUCKET_NAME = "plots"
    OBJECT_NAME = PLOT_FILE_NAME
    load_to_minio(PLOT_FILE_NAME, BUCKET_NAME, OBJECT_NAME)
    create_etl_artifact(BUCKET_NAME, OBJECT_NAME)

# ----------------------------- Run Flow -----------------------------

if __name__ == "__main__":
    motor_fault_detection_flow()
