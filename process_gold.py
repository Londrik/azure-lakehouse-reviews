import argparse
import logging
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    count,
    avg,
    sum as _sum,
    round as _round,
    when,
    year,
    month,
    min as _min,
    max as _max
)

# Configuração de logging estruturado operacional
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Lakehouse-Gold-Pipeline")


def parse_args():
    parser = argparse.ArgumentParser(description="Processamento Medallion: Camada Silver -> Camada Gold (Parquet)")
    parser.add_argument("--s3-endpoint", default="http://minio:9000", help="Endpoint do MinIO/S3")
    parser.add_argument("--s3-access-key", default="minioadmin", help="Access Key S3")
    parser.add_argument("--s3-secret-key", default="minioadmin", help="Secret Key S3")
    parser.add_argument("--silver-path", default="s3a://lakehouse/silver/amazon_reviews/books/", help="Caminho de entrada Silver")
    parser.add_argument("--gold-base-path", default="s3a://lakehouse/gold", help="Diretório base de saída da camada Gold")
    return parser.parse_args()


def get_spark_session(endpoint: str, access_key: str, secret_key: str) -> SparkSession:
    logger.info("Inicializando SparkSession com conector Hadoop AWS S3A...")
    spark = SparkSession.builder \
        .appName("Lakehouse-Gold-Processing") \
        .config("spark.hadoop.fs.s3a.endpoint", endpoint) \
        .config("spark.hadoop.fs.s3a.access.key", access_key) \
        .config("spark.hadoop.fs.s3a.secret.key", secret_key) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .config("spark.sql.parquet.compression.codec", "snappy") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")
    return spark


def main():
    args = parse_args()
    spark = get_spark_session(args.s3_endpoint, args.s3_access_key, args.s3_secret_key)

    try:
        logger.info(f"Carregando dataset Silver a partir de: {args.silver_path}")
        df_silver = spark.read.parquet(args.silver_path)

        # Normalização de nomes para garantir interoperabilidade
        # Mapeia product_id -> asin se asin não existir explicitamente
        if "asin" not in df_silver.columns and "product_id" in df_silver.columns:
            df_silver = df_silver.withColumn("asin", col("product_id"))

        # Mapeia customer_id -> reviewerID se reviewerID não existir explicitamente
        if "reviewerID" not in df_silver.columns and "customer_id" in df_silver.columns:
            df_silver = df_silver.withColumn("reviewerID", col("customer_id"))

        # Adiciona dimensões de particionamento temporal
        df_silver = df_silver \
            .withColumn("review_year", year(col("review_date"))) \
            .withColumn("review_month", month(col("review_date")))

        # Cache em memória para evitar releitura do storage nos 3 branches de agregação
        df_silver.cache()
        total_records = df_silver.count()
        logger.info(f"Total de registros Silver elegíveis para consolidação Gold: {total_records:,}")

        # -------------------------------------------------------------
        # 1. Agregação Gold: product_metrics
        # -------------------------------------------------------------
        logger.info("Processando agregação de product_metrics...")
        df_products = df_silver.groupBy("asin").agg(
            count("star_rating").alias("total_reviews"),
            _round(avg("star_rating"), 2).alias("avg_rating"),
            _sum("star_rating").alias("sum_rating"),
            _round(
                (count(when(col("star_rating") <= 2, 1)) / count("star_rating")) * 100.0,
                2
            ).alias("rejection_rate_pct"),
            _min("review_date").alias("first_review_date"),
            _max("review_date").alias("last_review_date")
        )

        products_target = f"{args.gold_base_path}/product_metrics"
        logger.info(f"Escrevendo product_metrics em: {products_target}")
        df_products.write.mode("overwrite").parquet(products_target)

        # -------------------------------------------------------------
        # 2. Agregação Gold: monthly_product_metrics
        # -------------------------------------------------------------
        logger.info("Processando agregação de monthly_product_metrics...")
        df_monthly = df_silver.filter(col("review_year").isNotNull() & col("review_month").isNotNull()) \
            .groupBy("asin", "review_year", "review_month").agg(
                count("star_rating").alias("monthly_reviews"),
                _round(avg("star_rating"), 2).alias("monthly_avg_rating")
            )

        monthly_target = f"{args.gold_base_path}/monthly_product_metrics"
        logger.info(f"Escrevendo monthly_product_metrics (particionado por ano/mês) em: {monthly_target}")
        df_monthly.write \
            .partitionBy("review_year", "review_month") \
            .mode("overwrite") \
            .parquet(monthly_target)

        # -------------------------------------------------------------
        # 3. Agregação Gold: reviewer_metrics
        # -------------------------------------------------------------
        logger.info("Processando agregação de reviewer_metrics...")
        df_reviewers = df_silver.groupBy("reviewerID").agg(
            count("star_rating").alias("total_reviews_written"),
            count("star_rating").alias("total_reviews_by_reviewer"),
            _round(avg("star_rating"), 2).alias("avg_rating_given"),
            _min("review_date").alias("first_active_date"),
            _max("review_date").alias("last_active_date")
        )

        reviewers_target = f"{args.gold_base_path}/reviewer_metrics"
        logger.info(f"Escrevendo reviewer_metrics em: {reviewers_target}")
        df_reviewers.write.mode("overwrite").parquet(reviewers_target)

        df_silver.unpersist()
        logger.info("Pipeline Gold consolidado com sucesso em todas as entidades analíticas.")

    except Exception as exc:
        logger.error(f"Falha catastrófica durante a execução da pipeline Gold: {exc}", exc_info=True)
        sys.exit(1)
    finally:
        spark.stop()
        logger.info("SparkSession encerrada.")


if __name__ == "__main__":
    main()
