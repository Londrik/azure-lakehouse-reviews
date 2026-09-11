import streamlit as st
import duckdb
import plotly.express as px
import pandas as pd

st.set_page_config(
    page_title="Lakehouse Reviews - Gold Analytics Engine",
    layout="wide"
)

st.title("Lakehouse Analytics - Camada Gold")
st.caption("Painel analitico operacional com DuckDB Pushdown e alocacao controlada de memoria sobre o MinIO.")

# -----------------------------------------------------------------------------
# 1. Conexao DuckDB com MinIO via httpfs (Cacheada e Otimizada)
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_duckdb_connection():
    con = duckdb.connect(database=":memory:", read_only=False)
    try:
        con.execute("LOAD httpfs;")
    except Exception:
        con.execute("INSTALL httpfs; LOAD httpfs;")

    con.execute("""
        SET s3_endpoint='localhost:9000';
        SET s3_access_key_id='minioadmin';
        SET s3_secret_access_key='minioadmin';
        SET s3_use_ssl=false;
        SET s3_url_style='path';
        SET max_memory='1GB';
        SET preserve_insertion_order=false;
        SET threads=4;
    """)

    # Views analiticas desacopladas com leitura colunar recursiva
    con.execute("""
        CREATE OR REPLACE VIEW v_products AS 
        SELECT * FROM read_parquet('s3://lakehouse/gold/product_metrics/**/*.parquet', hive_partitioning=true);
        
        CREATE OR REPLACE VIEW v_monthly AS 
        SELECT * FROM read_parquet('s3://lakehouse/gold/monthly_product_metrics/**/*.parquet', hive_partitioning=true);
        
        CREATE OR REPLACE VIEW v_reviewers AS 
        SELECT * FROM read_parquet('s3://lakehouse/gold/reviewer_metrics/**/*.parquet', hive_partitioning=true);
    """)
    return con

con = get_duckdb_connection()

# -----------------------------------------------------------------------------
# 2. Funcoes de Carga e Agregacao Otimizadas (Pushdown + Cache TTL)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def get_global_kpis():
    query_prod = """
        SELECT 
            COUNT(asin) AS total_products,
            COALESCE(SUM(total_reviews), 0) AS total_reviews_sum,
            COALESCE(AVG(avg_rating), 0.0) AS global_avg_rating
        FROM v_products
    """
    df_prod_kpis = con.execute(query_prod).df()
    total_monthly = con.execute("SELECT COUNT(asin) AS total FROM v_monthly").fetchone()[0]
    total_reviewers = con.execute("SELECT COUNT(reviewerID) AS total FROM v_reviewers").fetchone()[0]

    return {
        "products": int(df_prod_kpis["total_products"].iloc[0]),
        "reviews": int(df_prod_kpis["total_reviews_sum"].iloc[0]),
        "rating": float(df_prod_kpis["global_avg_rating"].iloc[0]),
        "monthly": int(total_monthly),
        "reviewers": int(total_reviewers)
    }

@st.cache_data(ttl=300, show_spinner=False)
def load_top_rejected_products(min_rev: int, limit: int):
    query = """
        SELECT asin, total_reviews, avg_rating, rejection_rate_pct 
        FROM v_products 
        WHERE total_reviews >= ?
        ORDER BY rejection_rate_pct DESC 
        LIMIT ?
    """
    return con.execute(query, [min_rev, limit]).df()

@st.cache_data(ttl=300, show_spinner=False)
def load_scatter_sample(min_rev: int, sample_size: int = 1000):
    query = f"""
        SELECT asin, total_reviews, avg_rating, rejection_rate_pct 
        FROM v_products 
        WHERE total_reviews >= ?
        USING SAMPLE {sample_size}
    """
    return con.execute(query, [min_rev]).df()

@st.cache_data(ttl=600, show_spinner=False)
def load_available_asins(limit: int = 30):
    query = """
        SELECT asin 
        FROM v_products 
        ORDER BY total_reviews DESC 
        LIMIT ?
    """
    return con.execute(query, [limit]).df()["asin"].tolist()

