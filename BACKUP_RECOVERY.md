# Disaster Recovery & Data Retention Policy

## Backup Procedures

### 1. MinIO Bucket Object Storage Backup
- Target: `s3a://lakehouse/`
- Method: Mirroring via MinIO Client (`mc mirror`) to external cold storage target.

### 2. Oracle Database DataPump Export
- Target: `GOLD_BOOK_REVIEWS` table.
- Execution:
  `docker exec -i lakehouse-oracle expdp system/oracle@//localhost:1521/XEPDB1 tables=GOLD_BOOK_REVIEWS directory=DATA_PUMP_DIR dumpfile=gold_reviews.dmp`
