# Arquitetura & Documentação Técnica: Pipeline Lakehouse HDFS/S3

## 1. Visão Geral do Sistema e Topologia

Este repositório contém a implementação de referência de um Data Lakehouse empresarial seguindo o padrão de Arquitetura Medalhão. O mecanismo de processamento de dados utiliza Apache Spark (PySpark) para transformações distribuídas entre as camadas de armazenamento (MinIO Object Storage) e as camadas relacionais de consulta (Banco de Dados Oracle Enterprise/XE).

``` mermaid
graph TD
    SubGraph1[Storage Layer - Object Store]
    A[Raw Data Ingestion\nTSV Format] -->|MinIO Bucket: s3a://lakehouse/bronze/| B(Bronze Layer)
    
    SubGraph2[Processing Engine - Distributed Spark]
    B -->|PySpark Schema Enforcement & Sanitation| C(Silver Layer\nFormat: Apache Parquet)
    
    SubGraph3[Serving Layer - Relational Database]
    C -->|PySpark Aggregation Engine| D[Oracle DB: XEPDB1\nTable: GOLD_BOOK_REVIEWS]

    style A fill:#f9f9f9,stroke:#333,stroke-width:1px
    style B fill:#d4e6f1,stroke:#333,stroke-width:1px
    style C fill:#d5f5e3,stroke:#333,stroke-width:1px
    style D fill:#fcf3cf,stroke:#333,stroke-width:1px
````
## 2. Matriz de Compatibilidade de Software e Especificações do Ambiente

O ambiente de execução requer paridade absoluta de versões entre as dependências dos drivers e os binários distribuídos para evitar conflitos de serialização (Kryo/Java RMI) e incompatibilidades no protocolo S3A.

| Componente | Versão Alvo | Binários / Pacotes Especificados | Escopo de Execução |
| :--- | :--- | :--- | :--- |
| **Sistema Operacional** | Linux 5.15+ (WSL2/Ubuntu) | zsh 5.8+ / Kernel x86_64 | Sistema Hospedeiro |
| **Mecanismo de Contêineres** | Docker Engine 24.0+ | Docker Compose v2.20+ | Isolamento de Runtime |
| **Apache Spark** | 3.4.x | PySpark Runtime (Python 3.10+) | Computação Distribuída |
| **Hadoop AWS S3A** | 3.3.4 | `org.apache.hadoop:hadoop-aws:3.3.4` | Conector do Protocolo S3 |
| **AWS Java SDK** | 1.12.262 | `com.amazonaws:aws-java-sdk-bundle:1.12.262` | Cliente API AWS S3 |
| **Banco de Dados Oracle** | 21c XE (21.3.0) | Nome do Serviço: `XEPDB1` | Data Mart de Servimento |
| **Oracle JDBC** | 21.9.0.0 | `com.oracle.database.jdbc:ojdbc8:21.9.0.0` | Conector Relacional |
| **Mecanismo MinIO** | RELEASE.2023+ | Protocolo S3 API V4 | Mecanismo de Armazenamento de Objetos |

## 3. Fluxo de Dados & Especificações da Camada Medalhão

### 3.1. Camada Bronze (Armazenamento Bruto)
* **Caminho:** `s3a://lakehouse/bronze/amazon_reviews/books/data.tsv`
* **Formato:** Valoração Separada por Tabulação (TSV), Codificação UTF-8.
* **Estratégia de Schema:** Schema-on-Read. Dados brutos em texto ingeridos sem mutações.

### 3.2. Camada Silver (Limpa & Estruturada)
* **Caminho:** `s3a://lakehouse/silver/amazon_reviews/books/`
* **Formato:** Apache Parquet (Compactação Snappy).
* **Transformações Aplicadas:**
  * **Tipagem estrita:** `star_rating` (Integer), `helpful_votes` (Integer), `total_votes` (Integer).
  * **Normalização de data:** `review_date` analisado via padrão ISO-8601 (`yyyy-MM-dd`).
  * **Linhagem de Auditoria:** Anexo do timestamp de ingestão via `current_timestamp()`.
  * **Saneamento:** Remoção de registros nulos onde `review_id IS NULL`.

### 3.3. Camada Gold (Agregações de Negócio)
* **Sistema Alvo:** Banco de Dados Oracle (`jdbc:oracle:thin:@//oracle:1521/XEPDB1`)
* **Identificador da Tabela:** `GOLD_BOOK_REVIEWS`
* **Estratégia de Persistência:** Modo Overwrite via gravações JDBC em lote (Batch Writes).

---

## 4. Formulações Matemáticas & Regras de Agregação

As métricas calculadas no pipeline da Camada Gold executam sob as seguintes definições matemáticas formais:

### 4.1. Avaliação Média ($\bar{R}$)
Dado um conjunto de avaliações $S_p$ para um produto específico $p$, onde $r_i$ representa a nota em estrelas da avaliação $i$ e $n = \vert{}S_p\vert{}$ é o total de avaliações para o produto $p$:

