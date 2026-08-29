# ROADMAP TÉCNICO E DEBITOS TÉCNICOS - AZURE LAKEHOUSE REVIEWS

## 1. STATUS ATUAL DA ARQUITETURA (MEDALLION)

- Bronze (Raw Layer):
  - Ingestão concluída no MinIO (`s3a://lakehouse/bronze/`).
  - Arquivos raw armazenados em formato JSON comprimido (`.json.gz`).

- Silver (Cleansed Layer):
  - Script `process_silver.py` executado com sucesso.
  - Schema padronizado, casts de tipos de dados aplicados e registros duplicados removidos.
  - Volumetria validada: 8.898.041 registros.
  - Formato de escrita: Apache Parquet particionado/comprimido em `s3a://lakehouse/silver/reviews_cleaned`.

- Gold (Curated Layer):
  - Script `process_gold.py` funcional.
  - Agregação por entidade produto (`asin`) validada com 367.982 registros únicos.
  - Mapeamento de métricas: `total_reviews`, `avg_rating`, `first_review_date`, `last_review_date`.
  - Distribuição de cardinalidade de `overall` validada (4.980.815 avaliações nota 5.0; 2.223.094 nota 4.0; 955.189 nota 3.0; 415.110 nota 2.0; 323.833 nota 1.0).

---

## 2. PENDÊNCIAS E PRÓXIMOS PASSOS TÉCNICOS

### 2.1. Refatoração e Padronização dos Módulos PySpark
- [ ] Parametrização dos scripts `process_silver.py` e `process_gold.py` usando `argparse` para receber rotas S3, chaves de acesso e endpoints como argumentos de execução em vez de hardcoded.
- [ ] Implementação de módulo de logging padrão (`logging`) substituindo os comandos `print`.
- [ ] Definição explícita de schemas via `StructType` no carregamento dos dados para evitar overhead de inferência de schema.

### 2.2. Migração de Armazenamento para Delta Lake
- [ ] Adicionar dependência `io.delta:delta-spark_2.12` nas submissões Spark.
- [ ] Alterar o formato do `DataFrameWriter` de `parquet` para `delta` nas camadas Silver e Gold.
- [ ] Implementar comandos de otimização de layout de arquivos (`OPTIMIZE` e `Z-ORDER BY asin`) para reduzir o problema de pequenos arquivos (small files problem).
- [ ] Configurar controle de concorrência e transações ACID.

### 2.3. Camada de Consulta e Serving (Engine OLAP)
- [ ] Configurar instância do DuckDB com extensão `httpfs` para execução de queries SQL ANSI diretamente nos arquivos Parquet/Delta do MinIO sem necessidade de subir uma SparkSession.
- [ ] Avaliar conteinerização de um catálogo Trino/Presto via `docker-compose.yml` conectado ao S3/MinIO para consultas distribuídas.

### 2.4. Orquestração e Pipeline de Dados
- [ ] Configurar ambiente Apache Airflow (ou Mage.ai) via Docker.
- [ ] Mapear as dependências e criar a DAG de execução sequencial:
  `Ingestion (Bronze) -> Transformation (Silver) -> Aggregation (Gold) -> Data Quality Checks`.
- [ ] Implementar testes de qualidade de dados na camada Silver e Gold utilizando Great Expectations ou PySpark Assertions.

### 2.5. Migração para Nuvem (Azure Production Deployment)
- [ ] Substituição da API S3/MinIO para Azure Blob Storage / Azure Data Lake Storage Gen2 (ADLS Gen2) via conector `ABFS`.
- [ ] Adaptação dos scripts PySpark para execução no Azure Databricks ou Azure Synapse Analytics.
- [ ] Armazenamento e gerenciamento de segredos via Azure Key Vault.

---

## 3. PROCEDIMENTO DE REINICIALIZAÇÃO DO AMBIENTE

Para validar o estado da camada Gold no próximo acesso:

```bash
PYSPARK_SUBMIT_ARGS="--master local[1] --conf spark.driver.memory=2g --packages org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262 pyspark-shell" python3 -c "
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName('CheckGoldState') \
    .config('spark.hadoop.fs.s3a.endpoint', 'http://localhost:9000') \
    .config('spark.hadoop.fs.s3a.access.key', 'minioadmin') \
    .config('spark.hadoop.fs.s3a.secret.key', 'minioadmin') \
    .config('spark.hadoop.fs.s3a.path.style.access', 'true') \
    .config('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem') \
    .config('spark.hadoop.fs.s3a.aws.credentials.provider', 'org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider') \
    .config('spark.hadoop.fs.s3a.threads.keepalivetime', '60') \
    .config('spark.hadoop.fs.s3a.connection.timeout', '60000') \
    .config('spark.hadoop.fs.s3a.connection.establish.timeout', '30000') \
    .config('spark.hadoop.fs.s3a.socket.timeout', '30000') \
    .config('spark.hadoop.fs.s3a.multipart.purge.age', '86400') \
    .config('spark.hadoop.fs.s3a.multipart.purge.interval', '86400') \
    .getOrCreate()

spark.read.parquet('s3a://lakehouse/gold/product_metrics').show(10, False)
spark.stop()
"

