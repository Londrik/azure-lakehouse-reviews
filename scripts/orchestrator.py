import sys
from pyspark.sql import SparkSession

def run_pipeline():
    start_batch = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    end_batch = int(sys.argv[2]) if len(sys.argv) > 2 else 89

    spark = SparkSession.builder \
        .appName("AzureLakehouseProcessing") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .config("spark.hadoop.fs.s3a.connection.timeout", "60000") \
        .config("spark.hadoop.fs.s3a.connection.establish.timeout", "60000") \
        .config("spark.hadoop.fs.s3a.socket.timeout", "60000") \
        .config("spark.hadoop.fs.s3a.connection.request.timeout", "60000") \
        .config("spark.hadoop.fs.s3a.threads.keepalivetime", "60") \
        .config("spark.hadoop.fs.s3a.multipart.purge.age", "86400") \
        .getOrCreate()

    lotes_bloco = [f"batch_{i:03d}.parquet" for i in range(start_batch, end_batch + 1)]
    print(f"Total de lotes neste bloco: {len(lotes_bloco)} (Lotes {start_batch} a {end_batch})")

    BUCKET_NAME = "lakehouse"

    for file_key in lotes_bloco:
        caminho_entrada = f"s3a://{BUCKET_NAME}/bronze/{file_key}"
        print(f"---> Processando lote: {caminho_entrada}")
        
        df_bronze = spark.read.parquet(caminho_entrada)
        df_bronze.write.mode("append").parquet(f"s3a://{BUCKET_NAME}/silver/reviews_cleaned")
        print(f"✓ Lote {file_key} gravado com sucesso!")

    spark.stop()

if __name__ == "__main__":
    run_pipeline()
