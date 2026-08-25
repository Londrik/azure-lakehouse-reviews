# Observability & Monitoring Guide

## Pipeline Metrics & Verification Strategy

| Layer | Verification Target | Execution Command | Expected Output |
| :--- | :--- | :--- | :--- |
| **Bronze** | MinIO Storage Object | `docker exec -it lakehouse-minio-setup /usr/bin/mc ls myminio/lakehouse/bronze/amazon_reviews/books/` | Presence of `data.tsv` |
| **Silver** | Parquet Metadata | `docker exec -it lakehouse-minio-setup /usr/bin/mc ls myminio/lakehouse/silver/amazon_reviews/books/` | Parquet part files & `_SUCCESS` |
| **Gold** | Oracle Table Data | `make query-oracle` | Non-empty dataset in `GOLD_BOOK_REVIEWS` |

## Service Health Check Endpoints

- MinIO Web Console: http://localhost:9001 (Credentials: minioadmin / minioadmin)
- Spark Master UI: http://localhost:8080
- Oracle Database Connection: localhost:1521/XEPDB1
