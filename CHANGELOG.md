# Histórico de Alterações (Changelog)

Todas as mudanças graduais e refatorações relevantes deste repositório são registradas aqui.

O formato baseia-se em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [2.0.0] - 2026-09-11

### Modificado
- **Substituição de Banco de Dados:** Remoção do Oracle DB (`XEPDB1`) como serving layer relacional da camada Gold.
- **Storage Central:** Adoção do MinIO (compatível com API S3) como data lake colunar para as três camadas (Bronze, Silver e Gold).
- **Engine OLAP:** Migração do consumo analítico para DuckDB nativo com extensão `httpfs`, eliminando a necessidade de clusters JDBC intermediários.
- **Frontend / Visualização:** Refatoração integral do `app.py` com Streamlit e Plotly Express, adotando o parâmetro mandatório `width='stretch'` em substituição a `use_container_width=True`.

### Adicionado
- Leitura analítica colunar recursiva (`**/*.parquet`) com suporte explícito a partições Hive (`hive_partitioning=true`).
- Governança de recursos na conexão DuckDB (`SET max_memory='1GB'` e `SET preserve_insertion_order=false`).
- Mapeamento dinâmico e defensivo de colunas na camada Gold (`total_reviews_by_reviewer` vs. `total_reviews_written`).
- Nova suíte de documentação padronizada em Português do Brasil com diagramas Mermaid revisados.

### Removido
- Dependências e conectores legados JDBC para Oracle.
- Scripts de inicialização DDL SQL para criação de tabelas relacionais em banco relacional.

---

## [1.0.0] - 2024-08-29

### Adicionado
- Versão inicial com ingestão de reviews da Amazon (categoria Books) em TSV na Camada Bronze.
- Scripts PySpark para processamento batch Silver (sanitização de nulos e tipos).
- Carga de agregações da camada Gold em tabelas relacionais Oracle.
