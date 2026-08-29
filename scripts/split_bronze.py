import gzip
import json
import gc
import boto3
import pandas as pd
from io import BytesIO

S3_ENDPOINT = "http://localhost:9000"
AWS_ACCESS_KEY = "minioadmin"
AWS_SECRET_KEY = "minioadmin"
BUCKET_NAME = "lakehouse"

# Reduzido para 100k registros por lote para manter o consumo de RAM baixo
CHUNK_SIZE = 100000 
INPUT_FILE = "data/dataset_raw.json.gz"

s3_client = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

def process_and_upload():
    print(f"Iniciando fatiamento otimizado de {INPUT_FILE}...")
    chunk = []
    batch_index = 1

    with gzip.open(INPUT_FILE, 'rt', encoding='utf-8') as f:
        for line in f:
            try:
                line_str = line.strip()
                if not line_str:
                    continue
                record = json.loads(line_str) if line_str.startswith('{') else eval(line_str)
                chunk.append(record)
            except Exception:
                continue

            if len(chunk) >= CHUNK_SIZE:
                upload_chunk(chunk, batch_index)
                batch_index += 1
                chunk = []
                gc.collect()

        if chunk:
            upload_chunk(chunk, batch_index)

    print("Fatiamento e upload concluídos com sucesso!")

def upload_chunk(data, index):
    df = pd.DataFrame(data)
    parquet_buffer = BytesIO()
    df.to_parquet(parquet_buffer, index=False, engine='pyarrow')
    parquet_buffer.seek(0)
    
    file_name = f"bronze/batch_{index:03d}.parquet"
    print(f"Enviando {file_name} ({len(df)} registros)...")
    
    s3_client.upload_fileobj(parquet_buffer, BUCKET_NAME, file_name)
    del df
    del parquet_buffer

if __name__ == "__main__":
    process_and_upload()
