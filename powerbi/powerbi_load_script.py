# =============================================================================
# SCRIPT DE CARGA PARA O POWER BI DESKTOP
# Como rodar no trabalho:
# 1. No Power BI Desktop: Obter Dados -> Mais... -> Script do Python
# 2. Cole este bloco de código e clique em OK
# =============================================================================

import os
import duckdb

# Identifica o diretório do projeto onde os dados foram clonados
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
DATA_PATH = os.path.join(BASE_DIR, "data") if os.path.exists(os.path.join(BASE_DIR, "data")) else os.path.join(BASE_DIR, "powerbi", "data")

conn = duckdb.connect(database=':memory:')
conn.execute("SET max_memory='1GB';")

# 1. Metricas de Produtos
df_product_metrics = conn.execute(f"""
    SELECT * FROM read_parquet('{DATA_PATH}/product_metrics.parquet')
""").df()

# 2. Metricas Mensais de Produtos
df_monthly_product_metrics = conn.execute(f"""
    SELECT * FROM read_parquet('{DATA_PATH}/monthly_product_metrics.parquet')
""").df()

# 3. Metricas de Avaliadores (com fallback defensivo de coluna)
df_reviewer_metrics = conn.execute(f"""
    SELECT * FROM read_parquet('{DATA_PATH}/reviewer_metrics.parquet')
""").df()

conn.close()
