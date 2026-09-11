# Lakehouse Gold - Consumo no Power BI Desktop

Este diretório contém os artefatos consolidados da camada Gold para ingestão analítica no Power BI sem necessidade de infraestrutura de containers ativa.

## Arquivos Disponíveis
- `data/product_metrics.parquet` (~5.9 MB)
- `data/monthly_product_metrics.parquet` (~31 MB)
- `data/reviewer_metrics.parquet` (~12 MB)
- `powerbi_load_script.py` (Script de extração automatizada via DuckDB)

## Passo a Passo para Execução no Trabalho

1. Clone ou baixe a branch `feat/powerbi-export` na máquina de trabalho.
2. Certifique-se de que o Python e a lib DuckDB estão instalados (`pip install duckdb pandas pyarrow`).
3. Abra o **Power BI Desktop**.
4. Vá em **Página Inicial** > **Obter Dados** > **Mais...** > **Script do Python**.
5. Abra o arquivo `powerbi/powerbi_load_script.py`, copie o conteúdo e cole na caixa de diálogo do Power BI.
6. Clique em **OK**.
7. Na janela do Navegador, selecione as três tabelas:
   - `df_product_metrics`
   - `df_monthly_product_metrics`
   - `df_reviewer_metrics`
8. Clique em **Carregar**.
