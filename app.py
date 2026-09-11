import streamlit as st
import duckdb
import plotly.express as px
import pandas as pd

st.set_page_config(
    page_title="Lakehouse Reviews Analytics",
    page_icon="📊",
    layout="wide"
)

# -----------------------------------------------------------------------------
# Conexão DuckDB com MinIO (S3 Local) via httpfs
# -----------------------------------------------------------------------------
@st.cache_resource
def get_duckdb_connection():
    con = duckdb.connect(database=":memory:")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("""
        SET s3_endpoint='localhost:9000';
        SET s3_access_key_id='minioadmin';
        SET s3_secret_access_key='minioadmin';
        SET s3_use_ssl=false;
        SET s3_url_style='path';
        SET max_memory='1GB';
        SET preserve_insertion_order=false;
    """)
    # Views analíticas com pushdown, leitura recursiva e particionamento Hive
    con.execute("""
        CREATE OR REPLACE VIEW v_product_metrics AS 
        SELECT * FROM read_parquet(
            's3://lakehouse/gold/product_metrics/**/*.parquet', 
            hive_partitioning=true
        );
    """)
    con.execute("""
        CREATE OR REPLACE VIEW v_monthly_product_metrics AS 
        SELECT * FROM read_parquet(
            's3://lakehouse/gold/monthly_product_metrics/**/*.parquet', 
            hive_partitioning=true
        );
    """)
    con.execute("""
        CREATE OR REPLACE VIEW v_reviewer_metrics AS 
        SELECT * FROM read_parquet(
            's3://lakehouse/gold/reviewer_metrics/**/*.parquet', 
            hive_partitioning=true
        );
    """)
    return con

try:
    con = get_duckdb_connection()
