from prefect import task, flow
from prefect.artifacts import create_link_artifact
from minio import Minio
from pymongo import MongoClient
import pandas as pd
from io import BytesIO
import os
import re
from typing import List, Tuple, Dict
from itertools import islice
from pathlib import Path
from snapstat.fingerprints import Sequence, sequences

# MinIO client configuration
minio_client = Minio(
    f"{os.getenv('MINIO_HOSTNAME', 'localhost')}:9000",
    access_key="password",
    secret_key="password",
    secure=False
)

# MongoDB client configuration
mongo_client = MongoClient(f"mongodb://{os.getenv('MONGO_HOSTNAME', 'localhost')}:27017/")
db = mongo_client["loganalysis"]
collection_details = db["loganalysis_details"]
collection_summary = db["loganalysis_summary"]

# Function to compile the sequence of patterns
def compile_patterns(event_sequence: Sequence) -> List[re.Pattern]:
    return [re.compile(pattern) for pattern in event_sequence.patterns]

# Helper function to generate sliding windows of lines
def sliding_window(iterable, n):
    it = iter(iterable)
    window = list(islice(it, n))
    if len(window) == n:
        yield window
    for elem in it:
        window = window[1:] + [elem]
        yield window

def process_log_file(
    log_lines: List[str], 
    compiled_sequence: List[re.Pattern], 
    sequence_length: int, 
    action=None,
    log_file_name: str = "log_file"
) -> Tuple[List[Dict[str, str]], int]:
    data: List[Dict[str, str]] = []
    sequence_count: int = 0
    line_num = 1  # Initialize line number counter

    for window_start, window in enumerate(sliding_window(log_lines, sequence_length), start=1):
        matches = []
        pattern_idx = 0  # Keep track of the current pattern we're looking for
        action_result = "No"  # Default action result to "No"

        # Iterate over the lines in the window and attempt to match the patterns in order
        for i, line in enumerate(window):
            if pattern_idx >= len(compiled_sequence):
                break  # Stop if we've matched all patterns

            pattern = compiled_sequence[pattern_idx]
            match = pattern.search(line)

            if match:
                # Capture details of the matched line
                char_position: int = match.start() + 1  # VS Code starts counting at 1 for columns
                matches.append({
                    "Log File": log_file_name,  # Use the provided log file name
                    "Matched Pattern": pattern.pattern,
                    "Log Line": line.strip(),
                    "Link": f"{log_file_name}:{window_start + i}:{char_position}",
                    "Action Matched": action_result  # Default to "No"
                })
                pattern_idx += 1  # Move to the next pattern

        # If all patterns are matched, check the action and record the sequence
        if pattern_idx == len(compiled_sequence):
            if action:
                # Run the action, expecting it to return a boolean or a string
                action_output = action(window)
                if isinstance(action_output, bool):
                    action_result = "Yes" if action_output else "No"
                elif isinstance(action_output, str):
                    action_result = action_output  # Capture the string result

                # If the action condition is False (or undesirable), skip this window
                if action_output is False:
                    continue  # Skip if the action condition is not met

            # Update action_result for all matches in this window
            for match in matches:
                match["Action Matched"] = action_result

            data.extend(matches)
            sequence_count += 1  # Count the completed sequence

    return data, sequence_count

# Function to analyze a single log file for a specific event sequence
def analyze_log_for_sequence(log_lines: List[str], event_sequence: Sequence, log_file_name: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    compiled_sequence: List[re.Pattern] = compile_patterns(event_sequence)
    sequence_length: int = event_sequence.window if event_sequence.window is not None else len(compiled_sequence)
    data: List[Dict[str, str]] = []
    summary: Dict[str, int] = {}

    file_data, file_sequence_count = process_log_file(log_lines, compiled_sequence, sequence_length, event_sequence.action, log_file_name)
    if file_data:
        data.extend(file_data)
        summary[log_file_name] = summary.get(log_file_name, 0) + file_sequence_count

    df: pd.DataFrame = pd.DataFrame(data)
    summary_df: pd.DataFrame = pd.DataFrame(list(summary.items()), columns=['Log File', 'Sequence Count'])

    return df.drop_duplicates(), summary_df.drop_duplicates()

@task
def extract_from_minio(bucket_name, object_name):
    response = minio_client.get_object(bucket_name, object_name)
    data = response.read().decode('utf-8').splitlines()
    return data, object_name

@task
def transform_data(log_lines_with_name):
    log_lines, log_file_name = log_lines_with_name
    all_data = []
    all_data_summary = []

    for event_sequence in sequences:
        sequence_df, summary_df = analyze_log_for_sequence(log_lines, event_sequence, log_file_name)

        if event_sequence.filter_actions:
            sequence_df = sequence_df[sequence_df["Action Matched"] != "No"] if "Action Matched" in sequence_df.columns else sequence_df
            sequence_df = sequence_df.drop_duplicates(subset='Log File') if 'Log File' in sequence_df.columns else sequence_df

        summary_df["fingerprint"] = event_sequence.name
        sequence_df["fingerprint"] = event_sequence.name

        all_data.append(sequence_df)
        all_data_summary.append(summary_df)

    combined_df = pd.concat(all_data).drop_duplicates()
    combined_summary_df = pd.concat(all_data_summary).drop_duplicates()

    return combined_df, combined_summary_df

@task
def load_to_mongodb(dfs):
    details_df, summary_df = dfs
    details_records = details_df.to_dict(orient='records')
    summary_records = summary_df.to_dict(orient='records')
    if details_records is not None and len(details_records) >=1:
        collection_details.insert_many(details_records)
    if details_records is not None and len(details_records) >=1:
        collection_summary.insert_many(summary_records)

@task
def create_etl_artifact(bucket_name, object_name):
    link = f"https://{os.getenv('MINIO_HOSTNAME', 'localhost')}:9000/{bucket_name}/{object_name}"
    create_link_artifact(
        key="etl-output",
        link=link,
        description="## ETL Pipeline Output\n\nData has been successfully extracted from MinIO, transformed, and loaded into MongoDB."
    )

@flow
def snapstat_fingerprints(bucket_name, object_name):
    log_lines_with_name = extract_from_minio(bucket_name, object_name)
    transformed_dfs = transform_data(log_lines_with_name)
    load_to_mongodb(transformed_dfs)
    create_etl_artifact(bucket_name, object_name)

if __name__ == "__main__":
    test_bucket_name = "alphabot-logs-bucket"
    test_object_name = "alphabot_000027_2024_08_16_07_34_10.txt"
    snapstat_fingerprints(test_bucket_name, test_object_name)
