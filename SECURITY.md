# Políticas de Segurança e Gestão de Acessos

Diretrizes para proteção de credenciais, isolamento de rede e governança de dados no ecossistema do Lakehouse.

---

## 1. Gestão de Credenciais e Segredos

* **Ambiente Local (Desenvolvimento):**
  * As credenciais padrão do MinIO (`minioadmin` / `minioadmin`) são restritas ao ambiente de desenvolvimento local via Docker bridge.
  * O arquivo `.env` nunca deve ser versionado no Git; utilize sempre `.env.example` como template.
* **Ambiente Produtivo (Nuvem / Azure):**
  * O acesso aos dados em nuvem (ADLS Gen2) deve utilizar identidades gerenciadas (Managed Identities) ou chaves rotacionadas via Azure Key Vault.
  * Proibido hardcode de chaves S3 (`s3_access_key_id` / `s3_secret_access_key`) em scripts que vão para branchs públicas.

---

## 2. Isolamento de Rede e Portas de Serviço

| Serviço | Porta Host | Interface | Política de Exposição |
| :--- | :--- | :--- | :--- |
| **MinIO S3 API** | `9000` | `127.0.0.1` | Apenas tráfego local ou containers na rede `lakehouse-net` |
| **MinIO Console** | `9001` | `127.0.0.1` | Acesso administrativo local |
| **Spark Master Web UI** | `8080` | `127.0.0.1` | Inspeção visual de jobs batch |
| **Streamlit Dashboard** | `8502` | `127.0.0.1` | Interface de usuário (recomenda-se proxy reverso com TLS em prod) |

---

## 3. Práticas de Segurança em Dados e Memória

* **Prevenção de Ataques de Negação de Serviço por Memória (OOM):**
  * O DuckDB opera com limite fixo (`SET max_memory='1GB'`) prevenindo que queries analíticas sobrecarreguem a memória do host.
* **Integridade dos Objetos S3:**
  * A camada Bronze (`s3://lakehouse/bronze/`) deve operar estritamente em modo append-only, sem permissão de sobrescrita ou exclusão por usuários analíticos.
* **Sanitização de Entradas:**
  * Filtros de interface no Streamlit não devem interpolar queries brutas sem validação para evitar injeção de comandos SQL na engine DuckDB.
