# Architecture & Technical Documentation: HDFS/S3 Lakehouse Pipeline

## 1. System Overview and Topology

This repository contains the reference implementation of an enterprise Data Lakehouse following the Medallion Architecture pattern. The data processing engine utilizes Apache Spark (PySpark) for distributed transformations across storage tiers (MinIO Object Storage) and relational serving layers (Oracle Enterprise/XE Database).

```mermaid
graph TD
    SubGraph1[Storage Layer - Object Store]
    A[Raw Data Ingestion\nTSV Format] -->|MinIO Bucket: s3a://lakehouse/bronze/| B(Bronze Layer)
    
    SubGraph2[Processing Engine - Distributed Spark]
    B -->|PySpark Schema Enforcement & Sanitation| C(Silver Layer\nFormat: Apache Parquet)
    
    SubGraph3[Serving Layer - Relational Database]
    C -->|PySpark Aggregation Engine| D[Oracle DB: XEPDB1\nTable: GOLD_BOOK_REVIEWS]

    style A fill:#f9f9f9,stroke:#333,stroke-width:1px
    style B fill:#d4e6f1,stroke:#333,stroke-width:1px
    style C fill:#d5f5e3,stroke:#333,stroke-width:1px
    style D fill:#fcf3cf,stroke:#333,stroke-width:1px
2. Software Compatibility Matrix and Environment SpecificationsThe runtime environment requires absolute version parity across driver dependencies and distributed binaries to prevent serialization conflicts (Kryo/Java RMI) and S3A protocol mismatches.ComponentTarget VersionBinaries / Packages SpecifiedExecution ScopeOperating SystemLinux 5.15+ (WSL2/Ubuntu)zsh 5.8+ / Kernel x86_64Host SystemContainer EngineDocker Engine 24.0+Docker Compose v2.20+Runtime IsolationApache Spark3.4.xPySpark Runtime (Python 3.10+)Distributed ComputeHadoop AWS S3A3.3.4org.apache.hadoop:hadoop-aws:3.3.4S3 Connector ProtocolAWS Java SDK1.12.262com.amazonaws:aws-java-sdk-bundle:1.12.262AWS S3 API ClientOracle Database21c XE (21.3.0)Service Name: XEPDB1Serving Data MartOracle JDBC21.9.0.0com.oracle.database.jdbc:ojdbc8:21.9.0.0Relational ConnectorMinIO EngineRELEASE.2023+S3 API V4 ProtocolObject Storage Engine3. Data Flow & Medallion Layer Specifications3.1. Bronze Layer (Raw Storage)Path: s3a://lakehouse/bronze/amazon_reviews/books/data.tsvFormat: Tab-Separated Values (TSV), UTF-8 Encoding.Schema Strategy: Schema-on-Read. Raw text data ingested without mutations.3.2. Silver Layer (Cleaned & Structured)Path: s3a://lakehouse/silver/amazon_reviews/books/Format: Apache Parquet (Snappy Compression).Transformations Applied:Strict type casting: star_rating (Integer), helpful_votes (Integer), total_votes (Integer).Date normalization: review_date parsed via ISO-8601 pattern yyyy-MM-dd.Audit Lineage: Ingestion timestamp append via current_timestamp().Sanitation: Null record eviction where review_id IS NULL.3.3. Gold Layer (Business Aggregations)Target System: Oracle Database (jdbc:oracle:thin:@//oracle:1521/XEPDB1)Table Identifier: GOLD_BOOK_REVIEWSPersistence Strategy: Overwrite Mode via JDBC Batch Writes.4. Mathematical Formulations & Aggregation RulesThe metrics calculated in the Gold Layer pipeline execute under the following formal mathematical definitions:4.1. Average Rating ($\bar{R}$)Given a set of reviews $S_p$ for a specific product $p$, where $r_i$ represents the star rating of review $i$ and $n = |S_p|$ is the total number of reviews for product $p$:$$\bar{R}_p = \text{round}\left( \frac{1}{n} \sum_{i=1}^{n} r_i, 2 \right)$$4.2. Average Helpful Votes ($\bar{H}$)Given $h_i$ as the number of helpful votes for review $i$ within product set $S_p$:$$\bar{H}_p = \text{round}\left( \frac{1}{n} \sum_{i=1}^{n} h_i, 2 \right)$$4.3. Total Reviews Count ($N_p$)$$N_p = \sum_{i \in S_p} 1$$5. Algorithmic Complexity & Big O Analysis5.1. Silver Layer Transformation PipelineLet $N$ be the total number of raw records in the input TSV file, and $M$ be the number of columns per row.Read TSV -> Map Transformation (Cast/Date/Filter) -> Parquet Disk Output
Time Complexity:Ingestion & Parsing: $\mathcal{O}(N \cdot M)$ to tokenize strings.Row Transformations: $\mathcal{O}(N)$ for column-wise casting and date normalization.Parquet Serialization: $\mathcal{O}(N \cdot M)$ due to columnar conversion and Snappy compression encoding.Overall Time Complexity: $\mathcal{O}(N)$ linear time complexity relative to record count.Space Complexity:In-Memory Transformation: $\mathcal{O}(B \cdot K)$ where $B$ is the execution batch/partition size and $K$ is memory overhead per row. Spark processes records in micro-batches per worker partition, avoiding $\mathcal{O}(N)$ memory footprint.Disk Footprint: $\mathcal{O}(N \cdot C)$ where $C$ is the compressed column size. Parquet columnar compression reduces disk footprint by 60%-80% compared to raw TSV.5.2. Gold Layer Aggregation PipelineLet $N$ be the total number of records in the Silver Parquet dataset, and $U$ be the number of unique products (product_id).Parquet Read -> Shuffle Hash GroupBy(product_id) -> Local/Global Aggregations -> JDBC Write
Time Complexity:Parquet Read: $\mathcal{O}(N')$, reading only required projection columns (product_id, product_title, star_rating, helpful_votes, review_id).Map-side Partial Aggregation: $\mathcal{O}(N)$ local hash map updates per partition.Network Shuffle Phase: $\mathcal{O}(N \log K)$ where $K$ is the number of Spark shuffle partitions across network.Reduce-side Final Aggregation: $\mathcal{O}(U)$ hash table lookup to compile final statistical means per unique key.JDBC Batch Insert: $\mathcal{O}(U)$ database execution time.Overall Time Complexity: $\mathcal{O}(N + U \log U)$ bounded by shuffle operations.Space Complexity:Shuffle Memory: $\mathcal{O}(U)$ auxiliary memory needed to store unique keys across executors.Database Memory: $\mathcal{O}(U)$ space allocated inside the target Oracle Database tablespace.6. Execution Guide and Environment Bootstrap6.1. System ProvisioningInitialize containerized services within the defined network bridge:Bash# Directory Context: ~/projects/azure-lakehouse-reviews
docker-compose up -d
6.2. Execution of Silver Pipeline ProcessingSubmit PySpark Job for Bronze-to-Silver ETL:Bash# Directory Context: ~/projects/azure-lakehouse-reviews
docker exec -it lakehouse-spark spark-submit \
  --packages org.apache.hadoop:hadoop-aws:3.3.4 \
  /home/jovyan/work/process_silver.py
6.3. Execution of Gold Pipeline AggregationSubmit PySpark Job for Silver-to-Gold aggregation and Oracle JDBC stream:Bash# Directory Context: ~/projects/azure-lakehouse-reviews
docker exec -it lakehouse-spark spark-submit \
  --packages org.apache.hadoop:hadoop-aws:3.3.4,com.oracle.database.jdbc:ojdbc8:21.9.0.0 \
  /home/jovyan/work/process_gold.py
6.4. Serving Layer VerificationQuery the target relational schema inside Oracle Enterprise Engine:Bash# Directory Context: ~/projects/azure-lakehouse-reviews
docker exec -i lakehouse-oracle sqlplus system/oracle@//localhost:1521/XEPDB1 << 'EOF'
SET PAGESIZE 50;
SET LINESIZE 200;
COLUMN PRODUCT_ID FORMAT A12;
COLUMN PRODUCT_TITLE FORMAT A40;
SELECT * FROM GOLD_BOOK_REVIEWS;
EXIT;
