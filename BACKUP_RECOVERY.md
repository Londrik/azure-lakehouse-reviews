# Política de Backup e Recuperação de Desastres (DRP)

Estratégias de backup, retenção e recuperação aplicadas aos buckets do MinIO S3 (camadas Bronze, Silver e Gold) e metadados da arquitetura Medallion.

---

## 1. Topologia de Armazenamento e Alvos de Backup

| Camada / Serviço | Caminho S3 / Container | Criticidade | Estratégia de Proteção |
| :--- | :--- | :--- | :--- |
| **Bronze (Raw)** | `s3://lakehouse/bronze/` | Alta | Imutável (Append-Only), espelhamento frio |
| **Silver (Sanitizada)** | `s3://lakehouse/silver/` | Média | Reproduzível via script `process_silver.py` |
| **Gold (Marts Parquet)** | `s3://lakehouse/gold/` | Alta | Sincronização periódica via MinIO Client (`mc`) |
| **Configs & Scripts** | Git Repository | Crítica | Controle de versão distribuído no GitHub |

---

## 2. Procedimento de Backup Frio (MinIO Client - `mc`)

### 2.1. Configurar Alias do MinIO Local
Execute uma única vez no host para registrar a instância local:

```bash
docker exec -it lakehouse-minio mc alias set local http://localhost:9000 minioadmin minioadmin
```

### 2.2. Executar Snapshot dos Dados Gold e Bronze
Sincroniza os objetos do bucket para um diretório de backup local ou volume montado:

```bash
# Espelhamento do bucket completo para diretório de backup local
docker exec -it lakehouse-minio mc mirror --overwrite local/lakehouse /data/backup/lakehouse_snapshot
```

---

## 3. Procedimento de Restauração de Dados

### 3.1. Cenário: Corrupção ou Perda Total do Bucket MinIO
Caso o volume de dados seja corrompido ou o bucket deletado acidentalmente:

1. Recriar o bucket principal:

```bash
docker exec -it lakehouse-minio mc mb local/lakehouse
```

2. Restaurar dados a partir do último snapshot:

```bash
docker exec -it lakehouse-minio mc mirror /data/backup/lakehouse_snapshot local/lakehouse
```

3. Validar a integridade das tabelas Gold via DuckDB:

```bash
python3 -c "
import duckdb
con = duckdb.connect()
con.execute('INSTALL httpfs; LOAD httpfs;')
con.execute('''
    SET s3_endpoint=\"localhost:9000\";
    SET s3_access_key_id=\"minioadmin\";
    SET s3_secret_access_key=\"minioadmin\";
    SET s3_use_ssl=false;
    SET s3_url_style=\"path\";
''')
print('Validação Gold:', con.execute('SELECT COUNT(*) FROM read_parquet(\"s3://lakehouse/gold/product_metrics/**/*.parquet\", hive_partitioning=true)').fetchone()[0])
"
```

---

## 4. Recuperação por Reprocessamento (Data Lineage Re-run)

Se não houver snapshot físico recente das camadas Silver e Gold, execute a regeneração determinística do pipeline Spark:

```bash
# Regenera Silver a partir do TSV Bronze
docker exec -it lakehouse-spark spark-submit \
  --packages org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262 \
  /home/jovyan/work/process_silver.py

# Regenera Gold a partir dos Parquets Silver
docker exec -it lakehouse-spark spark-submit \
  --packages org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262 \
  /home/jovyan/work/process_gold.py
```