$$\bar{R}_p = \text{round}\left( \frac{1}{n} \sum_{i=1}^{n} r_i, 2 \right)$$

### 4.2. Média de Votos Úteis ($\bar{H}$)
Dado $h_i$ como o número de votos úteis para a avaliação $i$ dentro do conjunto de produtos $S_p$:

$$\bar{H}_p = \text{round}\left( \frac{1}{n} \sum_{i=1}^{n} h_i, 2 \right)$$

### 4.3. Contagem Total de Avaliações ($N_p$)

$$N_p = \sum_{i \in S_p} 1$$

---

## 5. Complexidade Algorítmica & Análise Big O

### 5.1. Pipeline de Transformação da Camada Silver
Considere $N$ como o número total de registros brutos no arquivo TSV de entrada, e $M$ como o número de colunas por linha.

Leitura TSV -> Mapeamento de Transformação (Cast/Data/Filtro) -> Saída em Disco Parquet

Complexidade de Tempo

Ingestão & Parsing: O(N⋅M) para tokenizar as strings.

Transformações de Linha: O(N) para conversão de colunas e normalização de datas.

Serialização Parquet: O(N⋅M) devido à conversão colunar e codificação de compactação Snappy.

Complexidade de Tempo Geral: O(N) complexidade de tempo linear relativa à contagem de registros.

Complexidade de Espaço

Transformação em Memória: O(B⋅K) onde B é o tamanho do lote/partição de execução e K é a sobrecarga de memória por linha. O Spark processa registros em micro-lotes por partição de worker, evitando footprint de memória O(N).

Espaço em Disco: O(N⋅C) onde C é o tamanho da coluna compactada. A compactação colunar do Parquet reduz o uso de disco em 60%-80% em comparação ao TSV bruto.

5.2. Pipeline de Agregação da Camada Gold

Considere N como o número total de registros no dataset Silver Parquet, e U como o número de produtos únicos (product_id).
Plaintext

Leitura Parquet -> Shuffle Hash GroupBy(product_id) -> Agregações Locais/Globais -> Escrita JDBC

Complexidade de Tempo

Leitura Parquet: O(N′), lendo apenas as colunas projetadas necessárias (product_id, product_title, star_rating, helpful_votes, review_id).

Agregação Parcial no Map-side: O(N) atualizações locais na tabela hash por partição.

Fase de Shuffle na Rede: O(NlogK) onde K é o número de partições de shuffle do Spark na rede.

Agregação Final no Reduce-side: Consulta em tabela hash O(U) para compilar as médias estatísticas finais por chave única.

Inserção JDBC em Lote: Tempo de execução do banco de dados em O(U).

Complexidade de Tempo Geral: O(N+UlogU) delimitada por operações de shuffle.

Complexidade de Espaço

Memória de Shuffle: Memória auxiliar O(U) necessária para armazenar chaves únicas entre os executores.

Memória do Banco de Dados: Espaço O(U) alocado dentro do tablespace do Banco de Dados Oracle alvo.

6. Guia de Execução e Inicialização do Ambiente
6.1. Provisionamento do Sistema

Inicialize os serviços em contêineres dentro da bridge de rede definida:
````Bash

# Contexto do Diretório: ~/projects/azure-lakehouse-reviews
docker-compose up -d
````

6.2. Execução do Pipeline da Camada Silver

Submeta o job PySpark para o ETL de Bronze para Silver:
````Bash

# Contexto do Diretório: ~/projects/azure-lakehouse-reviews
docker exec -it lakehouse-spark spark-submit \
  --packages org.apache.hadoop:hadoop-aws:3.3.4 \
  /home/jovyan/work/process_silver.py
````
6.3. Execução da Agregação da Camada Gold

Submeta o job PySpark para a agregação de Silver para Gold e fluxo JDBC do Oracle:

````Bash
# Contexto do Diretório: ~/projects/azure-lakehouse-reviews
docker exec -it lakehouse-spark spark-submit \
  --packages org.apache.hadoop:hadoop-aws:3.3.4,com.oracle.database.jdbc:ojdbc8:21.9.0.0 \
  /home/jovyan/work/process_gold.py
````

6.4. Verificação da Camada de Consulta

Consulte o schema relacional alvo dentro do motor Oracle Enterprise:
````Bash

# Contexto do Diretório: ~/projects/azure-lakehouse-reviews
docker exec -i lakehouse-oracle sqlplus system/oracle@//localhost:1521/XEPDB1 << 'EOF'
SET PAGESIZE 50;
SET LINESIZE 200;
COLUMN PRODUCT_ID FORMAT A12;
COLUMN PRODUCT_TITLE FORMAT A40;
SELECT * FROM GOLD_BOOK_REVIEWS;
EXIT;
EOF
````
