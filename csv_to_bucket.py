import boto3
from botocore.exceptions import NoCredentialsError

# Configuration
access_key = 'password'
secret_key = 'password'
bucket_name = 'alphabot-logs-bucket'
file_path = 'alphabot_000000_2024_05_20_18_37_11-data.csv'
object_name = file_path #'file.csv'

def upload_to_minio(file_path, bucket_name, object_name):
    # Initialize the S3 client
    s3_client = boto3.client('s3',
                             endpoint_url='http://localhost:9000',
                             aws_access_key_id=access_key,
                             aws_secret_access_key=secret_key,
                             region_name='us-east-1',
                             config=boto3.session.Config(signature_version='s3v4'))

    try:
        # Upload the file
        s3_client.upload_file(file_path, bucket_name, object_name)
        print(f"File {file_path} uploaded to bucket {bucket_name} as {object_name}")
    except FileNotFoundError:
        print("The file was not found")
    except NoCredentialsError:
        print("Credentials not available")

if __name__ == "__main__":
    upload_to_minio(file_path, bucket_name, object_name)
