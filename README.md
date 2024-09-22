To create a bucket in MinIO, you can use the MinIO client (mc) or the AWS CLI. Below are the steps for both methods:

**Using MinIO Client (mc):**

1. Download and install the MinIO client (mc) from https://min.io/download#/macos.

2. Configure the MinIO client to point to your MinIO server:
   ```
   mc alias set myminio http://localhost:9000 password password
   ```

3. Create a bucket:
   ```
   mc mb myminio/alphabot-logs-bucket
   ```

3. **List the contents of the bucket**:
   ```
   mc ls myminio/alphabot-logs-bucket
   ```
