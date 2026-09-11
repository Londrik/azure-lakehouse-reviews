# Monitoramento e Observabilidade da Infraestrutura

Guia de inspeção operacional, saúde dos serviços e validação da volumetria no ecossistema Lakehouse (MinIO, Spark, DuckDB e Streamlit).

---

## 1. Verificação de Integridade dos Serviços

| Serviço | Tipo de Checagem | Endpoint / Comando | Status Esperado |
| :--- | :--- | :--- | :--- |
| **MinIO S3** | Endpoint HTTP | `curl -I http://localhost:9000/minio/health/live` | `HTTP/1.1 200 OK` |
| **MinIO Console** | Interface Web | Acessar `http://localhost:9001` | Tela de Login |
| **Spark Master** | Web UI | Acessar `http://localhost:8080` | `ALIVE` (Workers ativos) |
| **DuckDB Serving** | Execução Python | Query de contagem via extensão `httpfs` | Retorno de linhas sem erro |
| **Streamlit Dashboard** | Interface Web | Acessar `http://localhost:8502` | Dashboard carregado |

---

## 2. Inspeção de Volumetria via DuckDB CLI

Execute diretamente no terminal para verificar a contagem de registros persistidos na camada Gold:

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
print('Tabela product_metrics:', con.execute('SELECT COUNT(*) FROM read_parquet(\"s3://lakehouse/gold/product_metrics/**/*.parquet\", hive_partitioning=true)').fetchone()[0])
print('Tabela monthly_product_metrics:', con.execute('SELECT COUNT(*) FROM read_parquet(\"s3://lakehouse/gold/monthly_product_metrics/**/*.parquet\", hive_partitioning=true)').fetchone()[0])
print('Tabela reviewer_metrics:', con.execute('SELECT COUNT(*) FROM read_parquet(\"s3://lakehouse/gold/reviewer_metrics/**/*.parquet\", hive_partitioning=true)').fetchone()[0])
"
```

---

## 3. Acompanhamento de Logs em Tempo Real

Acompanhe as saídas dos containers durante a ingestão e transformações batch:

```bash
# Logs do MinIO
docker compose logs -f minio

# Logs do Spark Master
docker compose logs -f spark
```

---

## 4. Métricas de Consumo de Recursos

Para monitorar CPU e memória alocadas pelos containers da stack:

```bash
docker stats --no-stream --format \"table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\"
```
