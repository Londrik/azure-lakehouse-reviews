# Roadmap Técnico e Débitos Técnicos - Azure Lakehouse Reviews

## 1. Status Atual da Arquitetura Medallion

* **Bronze (Armazenamento Raw):**
  * Ingestão contínua em formato TSV no MinIO (`s3a://lakehouse/bronze/amazon_reviews/books/data.tsv`).
  * Armazenamento imutável e estruturado como append-only.

* **Silver (Dados Sanitizados e Tipados):**
  * Script `process_silver.py` funcional via Apache Spark.
  * Tipagem estrita aplicada (`star_rating`, `helpful_votes`, `total_votes` como inteiros; `review_date` normalizado para ISO-8601).
  * Gravação em Apache Parquet com compressão Snappy em `s3a://lakehouse/silver/amazon_reviews/books/`.

* **Gold (Marts Analíticos e Features):**
  * Script `process_gold.py` refatorado com logging estruturado e argumentos via `argparse`.
  * Tabelas materializadas em Parquet no MinIO:
    * `s3a://lakehouse/gold/product_metrics/` (Visão por produto/ASIN).
    * `s3a://lakehouse/gold/monthly_product_metrics/` (Particionado por `review_year` e `review_month`).
    * `s3a://lakehouse/gold/reviewer_metrics/` (Métricas de engajamento do usuário).

* **Serving & Visualização:**
  * Engine OLAP DuckDB consumindo direto do MinIO via extensão `httpfs`.
  * Pushdown de projeções e filtros com views lazy e limite de alocação de 1GB de RAM.
  * Dashboard Streamlit operacional com Plotly Express utilizando `width='stretch'`.

---

## 2. Débitos Técnicos e Próximos Passos

### 2.1. Otimização e Qualidade de Dados
- [ ] Implementar asserções de qualidade de dados com PySpark na camada Silver (verificação de nulos em chaves primárias e checagem de faixas de datas).
- [ ] Adicionar testes automatizados no DuckDB para validar consistência dos esquemas Parquet antes da renderização no Streamlit.

### 2.2. Migração para Delta Lake
- [ ] Adicionar suporte a `delta-spark` nas submissões Spark.
- [ ] Converter formato de escrita das camadas Silver e Gold de `parquet` puro para `delta`.
- [ ] Configurar transações ACID e comandos de compactação (`OPTIMIZE` e `Z-ORDER BY asin`).

### 2.3. Orquestração e Deploy em Nuvem
- [ ] Criar DAG no Apache Airflow para orquestrar: Ingestão -> Silver -> Gold -> Carga Analítica.
- [ ] Parametrizar conectores para suportar Azure Data Lake Storage Gen2 (ADLS Gen2 via protocolo `abfs://`) sem alterar código da aplicação.
