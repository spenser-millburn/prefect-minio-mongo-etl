# Log Analysis

## Overview
`log_analysis` is a Python package designed for analyzing log files using predefined fingerprint sequences. It extracts, transforms, and loads log data from MinIO to MongoDB, providing insights into specific patterns and events.

## Features
- Extracts log data from MinIO.
- Analyzes log files for specific event sequences.
- Loads analyzed data into MongoDB.
- Provides detailed and summary reports of log analysis.

## Installation
To install the package, run:
```
pip install .
```

## Requirements
- Python 3.6+
- `prefect`
- `minio`
- `pymongo`
- `pandas`

## Usage
To run the log analysis flow, use the following command:
```
snapstat_fingerprints <bucket_name> <object_name>
```

## Configuration
Ensure the following environment variables are set for MinIO and MongoDB connections:
- `MINIO_HOSTNAME`
- `MONGO_HOSTNAME`

## Example
```python
from log_analysis import snapstat_fingerprints

bucket_name = "alphabot-logs-bucket"
object_name = "alphabot_000027_2024_08_16_07_34_10.txt"
snapstat_fingerprints(bucket_name, object_name)
```

## Author
Your Name
your.email@example.com

## License
This project is licensed under the MIT License.

## Repository
For more information, visit the [GitHub repository](https://github.com/yourusername/log_analysis).