except Exception as e:
    st.error(f"Erro ao conectar ao MinIO/DuckDB: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# Funções de Carregamento com Agregação Pushdown
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_kpi_summary():
    query = """
        SELECT 
            COUNT(DISTINCT asin) AS total_products,
            SUM(total_reviews) AS total_reviews_sum,
            ROUND(AVG(avg_rating), 2) AS overall_avg_rating,
            ROUND(AVG(rejection_rate_pct), 2) AS avg_rejection_rate
        FROM v_product_metrics
    """
    return con.execute(query).df()

@st.cache_data(ttl=300)
def load_top_products(limit=15):
    query = f"""
        SELECT 
            asin,
            total_reviews,
            avg_rating,
            rejection_rate_pct
        FROM v_product_metrics
        ORDER BY total_reviews DESC
        LIMIT {limit}
    """
    return con.execute(query).df()

@st.cache_data(ttl=300)
def load_monthly_trends(selected_asin=None):
    if selected_asin and selected_asin != "Todos":
        query = f"""
            SELECT 
                review_year,
                review_month,
                printf('%04d-%02d', review_year, review_month) AS year_month,
                SUM(monthly_reviews) AS total_monthly_reviews,
                ROUND(AVG(monthly_avg_rating), 2) AS monthly_avg_rating
            FROM v_monthly_product_metrics
            WHERE asin = '{selected_asin}'
            GROUP BY review_year, review_month
            ORDER BY review_year, review_month
        """
    else:
        query = """
            SELECT 
                review_year,
                review_month,
                printf('%04d-%02d', review_year, review_month) AS year_month,
                SUM(monthly_reviews) AS total_monthly_reviews,
                ROUND(AVG(monthly_avg_rating), 2) AS monthly_avg_rating
            FROM v_monthly_product_metrics
            GROUP BY review_year, review_month
            ORDER BY review_year, review_month
        """
    return con.execute(query).df()

@st.cache_data(ttl=300)
def load_top_reviewers(limit=15):
    raw_df = con.execute("SELECT * FROM v_reviewer_metrics LIMIT 1").df()
    
    # Tratamento defensivo dinâmico para schema da camada Gold
    candidate_cols = ["total_reviews_by_reviewer", "total_reviews_written", "total_reviews"]
    target_col = next((c for c in candidate_cols if c in raw_df.columns), "total_reviews_by_reviewer")

    query = f"""
        SELECT 
            reviewerID,
            {target_col} AS reviews_count,
            ROUND(avg_rating_given, 2) AS avg_rating_given
        FROM v_reviewer_metrics
        ORDER BY {target_col} DESC
        LIMIT {limit}
    """
    return con.execute(query).df()

# -----------------------------------------------------------------------------
# Interface e Visualização
# -----------------------------------------------------------------------------
st.title("📚 Lakehouse Analytics - Amazon Reviews (Gold Layer)")
st.caption("Serving analítico vetorizado via DuckDB + MinIO S3 com pushdown de projeção")

# Resumo Executivo (KPIs)
kpi_df = load_kpi_summary()
if not kpi_df.empty:
    col1, col2, col3, col4 = st.columns(4)
    total_prod = kpi_df["total_products"].iloc[0] if "total_products" in kpi_df.columns else 0
    total_rev = kpi_df["total_reviews_sum"].iloc[0] if "total_reviews_sum" in kpi_df.columns else 0
    avg_rate = kpi_df["overall_avg_rating"].iloc[0] if "overall_avg_rating" in kpi_df.columns else 0.0
    rej_rate = kpi_df["avg_rejection_rate"].iloc[0] if "avg_rejection_rate" in kpi_df.columns else 0.0

    col1.metric("Produtos Catalogados", f"{int(total_prod):,}" if pd.notnull(total_prod) else "0")
    col2.metric("Total de Avaliações", f"{int(total_rev):,}" if pd.notnull(total_rev) else "0")
    col3.metric("Nota Média Geral", f"{avg_rate:.2f} ⭐" if pd.notnull(avg_rate) else "0.00 ⭐")
    col4.metric("Taxa Média de Rejeição", f"{rej_rate:.2f}%" if pd.notnull(rej_rate) else "0.00%")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🏆 Produtos em Destaque", "📈 Série Histórica Mensal", "👥 Perfil dos Avaliadores"])

with tab1:
    st.subheader("Top Produtos por Volume de Avaliações")
    df_top_prod = load_top_products()
    
    if not df_top_prod.empty:
        col_chart, col_table = st.columns([3, 2])
        with col_chart:
            fig_prod = px.bar(
                df_top_prod,
                x="asin",
                y="total_reviews",
                color="avg_rating",
                color_continuous_scale="Blues",
                labels={"asin": "ASIN", "total_reviews": "Total Reviews", "avg_rating": "Nota Média"},
                title="Top 15 Produtos com Mais Reviews"
            )
            fig_prod.update_layout(margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_prod, width='stretch')
        
        with col_table:
            st.dataframe(df_top_prod, hide_index=True)
    else:
        st.warning("Nenhum dado encontrado para product_metrics.")

with tab2:
    st.subheader("Evolução Temporal de Avaliações")
    top_asins_list = ["Todos"]
    df_asins = con.execute("SELECT DISTINCT asin FROM v_product_metrics ORDER BY asin LIMIT 50").df()
    if not df_asins.empty and "asin" in df_asins.columns:
        top_asins_list.extend(df_asins["asin"].dropna().tolist())
    
    selected_asin = st.selectbox("Filtrar por ASIN:", top_asins_list)
    df_trends = load_monthly_trends(selected_asin)
    
    if not df_trends.empty:
        fig_trend = px.line(
            df_trends,
            x="year_month",
            y="total_monthly_reviews",
            markers=True,
            labels={"year_month": "Ano-Mês", "total_monthly_reviews": "Reviews no Mês"},
            title=f"Tendência Mensal ({selected_asin})"
        )
        fig_trend.update_layout(margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_trend, width='stretch')
    else:
        st.warning("Sem dados históricos para a seleção informada.")

with tab3:
    st.subheader("Avaliadores Mais Ativos")
    df_reviewers = load_top_reviewers()
    
    if not df_reviewers.empty:
        col_rev_chart, col_rev_table = st.columns([3, 2])
        with col_rev_chart:
            fig_rev = px.bar(
                df_reviewers,
                x="reviewerID",
                y="reviews_count",
                color="avg_rating_given",
                color_continuous_scale="Teal",
                labels={"reviewerID": "Avaliador", "reviews_count": "Reviews Feitos", "avg_rating_given": "Nota Média"},
                title="Top Avaliadores por Volume"
            )
            fig_rev.update_layout(margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_rev, width='stretch')
        
        with col_rev_table:
            st.dataframe(df_reviewers, hide_index=True)
    else:
        st.warning("Nenhum dado encontrado para reviewer_metrics.")
