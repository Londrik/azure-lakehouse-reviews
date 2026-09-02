# Technical Specification & Pipeline Lineage

## 1. Network Topography & Container Interoperability

To ensure deterministic network resolution within isolated container bridges, the internal service endpoints must adhere to Docker DNS naming conventions instead of host loopback interfaces:

| Service Name | Internal Container Endpoint | Exposed Host Port | Transport Protocol |
| :--- | :--- | :--- | :--- |
| **MinIO API** | `http://minio:9000` | `9000` | HTTP / S3 API |
| **MinIO Console** | `http://minio:9001` | `9001` | HTTP |
| **Spark Master** | `spark://lakehouse-spark:7077` | `7077` / `8080` | Spark Native / RPC |
| **Oracle DB** | `jdbc:oracle:thin:@//oracle:1521/XEPDB1` | `1521` | TCP / Oracle TNS |

---

## 2. Structural Data Lineage

### 2.1. Bronze Layer Schema (Untyped Source)
* **Storage Type:** S3 Object (`s3a://lakehouse/bronze/amazon_reviews/books/data.tsv`)
* **Format:** Uncompressed Delimited Text

[marketplace: string, customer_id: string, review_id: string, product_id: string,
product_parent: string, product_title: string, product_category: string,
star_rating: string, helpful_votes: string, total_votes: string, vine: string,
verified_purchase: string, review_headline: string, review_body: string, review_date: string]


### 2.2. Silver Layer Schema (Typed Storage Target)
* **Storage Type:** S3 Object (`s3a://lakehouse/silver/amazon_reviews/books/`)
* **Format:** Columnar Parquet File Structure

````sql
|-- marketplace: string (nullable = true)
|-- customer_id: string (nullable = true)
|-- review_id: string (nullable = true)
|-- product_id: string (nullable = true)
|-- product_parent: string (nullable = true)
|-- product_title: string (nullable = true)
|-- product_category: string (nullable = true)
|-- star_rating: integer (nullable = true)
|-- helpful_votes: integer (nullable = true)
|-- total_votes: integer (nullable = true)
|-- vine: string (nullable = true)
|-- verified_purchase: string (nullable = true)
|-- review_headline: string (nullable = true)
|-- review_body: string (nullable = true)
|-- review_date: date (nullable = true)
|-- ingestion_timestamp: timestamp (nullable = false)  
````

### 2.3. Gold Layer Schema (Relational Data Mart Target)
* **Storage Type:** Relational Table (`GOLD_BOOK_REVIEWS` on Oracle Instance `XEPDB1`)
* **Engine Type:** Oracle RDBMS SQL Schema

```sql
CREATE TABLE GOLD_BOOK_REVIEWS (
    PRODUCT_ID VARCHAR2(12) NOT NULL,
    PRODUCT_TITLE VARCHAR2(40),
    TOTAL_REVIEWS NUMBER(10, 0),
    AVG_RATING NUMBER(3, 2),
    AVG_HELPFUL_VOTES NUMBER(5, 2),
    CONSTRAINT PK_GOLD_BOOK_REVIEWS PRIMARY KEY (PRODUCT_ID)
);
````

