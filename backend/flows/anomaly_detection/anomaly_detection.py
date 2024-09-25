import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from joblib import dump, load
from prefect import flow, task

# ----------------------------- Tasks -----------------------------

@task
def generate_data():
    """Task: Generate synthetic data for anomaly detection"""
    np.random.seed(42)
    
    # Normal data (90% of dataset)
    normal_data = np.random.normal(0, 1, (900, 2))
    
    # Anomalous data (10% of dataset)
    anomalous_data = np.random.normal(5, 1, (100, 2))
    
    # Combine the datasets
    data = np.concatenate([normal_data, anomalous_data], axis=0)
    
    # Create labels (1 for normal, -1 for anomaly)
    labels = np.concatenate([np.ones(900), -1 * np.ones(100)], axis=0)
    
    # Create DataFrame for easier handling
    df = pd.DataFrame(data, columns=["feature_1", "feature_2"])
    df['label'] = labels
    
    print("Data generated!")
    return df


@task
def split_data(df):
    """Task: Split data into training and test sets"""
    X_train, X_test, y_train, y_test = train_test_split(
        df[["feature_1", "feature_2"]],
        df["label"],
        test_size=0.2,
        random_state=42
    )
    print("Data split into training and test sets!")
    return X_train, X_test, y_train, y_test


@task
def train_model(X_train, y_train):
    """Task: Train the Isolation Forest anomaly detection model"""
    model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
    model.fit(X_train)
    
    print("Model trained successfully!")
    return model


@task
def evaluate_model(model, X_test, y_test):
    """Task: Evaluate the model on the test set"""
    y_pred = model.predict(X_test)
    
    # Print evaluation metrics
    print("Classification Report:")
    print(classification_report(y_test, y_pred))
    print(f"Accuracy: {accuracy_score(y_test, y_pred)}")


@task
def save_model(model, filename='anomaly_detection_model.joblib'):
    """Task: Save the trained model to a file"""
    dump(model, filename)
    print(f"Model saved to {filename}!")


@task
def load_and_predict(filename, new_data):
    """Task: Load a trained model and use it for predictions"""
    model = load(filename)
    predictions = model.predict(new_data)
    print("Predictions on new data:", predictions)
    return predictions

# ----------------------------- Flow -----------------------------

@flow
def anomaly_detection_flow():
    """The main Prefect flow that orchestrates all tasks"""
    # Step 1: Generate data
    df = generate_data()
    
    # Step 2: Split data
    X_train, X_test, y_train, y_test = split_data(df)
    
    # Step 3: Train model
    model = train_model(X_train, y_train)
    
    # Step 4: Evaluate model
    evaluate_model(model, X_test, y_test)
    
    # Step 5: Save model
    save_model(model)
    
    # Step 6: Load and predict with new data (optional for future use)
    # Example new data (replace with real-world data as needed)
    new_data = np.random.normal(0, 1, (10, 2))
    load_and_predict("anomaly_detection_model.joblib", new_data)


# ----------------------------- Run Flow -----------------------------

# Run the flow
if __name__ == "__main__":
    anomaly_detection_flow()
