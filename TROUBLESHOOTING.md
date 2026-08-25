# Troubleshooting & Known Issues Guide

## Common Errors and Resolutions

### 1. Connection Refused to MinIO (S3A Endpoint Error)
- Cause: Script inside `lakehouse-spark` container references `http://localhost:9000` instead of Docker internal DNS.
- Resolution: Ensure `spark.hadoop.fs.s3a.endpoint` is configured to `http://minio:9000`.

### 2. TTY Input Device Error on SQL*Plus Execution
- Cause: Using `-t` interactive flag in Docker with non-interactive standard input redirection (`<< EOF`).
- Resolution: Omit `-t` flag and execute with `-i` (`docker exec -i lakehouse-oracle sqlplus ...`).

### 3. MinIO Client Bucket Path Not Found (/myminio/...)
- Cause: Alias `myminio` unconfigured or missing credentials inside `lakehouse-minio-setup`.
- Resolution: Execute:
  `docker exec -it lakehouse-minio-setup /usr/bin/mc alias set myminio http://minio:9000 minioadmin minioadmin`
