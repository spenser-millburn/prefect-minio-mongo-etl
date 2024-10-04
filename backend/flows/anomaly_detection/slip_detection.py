import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from prefect import flow, task
from prefect import get_run_logger
from prefect.artifacts import create_link_artifact
from joblib import dump, load
from minio import Minio
from io import BytesIO
import os
from pathlib import Path

# MinIO client configuration
minio_client = Minio(
    f"{os.getenv('MINIO_HOSTNAME', 'localhost')}:9000",
    access_key="password",
    secret_key="password",
    secure=False
)

# ----------------------------- Tasks -----------------------------

@task
def generate_wheel_data():
    """Task: Generate synthetic wheel speed and robot velocity data.
    
    Generates synthetic data representing wheel speeds and actual robot velocities, 
    with some data representing wheel slip.
    
    Returns:
    pandas DataFrame: DataFrame containing wheel speeds, robot velocity, and labels.
    """
    logger = get_run_logger()
    np.random.seed(42)
    
    # Simulate normal wheel data
    wheel_speed = np.random.normal(10.0, 0.5, 1000)  # Normal wheel speed (m/s)
    robot_velocity = np.random.normal(10.0, 0.5, 1000)  # Normal robot velocity (m/s)

    # Simulate wheel slip data where wheel speed is high but robot velocity is low
    slip_wheel_speed = np.random.normal(10.0, 0.5, 100)  # High wheel speed
    slip_robot_velocity = np.random.normal(5.0, 0.2, 100)  # Low robot velocity during slip
    
    # Combine normal and slip data
    wheel_speeds = np.concatenate([wheel_speed, slip_wheel_speed])
    robot_velocities = np.concatenate([robot_velocity, slip_robot_velocity])
    labels = np.array([0] * len(wheel_speed) + [1] * len(slip_wheel_speed))  # 0: No slip, 1: Slip
    
    # Create DataFrame for easier handling
    df = pd.DataFrame({
        'wheel_speed': wheel_speeds,
        'robot_velocity': robot_velocities,
        'label': labels
    })
    
    logger.info("Wheel and robot velocity data generated!")
    return df

@task
def split_data(df):
    """Task: Split data into training and test sets.
    
    Parameters:
    df (pandas DataFrame): DataFrame containing wheel speeds, robot velocity, and labels.
    
    Returns:
    tuple: Tuple containing the training and test sets (X_train, X_test, y_train, y_test).
    """
    logger = get_run_logger()
    X_train, X_test, y_train, y_test = train_test_split(
        df[['wheel_speed', 'robot_velocity']],
        df['label'],
        test_size=0.2,
        random_state=42
    )
    logger.info("Data split into training and test sets!")
    return X_train, X_test, y_train, y_test

@task
def train_anomaly_model(X_train):
    """Task: Train an Isolation Forest for anomaly detection.
    
    Trains an Isolation Forest model to detect wheel slip anomalies based on differences
    between wheel speed and robot velocity.
    
    Parameters:
    X_train (pandas DataFrame): Training set features (wheel speed and robot velocity).
    
    Returns:
    IsolationForest: Trained Isolation Forest model.
    """
    logger = get_run_logger()
    model = IsolationForest(contamination=0.1, random_state=42)
    model.fit(X_train)
    
    logger.info("Anomaly detection model trained successfully!")
    return model

@task
def evaluate_model(model, X_test, y_test):
    """Task: Evaluate the model on the test set.
    
    Evaluates the trained anomaly detection model on the test set.
    
    Parameters:
    model (IsolationForest): Trained Isolation Forest model.
    X_test (pandas DataFrame): Test set features.
    y_test (pandas Series): Test set labels.
    """
    logger = get_run_logger()
    
    # Predict anomalies (-1 for anomalies, 1 for normal)
    y_pred = model.predict(X_test)
    
    # Convert model output to binary labels (1 for slip, 0 for no slip)
    y_pred = np.where(y_pred == -1, 1, 0)
    
    # Print evaluation metrics
    logger.info("Classification Report:")
    logger.info(classification_report(y_test, y_pred))
    logger.info(f"Accuracy: {accuracy_score(y_test, y_pred)}")

@task
def save_model(model, filename='wheel_slip_detection_model.joblib'):
    """Task: Save the trained anomaly detection model to a file.
    
    Parameters:
    model (IsolationForest): Trained Isolation Forest model.
    filename (str): Filename to save the model.
    """
    logger = get_run_logger()
    try:
        dump(model, filename)
        logger.info(f"Model saved to {filename}!")
    except Exception as e:
        logger.error(f"Failed to save model to {filename}: {e}")

@task
def load_and_predict(filename, new_wheel_data):
    """Task: Load the trained model and use it for predictions on new wheel speed and robot velocity data.
    
    Loads the trained model and predicts potential wheel slip based on new data.
    
    Parameters:
    filename (str): Filename to load the model from.
    new_wheel_data (numpy array): Array of new wheel speed and robot velocity data.
    
    Returns:
    numpy array: Predicted labels (0: No slip, 1: Slip).
    """
    logger = get_run_logger()
    try:
        # Load the trained model from the file
        model = load(filename)
        logger.info(f"Model loaded from {filename}")
    except FileNotFoundError as e:
        logger.error(f"File not found: {filename}")
        raise e
    except Exception as e:
        logger.error(f"Failed to load model from {filename}: {e}")
        raise e
    
    # Predict anomalies
    predictions = model.predict(new_wheel_data)
    
    # Convert model output to binary labels (1 for slip, 0 for no slip)
    predictions = np.where(predictions == -1, 1, 0)
    
    # Log predictions
    logger.info(f"Predicted wheel slip labels: {predictions}")
    
    return predictions

@task
def load_to_minio(file, bucket_name, object_name):
    """Task: Save the model to MinIO storage."""
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
    """Task: Create an ETL artifact with a link to the saved model in MinIO."""
    link = f"http://localhost:8000/get-object/{bucket_name}/{object_name}"
    create_link_artifact(
        key="etl-output",
        link=link,
        description="## ETL Pipeline Output\n\nModel has been saved in MinIO for wheel slip detection."
    )

# ----------------------------- Flow -----------------------------

@flow
def wheel_slip_detection_flow():
    """The main Prefect flow orchestrating the wheel slip detection tasks."""
    # Step 1: Generate wheel speed and robot velocity data
    df = generate_wheel_data()
    
    # Step 2: Split data into training and test sets
    X_train, X_test, y_train, y_test = split_data(df)
    
    # Step 3: Train the anomaly detection model
    model = train_anomaly_model(X_train)
    
    # Step 4: Evaluate the model on the test set
    evaluate_model(model, X_test, y_test)
    
    # Step 5: Save the trained model
    MODEL_FILE_NAME = "wheel_slip_detection_model.joblib"
    save_model(model=model, filename=MODEL_FILE_NAME)
    
    # Step 6: Load saved model and make predictions on new data
    new_wheel_data = np.array([[10.2, 9.8], [10.0, 4.5], [9.9, 9.9]])  # Simulate new wheel and velocity data
    load_and_predict(MODEL_FILE_NAME, new_wheel_data)
    
    # Step 7: Load saved model to MinIO
    BUCKET_NAME = "models"
    OBJECT_NAME = MODEL_FILE_NAME
    load_to_minio(MODEL_FILE_NAME, BUCKET_NAME, OBJECT_NAME)
    create_etl_artifact(BUCKET_NAME, OBJECT_NAME)

# ----------------------------- Run Flow -----------------------------

if __name__ == "__main__":
    wheel_slip_detection_flow()
