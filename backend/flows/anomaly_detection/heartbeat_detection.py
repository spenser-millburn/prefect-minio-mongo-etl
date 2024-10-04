import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from joblib import dump, load
from prefect import flow, task
from prefect import get_run_logger
from prefect.artifacts import create_link_artifact
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
def generate_heartbeat_waveforms():
    """Task: Generate synthetic heartbeat waveforms with and without irregularities.
    
    Generates random heartbeat waveforms, with some exhibiting irregular beats, 
    and labels them accordingly.
    
    Returns:
    pandas DataFrame: DataFrame containing the waveforms and their labels.
    """
    logger = get_run_logger()
    np.random.seed(42)
    
    # Generate normal heartbeats (sine wave-like)
    x = np.linspace(0, 10, 100)
    normal_heartbeat = np.sin(x)  # Normal sine wave representing a regular heartbeat

    # Irregular heartbeat with noise and spike
    irregular_heartbeat = np.sin(x) + np.random.normal(0, 0.1, size=len(x))
    irregular_heartbeat[50] += 5  # Add a spike simulating an arrhythmic event

    # Another normal beat (cosine wave)
    normal_cosine_heartbeat = np.cos(x)

    # Irregular cosine heartbeat with spike
    irregular_cosine_heartbeat = np.cos(x) + np.random.normal(0, 0.1, size=len(x))
    irregular_cosine_heartbeat[30] += 5  # Add an irregular beat
    
    # Create dataset
    heartbeats = np.array([normal_heartbeat, irregular_heartbeat, normal_cosine_heartbeat, irregular_cosine_heartbeat])
    labels = ["normal", "irregular", "normal", "irregular"]  # Labels for heartbeat regularity
    
    # Convert to DataFrame for easier handling
    df = pd.DataFrame(heartbeats, columns=[f"point_{i}" for i in range(100)])
    df['label'] = labels
    
    logger.info("Heartbeat waveforms generated!")
    return df

@task
def split_data(df):
    """Task: Split data into training and test sets.
    
    Splits the DataFrame into training and test sets.
    
    Parameters:
    df (pandas DataFrame): DataFrame containing the waveforms and their labels.
    
    Returns:
    tuple: Tuple containing the training and test sets (X_train, X_test, y_train, y_test).
    """
    logger = get_run_logger()
    X_train, X_test, y_train, y_test = train_test_split(
        df.drop(columns=["label"]),
        df["label"],
        test_size=0.2,
        random_state=42
    )
    logger.info("Data split into training and test sets!")
    return X_train, X_test, y_train, y_test

@task
def train_model(X_train, y_train):
    """Task: Train the Random Forest classifier for irregular heartbeat detection.
    
    Trains a Random Forest classifier on the training data.
    
    Parameters:
    X_train (pandas DataFrame): Training set features.
    y_train (pandas Series): Training set labels.
    
    Returns:
    RandomForestClassifier: Trained Random Forest classifier.
    """
    logger = get_run_logger()
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    logger.info("Model trained successfully!")
    return model

@task
def evaluate_model(model, X_test, y_test):
    """Task: Evaluate the model on the test set.
    
    Evaluates the trained model on the test set and logs the classification report and accuracy.
    
    Parameters:
    model (RandomForestClassifier): Trained Random Forest classifier.
    X_test (pandas DataFrame): Test set features.
    y_test (pandas Series): Test set labels.
    """
    logger = get_run_logger()
    y_pred = model.predict(X_test)
    
    # Print evaluation metrics
    logger.info("Classification Report:")
    logger.info(classification_report(y_test, y_pred))
    logger.info(f"Accuracy: {accuracy_score(y_test, y_pred)}")

@task
def save_model(model, filename='heartbeat_detection_model.joblib'):
    """Task: Save the trained model to a file.
    
    Saves the trained Random Forest classifier to a file.
    
    Parameters:
    model (RandomForestClassifier): Trained Random Forest classifier.
    filename (str): Filename to save the model.
    """
    logger = get_run_logger()
    try:
        dump(model, filename)
        logger.info(f"Model saved to {filename}!")
    except Exception as e:
        logger.error(f"Failed to save model to {filename}: {e}")

