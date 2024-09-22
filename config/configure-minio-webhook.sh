mc admin config set myminio/ notify_webhook:1 endpoint=http://flowsapi:8000/trigger-etl auth_token= queue_limit=0 queue_dir= client_cert= client_key=

mc event add myminio/alphabot-logs-bucket arn:minio:sqs::1:webhook --event put --suffix .csv
mc admin service restart myminio