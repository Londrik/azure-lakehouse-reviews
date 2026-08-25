from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, count, round

def main():
    print("Iniciando processamento Spark (Silver -> Gold)...")

    spark = SparkSession.builder \
        .appName("Lakehouse-Gold-Processing") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    silver_path = "s3a://lakehouse/silver/amazon_reviews/books/"

    # Ler dados da Silver
    df_silver = spark.read.parquet(silver_path)

    # Agregação para a camada Gold (Métricas por produto)
    df_gold = df_silver.groupBy("product_id", "product_title") \
        .agg(
            count("review_id").alias("total_reviews"),
            round(avg("star_rating"), 2).alias("avg_rating"),
            round(avg("helpful_votes"), 2).alias("avg_helpful_votes")
        )

    print("Escrevendo tabela agregada no Oracle DB...")
    
    # Carga no Oracle via JDBC
    oracle_url = "jdbc:oracle:thin:@//oracle:1521/XEPDB1"
    
    df_gold.write \
        .format("jdbc") \
        .option("url", oracle_url) \
        .option("dbtable", "GOLD_BOOK_REVIEWS") \
        .option("user", "system") \
        .option("password", "oracle") \
        .option("driver", "oracle.jdbc.driver.OracleDriver") \
        .mode("overwrite") \
        .save()

    print("Processamento Gold e carga no Oracle concluídos com sucesso!")
    spark.stop()

if __name__ == "__main__":
    main()
