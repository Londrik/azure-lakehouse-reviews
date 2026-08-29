# Changelog

All notable changes to the Lakehouse Architecture will be documented in this file.

## [1.0.0] - 2026-08-25
### Added
- Ingestion module for raw TSV files into MinIO S3 Bronze Layer (`ingest_bronze.py`).
- PySpark cleaning and schema casting engine for Parquet Silver Layer (`process_silver.py`).
- PySpark analytical aggregation engine with Oracle JDBC write support for Gold Layer (`process_gold.py`).
- Full container infrastructure orchestration via `docker-compose.yml`.
- System architecture, Big O mathematical complexity, and operational documentation.
