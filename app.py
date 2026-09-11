import streamlit as st
import duckdb
import plotly.express as px
import pandas as pd

st.set_page_config(
    page_title="Lakehouse Reviews - Gold Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Lakehouse Analytics - Métricas Gold")
st.markdown("Visão executiva das métricas salvas no MinIO via DuckDB.")

# Conexão DuckDB com MinIO (S3 Local)
@st.cache_resource
def get_duckdb_connection():
    con = duckdb.connect()
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
    """)
    return con

con = get_duckdb_connection()

# Carregamento com busca recursiva e hive_partitioning
@st.cache_data(ttl=600)
def load_gold_data():
    queries = {
        "products": "SELECT * FROM read_parquet('s3://lakehouse/gold/product_metrics/**/*.parquet', hive_partitioning=true)",
        "monthly": "SELECT * FROM read_parquet('s3://lakehouse/gold/monthly_product_metrics/**/*.parquet', hive_partitioning=true)",
        "reviewers": "SELECT * FROM read_parquet('s3://lakehouse/gold/reviewer_metrics/**/*.parquet', hive_partitioning=true)"
    }
    
    data = {}
    for name, query in queries.items():
        try:
            data[name] = con.execute(query).df()
        except Exception as e:
            st.error(f"Erro ao carregar dados de `{name}`: {e}")
            data[name] = pd.DataFrame()
            
    return data["products"], data["monthly"], data["reviewers"]

with st.spinner("Carregando tabelas Gold do MinIO..."):
    df_products, df_monthly, df_reviewers = load_gold_data()

# 1. KPI Cards Gerais
st.subheader("📌 Indicadores Gerais")
col1, col2, col3, col4 = st.columns(4)

total_products = len(df_products)
total_monthly_records = len(df_monthly)
total_reviewers = len(df_reviewers)
global_avg_rating = df_products['avg_rating'].mean() if 'avg_rating' in df_products.columns and not df_products.empty else 0.0

col1.metric("Total de Produtos Únicos", f"{total_products:,}")
col2.metric("Pontos Mensais Agregados", f"{total_monthly_records:,}")
col3.metric("Total de Avaliadores", f"{total_reviewers:,}")
col4.metric("Nota Média Global", f"{global_avg_rating:.2f} ⭐")

st.divider()

# 2. Visualizações em Abas
tab1, tab2, tab3 = st.tabs(["📦 Produtos & Rejeição", "📈 Tendência Temporal", "👤 Perfis de Avaliadores"])

with tab1:
    st.subheader("Top Produtos por Taxa de Rejeição (%)")
    
    if not df_products.empty and {'asin', 'total_reviews', 'rejection_rate_pct'}.issubset(df_products.columns):
        max_vol = int(df_products['total_reviews'].max()) if df_products['total_reviews'].max() > 1 else 100
        min_reviews = st.slider("Mínimo de avaliações recebidas:", min_value=1, max_value=min(max_vol, 500), value=min(10, max_vol))
        
        df_filtered = df_products[df_products['total_reviews'] >= min_reviews].sort_values(
            by='rejection_rate_pct', ascending=False
        ).head(15)
        
        if not df_filtered.empty:
            fig_bar = px.bar(
                df_filtered,
                x='asin',
                y='rejection_rate_pct',
                color='rejection_rate_pct',
                title="Top 15 Produtos com Maior Rejeição (Notas <= 2)",
                labels={'asin': 'Produto (ASIN)', 'rejection_rate_pct': 'Taxa de Rejeição (%)'},
                hover_data=['total_reviews', 'avg_rating'],
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_bar, width='stretch')
        else:
            st.info("Nenhum produto atende ao filtro de avaliações selecionado.")
    else:
        st.warning("Dados de `product_metrics` incompletos ou vazios.")

with tab2:
    st.subheader("Evolução Temporal das Avaliações")
    
    if not df_monthly.empty and 'asin' in df_monthly.columns:
        # Tratamento da coluna de período
        if 'review_year' in df_monthly.columns and 'review_month' in df_monthly.columns:
            df_monthly['periodo'] = df_monthly['review_year'].astype(str) + "-" + df_monthly['review_month'].astype(str).str.zfill(2)
        elif 'review_year_month' in df_monthly.columns:
            df_monthly['periodo'] = df_monthly['review_year_month'].astype(str)
        else:
            df_monthly['periodo'] = df_monthly.index.astype(str)

        rating_col = 'monthly_avg_rating' if 'monthly_avg_rating' in df_monthly.columns else 'avg_rating'
        
        # Seleção dos 20 produtos com mais registros
        sample_asins = df_monthly['asin'].value_counts().head(20).index.tolist()
        if not df_products.empty and 'total_reviews' in df_products.columns:
            sample_asins = df_products.sort_values(by='total_reviews', ascending=False)['asin'].head(20).tolist()
            
        selected_asin = st.selectbox("Selecione um Produto de Alto Volume:", sample_asins)
        
        if selected_asin:
            df_prod_trend = df_monthly[df_monthly['asin'] == selected_asin].sort_values(by='periodo')
            
            fig_line = px.line(
                df_prod_trend,
                x='periodo',
                y=rating_col,
                markers=True,
                title=f"Evolução Temporal da Nota Média - ASIN {selected_asin}",
                labels={'periodo': 'Mês/Ano', rating_col: 'Nota Média Mensal'}
            )
            st.plotly_chart(fig_line, width='stretch')
            
            if 'monthly_reviews' in df_prod_trend.columns:
                fig_volume = px.bar(
                    df_prod_trend,
                    x='periodo',
                    y='monthly_reviews',
                    title=f"Volume de Avaliações por Mês - ASIN {selected_asin}",
                    labels={'periodo': 'Mês/Ano', 'monthly_reviews': 'Quantidade de Avaliações'}
                )
                st.plotly_chart(fig_volume, width='stretch')
    else:
        st.warning("Dados de `monthly_product_metrics` incompletos ou vazios.")

with tab3:
    st.subheader("Comportamento dos Avaliadores")
    
    reviewer_count_cols = ['total_reviews_written', 'total_reviews_by_reviewer', 'total_reviews', 'review_count']
    rev_col = next((c for c in reviewer_count_cols if c in df_reviewers.columns), None)
    
    if not df_reviewers.empty and rev_col:
        col_r1, col_r2 = st.columns(2)
        
        p99 = int(df_reviewers[rev_col].quantile(0.99)) if len(df_reviewers) > 10 else 50
        
        with col_r1:
            fig_hist = px.histogram(
                df_reviewers[df_reviewers[rev_col] <= p99],
                x=rev_col,
                nbins=30,
                title=f"Distribuição de Reviews por Usuário (Até Percentil 99: {p99})",
                labels={rev_col: 'Avaliações Escritas'}
            )
            st.plotly_chart(fig_hist, width='stretch')
            
        with col_r2:
            rating_rev_col = 'avg_rating_given' if 'avg_rating_given' in df_reviewers.columns else 'avg_rating'
            if rating_rev_col in df_reviewers.columns:
                fig_ratings = px.histogram(
                    df_reviewers,
                    x=rating_rev_col,
                    nbins=20,
                    title="Distribuição das Notas Médias Dadas pelos Usuários",
                    labels={rating_rev_col: 'Nota Média Dada'}
                )
                st.plotly_chart(fig_ratings, width='stretch')
    else:
        st.warning("Dados de `reviewer_metrics` incompletos ou coluna de contagem não encontrada.")
