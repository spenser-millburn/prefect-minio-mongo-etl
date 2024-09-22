#!/bin/bash
ALIAS_NAME="myminio"
BUCKET_NAME="alphabot-logs-bucket"
MINIO_URL="http://localhost:9000"
ACCESS_KEY="password"
SECRET_KEY="password"

# Check if the alias is already set
alias_exists=$(mc alias list | grep -w $ALIAS_NAME)

if [ -z "$alias_exists" ]; then
  # Set the alias if it does not exist
  mc alias set $ALIAS_NAME $MINIO_URL $ACCESS_KEY $SECRET_KEY
  echo "Alias $ALIAS_NAME set."
else
  echo "Alias $ALIAS_NAME already exists."
fi

# Check if the bucket already exists
bucket_exists=$(mc ls $ALIAS_NAME | grep -w $BUCKET_NAME)

if [ -z "$bucket_exists" ]; then
  # Create the bucket if it does not exist
  mc mb $ALIAS_NAME/$BUCKET_NAME
  echo "Bucket $BUCKET_NAME created."
else
  echo "Bucket $BUCKET_NAME already exists."
fi
