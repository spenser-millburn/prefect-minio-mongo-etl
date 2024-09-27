#!/bin/bash

ALIAS_NAME="myminio"
MINIO_URL="http://minio:9000"
ACCESS_KEY="password"
SECRET_KEY="password"

# Read JSON configuration from file
CONFIG_FILE=$1
CONFIG=$(cat $CONFIG_FILE)

# Check if the alias is already set
alias_exists=$(mc alias list | grep -w $ALIAS_NAME)

if [ -z "$alias_exists" ]; then
  # Set the alias if it does not exist
  mc alias set $ALIAS_NAME $MINIO_URL $ACCESS_KEY $SECRET_KEY
  echo "Alias $ALIAS_NAME set."
else
  echo "Alias $ALIAS_NAME already exists."
fi

# Remove existing notify webhooks
existing_webhooks=$(mc admin config get $ALIAS_NAME/ | grep notify_webhook)
if [ -n "$existing_webhooks" ]; then
  mc admin config set $ALIAS_NAME/ notify_webhook:1 endpoint= auth_token= queue_limit=0 queue_dir= client_cert= client_key=
  echo "Existing notify webhooks removed."
fi

# Iterate over the JSON configuration to create buckets and set webhook notifications
echo "$CONFIG" | jq -c '.[]' | while read -r bucket; do
  BUCKET_NAME=$(echo $bucket | jq -r '.name')
  WEBHOOK_ENDPOINT=$(echo $bucket | jq -r '.webhook')

  # Check if the bucket already exists
  bucket_exists=$(mc ls $ALIAS_NAME | grep -w $BUCKET_NAME)

  if [ -z "$bucket_exists" ]; then
    # Create the bucket if it does not exist
    mc mb $ALIAS_NAME/$BUCKET_NAME
    echo "Bucket $BUCKET_NAME created."
  else
    echo "Bucket $BUCKET_NAME already exists."
  fi

  # Set the webhook notification configuration if an endpoint is provided
  if [ -n "$WEBHOOK_ENDPOINT" ]; then
    mc admin config set $ALIAS_NAME/ notify_webhook:1 endpoint=$WEBHOOK_ENDPOINT auth_token= queue_limit=0 queue_dir= client_cert= client_key=
    echo "Webhook notification configuration set for $BUCKET_NAME."

    # Add event notification for the bucket
    mc event add $ALIAS_NAME/$BUCKET_NAME arn:minio:sqs::1:webhook --event put --suffix .csv
    echo "Event notification added for $BUCKET_NAME."
  else
    echo "No webhook endpoint provided for $BUCKET_NAME."
  fi
done

# Restart the MinIO service
mc admin service restart $ALIAS_NAME
echo "MinIO service restarted."