@st.cache_data(ttl=300, show_spinner=False)
def load_asin_monthly_trend(selected_asin: str):
    query = """
        SELECT 
            PRINTF('%d-%02d', review_year, review_month) AS periodo,
            monthly_reviews,
            monthly_avg_rating
        FROM v_monthly
        WHERE asin = ?
        ORDER BY review_year, review_month
    """
    return con.execute(query, [selected_asin]).df()

@st.cache_data(ttl=600, show_spinner=False)
def load_reviewer_sample(sample_size: int = 50000):
    # Deteccao dinamica de esquema via metadados puros (sem leitura de dados)
    columns_info = con.execute("DESCRIBE v_reviewers").df()["column_name"].tolist()

    col_rev_count = "total_reviews_by_reviewer"
    if "total_reviews_written" in columns_info:
        col_rev_count = "total_reviews_written"
    elif "total_reviews" in columns_info:
        col_rev_count = "total_reviews"

    col_rev_rating = "avg_rating_given" if "avg_rating_given" in columns_info else "avg_rating"

    query = f"""
        SELECT 
            {col_rev_count} AS total_reviews_written, 
            {col_rev_rating} AS avg_rating_given
        FROM v_reviewers
        USING SAMPLE {sample_size}
    """
    return con.execute(query).df()

@st.cache_data(ttl=120, show_spinner=False)
def load_table_sample(view_name: str, limit: int = 100):
    return con.execute(f"SELECT * FROM {view_name} LIMIT ?", [limit]).df()

# -----------------------------------------------------------------------------
# 3. Renderizacao da Interface
# -----------------------------------------------------------------------------
with st.spinner("Computando indicadores agregados..."):
    kpis = get_global_kpis()

st.subheader("Indicadores de Escala e Centralidade")
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("SKUs Catalogados", f"{kpis['products']:,}")
kpi2.metric("Avaliacoes Consolidadas", f"{kpis['reviews']:,}")
kpi3.metric("Series Temporais (Mes)", f"{kpis['monthly']:,}")
kpi4.metric("Avaliadores Unicos", f"{kpis['reviewers']:,}")
kpi5.metric("Media Ponderada Global", f"{kpis['rating']:.2f} / 5.00")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "Diagnostico de Qualidade e Risco",
    "Series Temporais e Volatilidade",
    "Comportamento de Consumo",
    "Inspecao Tabular de Dados"
])

with tab1:
    st.subheader("Analise de Dispersao e Taxa de Rejeicao")
    st.markdown("""
    Finalidade Tecnica: Identificar anomalias de satisfacao e priorizar intervencoes de catalogo.  
    A taxa de rejeicao quantifica a proporcao de avaliacoes com nota menor ou igual a 2.0.
    """)

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        min_rev_filter = st.slider("Corte Minimo de Avaliacoes por SKU (Filtro de Significancia):", 1, 500, 15)
    with f_col2:
        top_n = st.selectbox("Amostragem de Registros Criticos:", [10, 20, 50], index=1)

    df_top_rej = load_top_rejected_products(min_rev_filter, top_n)
    df_sample_scatter = load_scatter_sample(min_rev_filter, 1000)

    c1, c2 = st.columns(2)
    with c1:
        if not df_top_rej.empty:
            fig_rej = px.bar(
                df_top_rej,
                x='asin',
                y='rejection_rate_pct',
                color='avg_rating',
                title=f"Top {top_n} Produtos com Maior Rejeicao (Score <= 2.0)",
                labels={'asin': 'Codigo ASIN', 'rejection_rate_pct': 'Taxa de Rejeicao (%)', 'avg_rating': 'Nota Media'},
                color_continuous_scale='Turbo'
            )
            st.plotly_chart(fig_rej, width='stretch')
            st.caption("Interpretacao: SKUs com barras elevadas demandam auditoria de conformidade de catalogo.")
        else:
            st.info("Nenhum registro localizado para o filtro selecionado.")

    with c2:
        if not df_sample_scatter.empty:
            fig_scatter = px.scatter(
                df_sample_scatter,
                x='total_reviews',
                y='avg_rating',
                size='rejection_rate_pct',
                color='rejection_rate_pct',
                hover_name='asin',
                log_x=True,
                title="Relacao Volume vs Nota Media (Amostra Estatistica de 1.000 SKUs)",
                labels={'total_reviews': 'Total de Avaliacoes (Log)', 'avg_rating': 'Nota Media', 'rejection_rate_pct': 'Rejeicao %'},
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_scatter, width='stretch')
            st.caption("Interpretacao: Permite diferenciar produtos polarizados de produtos estabilizados com alto volume.")

