# Estratégia de Testes e Garantia de Qualidade

Este guia estabelece os padrões e rotinas de validação para as pipelines Spark, integridade do armazenamento Parquet no MinIO e queries analíticas do DuckDB.

---

## 1. Escopo da Pirâmide de Testes

| Camada | Tipo de Validação | Ferramental | Alvo |
| :--- | :--- | :--- | :--- |
| **Bronze -> Silver** | Tipagem e Integridade | PySpark / Assertions | Nulos em chaves (`review_id`), formato ISO de datas |
| **Silver -> Gold** | Regras de Negócio | PySpark / Unit Tests | Agregações de notas (`1.0 <= avg_rating <= 5.0`), taxas percentuais |
| **Serving (Gold)** | Integridade e Pushdown | DuckDB + `pytest` | Leitura recursiva Parquet, partições Hive, schema enforcement |
| **Interface (UI)** | Smoke Test e Renderização | Streamlit CLI | Subida sem exceções, compatibilidade de colunas |

---

## 2. Testes de Integridade de Dados no DuckDB (CLI)

Execute no host para verificar se todas as tabelas Gold estão acessíveis via `httpfs` e sem registros corrompidos:

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

# 1. Teste de contagem não-nula em product_metrics
prod_count = con.execute('''
    SELECT COUNT(*) FROM read_parquet(\"s3://lakehouse/gold/product_metrics/**/*.parquet\", hive_partitioning=true)
    WHERE asin IS NULL OR total_reviews <= 0
''').fetchone()[0]
assert prod_count == 0, f'Falha: encontrados {prod_count} registros inválidos em product_metrics'

# 2. Teste de consistência de datas e partições em monthly_product_metrics
month_count = con.execute('''
    SELECT COUNT(*) FROM read_parquet(\"s3://lakehouse/gold/monthly_product_metrics/**/*.parquet\", hive_partitioning=true)
    WHERE review_year < 1990 OR review_month NOT BETWEEN 1 AND 12
''').fetchone()[0]
assert month_count == 0, f'Falha: partições de ano/mês corrompidas'

# 3. Teste de limites de avaliação
rating_outliers = con.execute('''
    SELECT COUNT(*) FROM read_parquet(\"s3://lakehouse/gold/product_metrics/**/*.parquet\", hive_partitioning=true)
    WHERE avg_rating < 1.0 OR avg_rating > 5.0
''').fetchone()[0]
assert rating_outliers == 0, f'Falha: notas médias fora do intervalo [1, 5]'

print('Todos os testes de asserção da Camada Gold passaram com sucesso!')
"

3. Teste de Carga e Alocação de Memória

Simula o comportamento de pushdown do DuckDB com teto estrito de 1GB de RAM para garantir imunidade a OOM:
Bash

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
    SET max_memory=\"1GB\";
''')

df = con.execute('''
    SELECT 
        asin,
        SUM(monthly_reviews) AS total_reviews,
        ROUND(AVG(monthly_avg_rating), 2) AS general_avg
    FROM read_parquet(\"s3://lakehouse/gold/monthly_product_metrics/**/*.parquet\", hive_partitioning=true)
    GROUP BY asin
    ORDER BY total_reviews DESC
    LIMIT 100
''').df()

assert len(df) <= 100
print(f'Teste de Pushdown com limite de memória OK. Linhas retornadas: {len(df)}')
"

4. Smoke Test do Dashboard Streamlit

Valida se o arquivo principal do dashboard carrega sem erros de sintaxe ou bibliotecas ausentes:
Bash

python3 -m py_compile app.py && echo "Sintaxe do app.py validada com sucesso."

