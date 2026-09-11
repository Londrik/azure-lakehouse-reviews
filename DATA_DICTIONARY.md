# Dicionário de Dados e Contrato de Schemas

## 1. Camada Bronze

* **URI de Armazenamento:** `s3a://lakehouse/bronze/amazon_reviews/books/data.tsv`
* **Formato:** TSV / Texto Plano UTF-8
* **Estratégia de Ingestão:** Carga bruta imutável (append-only)

---

## 2. Camada Silver

* **URI de Armazenamento:** `s3a://lakehouse/silver/amazon_reviews/books/`
* **Formato:** Apache Parquet com Compressão Snappy

| Campo | Tipo Primitivo | Anulável | Restrição / Domínio | Descrição Técnica |
| :--- | :--- | :--- | :--- | :--- |
| `marketplace` | STRING | SIM | Código ISO (2 letras) | País de origem da avaliação |
| `customer_id` | STRING | SIM | Alfanumérico | Identificador anônimo do comprador |
| `review_id` | STRING | NÃO | Chave Primária | Identificador exclusivo do registro |
| `product_id` | STRING | NÃO | ASIN / ISBN-10 | Identificador único do produto |
| `product_parent` | STRING | SIM | Alfanumérico | Identificador da variação pai |
| `product_title` | STRING | SIM | Texto livre | Título catalogado do produto |
| `product_category` | STRING | SIM | Literal (`Books`) | Categoria de alto nível |
| `star_rating` | INTEGER | SIM | Intervalo: `[1, 5]` | Nota quantitativa atribuída |
| `helpful_votes` | INTEGER | SIM | Valor: >= 0 | Votos de utilidade da comunidade |
| `total_votes` | INTEGER | SIM | Valor: >= helpful_votes | Total de votos computados |
| `vine` | STRING | SIM | Enum: `['Y', 'N']` | Participação no programa Vine Voice |
| `verified_purchase`| STRING | SIM | Enum: `['Y', 'N']` | Confirmação de compra verificada |
| `review_headline` | STRING | SIM | Texto livre | Resumo/título da avaliação |
| `review_body` | STRING | SIM | Texto longo | Texto narrativo da avaliação |
| `review_date` | DATE | SIM | Formato: `yyyy-MM-dd` | Data de publicação da avaliação |
| `ingestion_timestamp`| TIMESTAMP | NÃO | UTC | Timestamp de auditoria de ingestão |

---

## 3. Camada Gold

### 3.1. Tabela: `product_metrics`
* **URI de Armazenamento:** `s3a://lakehouse/gold/product_metrics/`
* **Formato:** Parquet Colunar (`**/*.parquet`)

| Coluna | Tipo | Chave | Descrição Técnica | Regra de Cálculo |
| :--- | :--- | :--- | :--- | :--- |
| `asin` | STRING | PK | Código ASIN/ISBN do produto | Identificador de catálogo |
| `total_reviews` | BIGINT | - | Contagem total de avaliações | Contagem agregada (COUNT) |
| `avg_rating` | DOUBLE | - | Média das notas arredondada (2 decimais) | Média aritmética (AVG) |
| `sum_rating` | BIGINT | - | Soma total dos pontos atribuídos | Soma acumulada (SUM) |
| `rejection_rate_pct` | DOUBLE | - | Percentual de avaliações com nota <= 2 | (Total notas <= 2 / Total) * 100 |
| `first_review_date` | DATE | - | Data da primeira avaliação registrada | Menor data encontrada (MIN) |
| `last_review_date` | DATE | - | Data da avaliação mais recente | Maior data encontrada (MAX) |

### 3.2. Tabela: `monthly_product_metrics`
* **URI de Armazenamento:** `s3a://lakehouse/gold/monthly_product_metrics/`
* **Particionamento Hive:** `review_year=<YYYY>/review_month=<MM>/`

| Coluna | Tipo | Chave | Descrição Técnica | Regra de Cálculo |
| :--- | :--- | :--- | :--- | :--- |
| `asin` | STRING | PK Composta | Código ASIN/ISBN do produto | SKU do produto |
| `review_year` | INTEGER | Partição | Ano da avaliação | Partição Hive extraída |
| `review_month` | INTEGER | Partição | Mês da avaliação | Partição Hive extraída |
| `monthly_reviews` | BIGINT | - | Total de avaliações no mês | Contagem na janela temporal |
| `monthly_avg_rating` | DOUBLE | - | Média mensal das notas do produto | Média aritmética no mês |

### 3.3. Tabela: `reviewer_metrics`
* **URI de Armazenamento:** `s3a://lakehouse/gold/reviewer_metrics/`
* **Formato:** Parquet Colunar (`**/*.parquet`)

| Coluna | Tipo | Chave | Descrição Técnica | Regra de Cálculo |
| :--- | :--- | :--- | :--- | :--- |
| `reviewerID` | STRING | PK | Identificador do usuário avaliador | Identificador único |
| `total_reviews_written` | BIGINT | - | Volume de avaliações publicadas | Total histórico do usuário |
| `total_reviews_by_reviewer`| BIGINT | - | Alias de compatibilidade retroativa | Total histórico do usuário |
| `avg_rating_given` | DOUBLE | - | Média de notas dadas pelo avaliador | Média individual do avaliador |
| `first_active_date` | DATE | - | Data da primeira atividade | Registro mais antigo |
| `last_active_date` | DATE | - | Data da última atividade | Registro mais recente |
