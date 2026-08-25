import os
import csv
import boto3
from botocore.exceptions import ClientError

RAW_FILE = "amazon_reviews_us_Books_v1_02.tsv"
BUCKET_NAME = "lakehouse"
OBJECT_KEY = "bronze/amazon_reviews/books/data.tsv"


def generate_mock_data():
    print("Gerando dataset mock local para a camada Bronze...")
    columns = [
        "marketplace", "customer_id", "review_id", "product_id",
        "product_parent", "product_title", "product_category",
        "star_rating", "helpful_votes", "total_votes", "vine",
        "verified_purchase", "review_headline", "review_body", "review_date"
    ]
    
    rows = [
        ["US", "12345678", "R1111111", "0345803484", "10000001", "Fifty Shades of Grey", "Books", "5", "10", "12", "N", "Y", "Great book", "Loved the story and narrative.", "2023-01-15"],
        ["US", "87654321", "R2222222", "0439139600", "10000002", "Harry Potter and the Goblet of Fire", "Books", "5", "5", "5", "N", "Y", "Classic read", "Must read for everyone.", "2023-02-10"],
        ["US", "11223344", "R3333333", "0060853980", "10000003", "Good Omens", "Books", "4", "2", "3", "N", "N", "Very funny", "Witty and entertaining.", "2023-03-01"],
        ["US", "44332211", "R4444444", "038549081X", "10000004", "The Handmaid's Tale", "Books", "1", "0", "4", "N", "Y", "Not for me", "Did not enjoy the pacing.", "2023-04-12"],
        ["US", "55667788", "R5555555", "0316769487", "10000005", "The Catcher in the Rye", "Books", "3", "1", "1", "N", "Y", "Average", "Decent book overall.", "2023-05-20"]
    ]

    with open(RAW_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(columns)
        writer.writerows(rows)


def run_ingestion():
    if not os.path.exists(RAW_FILE):
        generate_mock_data()

    s3_client = boto3.client(
        "s3",
        endpoint_url="http://localhost:9000",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
    )

    # Garantir que o bucket exista antes do upload
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
    except ClientError:
        print(f"Bucket '{BUCKET_NAME}' não encontrado. Criando bucket...")
        s3_client.create_bucket(Bucket=BUCKET_NAME)

    print("Enviando arquivo bruto para a camada Bronze (MinIO)...")
    s3_client.upload_file(RAW_FILE, BUCKET_NAME, OBJECT_KEY)
    print(f"Ingestão concluída com sucesso! Salvo em s3://{BUCKET_NAME}/{OBJECT_KEY}")

    if os.path.exists(RAW_FILE):
        os.remove(RAW_FILE)


if __name__ == "__main__":
    run_ingestion()
