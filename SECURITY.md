# Security & Credentials Policy

## Secrets Management
- No production secrets must be hardcoded inside PySpark scripts or Docker Compose files.
- Local execution relies on default mock credentials (`minioadmin` / `oracle`) reserved exclusively for isolated development environments.

## Data Isolation
- Network access between Spark executors, MinIO storage, and Oracle DB is locked strictly within the internal Docker bridge network (`lakehouse-net`).
