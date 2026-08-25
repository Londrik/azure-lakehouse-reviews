from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, current_timestamp

def main():
    print("Iniciando processamento Spark (Bronze -> Silver)...")
    
    spark = SparkSession.builder \
        .appName("Lakehouse-Silver-Processing") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    input_path = "s3a://lakehouse/bronze/amazon_reviews/books/data.tsv"
    output_path = "s3a://lakehouse/silver/amazon_reviews/books/"

    df_raw = spark.read \
        .option("header", "true") \
        .option("sep", "\t") \
        .csv(input_path)

    df_silver = df_raw \
        .withColumn("star_rating", col("star_rating").cast("integer")) \
        .withColumn("helpful_votes", col("helpful_votes").cast("integer")) \
        .withColumn("total_votes", col("total_votes").cast("integer")) \
        .withColumn("review_date", to_date(col("review_date"), "yyyy-MM-dd")) \
        .withColumn("ingestion_timestamp", current_timestamp()) \
        .filter(col("review_id").isNotNull())

    print("Escrevendo dados limpos na camada Silver...")
    df_silver.write \
        .mode("overwrite") \
        .parquet(output_path)

    print(f"Processamento Silver concluído com sucesso! Salvo em {output_path}")
    spark.stop()

if __name__ == "__main__":
    main()