with tab2:
    st.subheader("Analise Longitudinal e Sazonalidade")
    st.markdown("""
    Finalidade Tecnica: Acompanhar a evolucao temporal de satisfacao dos SKUs com alto volume amostral.
    """)

    top_asins = load_available_asins(30)

    if top_asins:
        selected_asin = st.selectbox("Selecione o ASIN Alvo para Decomposicao Temporal:", top_asins)
        df_target = load_asin_monthly_trend(selected_asin)

        c_time1, c_time2 = st.columns(2)
        with c_time1:
            if not df_target.empty:
                fig_trend = px.line(
                    df_target,
                    x='periodo',
                    y='monthly_avg_rating',
                    markers=True,
                    title=f"Nota Media Mensal - ASIN: {selected_asin}",
                    labels={'periodo': 'Ano-Mes', 'monthly_avg_rating': 'Nota Media'}
                )
                st.plotly_chart(fig_trend, width='stretch')
                st.caption("Interpretacao: Oscilacoes bruscas indicam eventos pontuais de insatisfacao.")
            else:
                st.info("Sem dados temporais para o ASIN selecionado.")

        with c_time2:
            if not df_target.empty:
                fig_v = px.bar(
                    df_target,
                    x='periodo',
                    y='monthly_reviews',
                    title=f"Volume de Avaliacoes Mensais - ASIN: {selected_asin}",
                    labels={'periodo': 'Ano-Mes', 'monthly_reviews': 'Avaliacoes Submetidas'}
                )
                st.plotly_chart(fig_v, width='stretch')
                st.caption("Interpretacao: Avalia a significancia estatistica das notas ao longo do tempo.")
    else:
        st.warning("Nenhum ASIN identificado na camada Gold.")

with tab3:
    st.subheader("Assimetria de Distribuicao e Engajamento")
    st.markdown("""
    Finalidade Tecnica: Segmentacao do comportamento dos avaliadores atraves de histogramas agregados via DuckDB.
    """)

    df_rev_sample = load_reviewer_sample(50000)

    if not df_rev_sample.empty and "total_reviews_written" in df_rev_sample.columns:
        p99 = int(df_rev_sample['total_reviews_written'].quantile(0.99))
        p99 = max(p99, 10)

        c_r1, c_r2 = st.columns(2)
        with c_r1:
            fig_user_vol = px.histogram(
                df_rev_sample[df_rev_sample['total_reviews_written'] <= p99],
                x='total_reviews_written',
                nbins=30,
                title=f"Histograma de Contribuicao por Avaliador (Truncado no P99: {p99})",
                labels={'total_reviews_written': 'Reviews Escritos por Usuario'}
            )
            st.plotly_chart(fig_user_vol, width='stretch')
            st.caption("Interpretacao: Demonstra o comportamento de cauda longa na geracao de avaliacoes.")

        with c_r2:
            fig_user_rates = px.histogram(
                df_rev_sample,
                x='avg_rating_given',
                nbins=20,
                title="Distribuicao das Notas Medias Atribuidas pelos Avaliadores",
                labels={'avg_rating_given': 'Nota Media Fornecida'}
            )
            st.plotly_chart(fig_user_rates, width='stretch')
            st.caption("Interpretacao: Mensura vies de severidade ou leniencia na comunidade.")
    else:
        st.warning("Tabela reviewer_metrics vazia ou colunas nao compativeis.")

with tab4:
    st.subheader("Auditoria dos Registros (Engine OLAP - Limit 100)")
    st.markdown("Inspecao paginada diretamente dos arquivos Parquet para evitar saturacao de memoria RAM.")

    inspect_table = st.radio(
        "Selecione o Data Lakehouse Layer para Inspecao:", 
        ["product_metrics", "monthly_product_metrics", "reviewer_metrics"], 
        horizontal=True
    )

    view_map = {
        "product_metrics": "v_products",
        "monthly_product_metrics": "v_monthly",
        "reviewer_metrics": "v_reviewers"
    }

    sample_df = load_table_sample(view_map[inspect_table], 100)
    st.dataframe(sample_df, height=350)