@task
def load_and_predict(filename, new_waveforms, true_labels):
    """Task: Load a trained model and use it for predictions.
    
    Loads a trained model from a file and uses it to predict labels for new waveforms.
    
    Parameters:
    filename (str): Filename to load the model from.
    new_waveforms (numpy array): Array of new waveforms to predict.
    true_labels (numpy array): Array of true labels for the new waveforms.
    
    Returns:
    numpy array: Predicted labels for the new waveforms.
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
    
    # Predict the labels for the new waveforms
    predictions = model.predict(new_waveforms)
    
    # Explicitly log the test cases, expected labels, and predictions
    logger.info("\nExplicit Test Case Logging:")
    for i, (true_label, prediction) in enumerate(zip(true_labels, predictions)):
        logger.info(f"Test Case {i+1}:")
        logger.info(f"  Expected: {true_label}")
        logger.info(f"  Predicted: {prediction}")
    
    # Log the overall results
    logger.info("Predictions on new data: %s", predictions)
    logger.info("True labels: %s", true_labels)
    
    # Evaluate the performance on new test data
    logger.info("\nClassification Report on new test data:")
    logger.info(classification_report(true_labels, predictions))
    logger.info(f"Accuracy on new data: {accuracy_score(true_labels, predictions)}")
    
    return predictions

@task
def generate_test_heartbeat_waveforms():
    """Task: Generate new heartbeat waveforms with and without irregularities for final testing.
    
    Generates new sine, cosine, and polynomial waveforms, with some containing irregular beats,
    and returns the waveforms and their labels.
    
    Returns:
    tuple: Tuple containing the new waveforms and their labels (waveforms, labels).
    """
    x = np.linspace(0, 10, 100)
    
    # Generate new heartbeat waveforms
    normal_heartbeat = np.sin(x)        # No irregular beat
    irregular_heartbeat = np.sin(x) + np.random.normal(0, 0.1, size=len(x))  # Add noise and irregular beat
    irregular_heartbeat[20] += 4        # Add an irregular beat
    
    # Combine waveforms and labels
    waveforms = np.array([normal_heartbeat, irregular_heartbeat])
    labels = ["normal", "irregular"]
    
    return waveforms, labels

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
        description="## ETL Pipeline Output\n\nHeartbeat data has been successfully extracted from MinIO, transformed, and loaded back into MinIO."
    )

# ----------------------------- Flow -----------------------------

@flow
def heartbeat_detection_flow():
    """The main Prefect flow that orchestrates the heartbeat detection tasks.
    
    Orchestrates the tasks of generating heartbeat waveforms, splitting data, training the model,
    evaluating the model, saving the model, generating new test heartbeats, and loading
    and predicting on new heartbeats.
    """
    # Step 1: Generate waveforms with irregular heartbeats
    df = generate_heartbeat_waveforms()
    
    # Step 2: Split data
    X_train, X_test, y_train, y_test = split_data(df)
    
    # Step 3: Train model
    model = train_model(X_train, y_train)
    
    # Step 4: Evaluate model
    evaluate_model(model, X_test, y_test)
    
    # Step 5: Save model
    MODEL_FILE_NAME = "heartbeat_detection_model.joblib"
    save_model(model=model, filename=MODEL_FILE_NAME)
    
    # Step 6: Generate new test waveforms (with and without irregular beats)
    new_waveforms, true_labels = generate_test_heartbeat_waveforms()
    
    # Step 7: Load saved model and predict on new test waveforms
    load_and_predict(MODEL_FILE_NAME, new_waveforms, true_labels)

    # Step 8: Load saved model to MinIO
    BUCKET_NAME = "models"
    OBJECT_NAME = MODEL_FILE_NAME
    load_to_minio(MODEL_FILE_NAME, BUCKET_NAME, OBJECT_NAME)
    create_etl_artifact(BUCKET_NAME, OBJECT_NAME)

# ----------------------------- Run Flow -----------------------------

if __name__ == "__main__":
    heartbeat_detection_flow()
