import streamlit as st
import duckdb
import plotly.express as px
import pandas as pd

st.set_page_config(
    page_title="Lakehouse Reviews - Gold Analytics Engine",
    layout="wide"
)

st.title("Lakehouse Analytics - Camada Gold")
st.caption("Painel analítico operacional com DuckDB Pushdown e alocação controlada de memória sobre o MinIO.")

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
        SET max_memory='1GB';
        SET preserve_insertion_order=false;
    """)
    return con

con = get_duckdb_connection()

# Criação de Views Lazy (Zero carregamento prévio em RAM)
@st.cache_resource
def setup_views():
    con.execute("""
        CREATE OR REPLACE VIEW v_products AS 
        SELECT * FROM read_parquet('s3://lakehouse/gold/product_metrics/**/*.parquet', hive_partitioning=true);
        
        CREATE OR REPLACE VIEW v_monthly AS 
        SELECT * FROM read_parquet('s3://lakehouse/gold/monthly_product_metrics/**/*.parquet', hive_partitioning=true);
        
        CREATE OR REPLACE VIEW v_reviewers AS 
        SELECT * FROM read_parquet('s3://lakehouse/gold/reviewer_metrics/**/*.parquet', hive_partitioning=true);
    """)

setup_views()

# Agregações leves direto no DuckDB (Pushdown)
@st.cache_data(ttl=600)
def get_global_kpis():
    query = """
        SELECT 
            COUNT(*) AS total_products,
            COALESCE(SUM(total_reviews), 0) AS total_reviews_sum,
            COALESCE(AVG(avg_rating), 0.0) AS global_avg_rating
        FROM v_products
    """
    df_prod_kpis = con.execute(query).df()
    
    total_monthly = con.execute("SELECT COUNT(*) AS total FROM v_monthly").fetchone()[0]
    total_reviewers = con.execute("SELECT COUNT(*) AS total FROM v_reviewers").fetchone()[0]
    
    return {
        "products": int(df_prod_kpis["total_products"][0]),
        "reviews": int(df_prod_kpis["total_reviews_sum"][0]),
        "rating": float(df_prod_kpis["global_avg_rating"][0]),
        "monthly": int(total_monthly),
        "reviewers": int(total_reviewers)
    }

with st.spinner("Computando indicadores agregados..."):
    kpis = get_global_kpis()

st.subheader("Indicadores de Escala e Centralidade")
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("SKUs Catalogados", f"{kpis['products']:,}")
kpi2.metric("Avaliações Consolidadas", f"{kpis['reviews']:,}")
kpi3.metric("Séries Temporais (Mês)", f"{kpis['monthly']:,}")
kpi4.metric("Avaliadores Únicos", f"{kpis['reviewers']:,}")
kpi5.metric("Média Ponderada Global", f"{kpis['rating']:.2f} / 5.00")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "Diagnóstico de Qualidade e Risco",
    "Séries Temporais e Volatilidade",
    "Comportamento de Consumo",
    "Inspeção Tabular de Dados"
])

with tab1:
    st.subheader("Análise de Dispersão e Taxa de Rejeição")
    st.markdown("""
    **Finalidade Técnica:** Identificar anomalias de satisfação e priorizar intervenções de catálogo.  
    A taxa de rejeição quantifica a proporção de avaliações com nota menor ou igual a 2.0.
    """)
    
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        min_rev_filter = st.slider("Corte Mínimo de Avaliações por SKU (Filtro de Significância):", 1, 500, 15)
    with f_col2:
        top_n = st.selectbox("Amostragem de Registros Críticos:", [10, 20, 50], index=1)

    query_tab1 = f"""
        SELECT asin, total_reviews, avg_rating, rejection_rate_pct 
        FROM v_products 
        WHERE total_reviews >= {min_rev_filter}
        ORDER BY rejection_rate_pct DESC 
        LIMIT {top_n}
    """
    df_top_rej = con.execute(query_tab1).df()

    query_sample = f"""
        SELECT asin, total_reviews, avg_rating, rejection_rate_pct 
        FROM v_products 
        WHERE total_reviews >= {min_rev_filter}
        USING SAMPLE 1000
    """
    df_sample_scatter = con.execute(query_sample).df()

    c1, c2 = st.columns(2)
    with c1:
        if not df_top_rej.empty:
            fig_rej = px.bar(
                df_top_rej,
                x='asin',
                y='rejection_rate_pct',
                color='avg_rating',
                title=f"Top {top_n} Produtos com Maior Rejeição (Score <= 2.0)",
                labels={'asin': 'Código ASIN', 'rejection_rate_pct': 'Taxa de Rejeição (%)', 'avg_rating': 'Nota Média'},
                color_continuous_scale='Turbo'
            )
            st.plotly_chart(fig_rej, width='stretch')
            st.caption("Interpretação: SKUs com barras elevadas demandam auditoria de conformidade de catálogo.")
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
                title="Relação Volume vs Nota Média (Amostra Estatística de 1.000 SKUs)",
                labels={'total_reviews': 'Total de Avaliações (Log)', 'avg_rating': 'Nota Média', 'rejection_rate_pct': 'Rejeição %'},
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_scatter, width='stretch')
            st.caption("Interpretação: Permite diferenciar produtos polarizados de produtos estabilizados com alto volume.")

with tab2:
    st.subheader("Análise Longitudinal e Sazonalidade")
    st.markdown("""
    **Finalidade Técnica:** Acompanhar a evolução temporal de satisfação dos SKUs com alto volume amostral.
    """)
    
    top_asins = con.execute("""
        SELECT asin 
        FROM v_products 
        ORDER BY total_reviews DESC 
        LIMIT 30
    """).df()['asin'].tolist()

    if top_asins:
        selected_asin = st.selectbox("Selecione o ASIN Alvo para Decomposição Temporal:", top_asins)
        
        query_trend = f"""
            SELECT 
                PRINTF('%d-%02d', review_year, review_month) AS periodo,
                monthly_reviews,
                monthly_avg_rating
            FROM v_monthly
            WHERE asin = '{selected_asin}'
            ORDER BY review_year, review_month
        """
        df_target = con.execute(query_trend).df()

        c_time1, c_time2 = st.columns(2)
        with c_time1:
            if not df_target.empty:
                fig_trend = px.line(
                    df_target,
                    x='periodo',
                    y='monthly_avg_rating',
                    markers=True,
                    title=f"Nota Média Mensal - ASIN: {selected_asin}",
                    labels={'periodo': 'Ano-Mês', 'monthly_avg_rating': 'Nota Média'}
                )
                st.plotly_chart(fig_trend, width='stretch')
                st.caption("Interpretação: Oscilações bruscas indicam eventos pontuais de insatisfação.")
            else:
                st.info("Sem dados temporais para o ASIN selecionado.")

        with c_time2:
            if not df_target.empty:
                fig_v = px.bar(
                    df_target,
                    x='periodo',
                    y='monthly_reviews',
                    title=f"Volume de Avaliações Mensais - ASIN: {selected_asin}",
                    labels={'periodo': 'Ano-Mês', 'monthly_reviews': 'Avaliações Submetidas'}
                )
                st.plotly_chart(fig_v, width='stretch')
                st.caption("Interpretação: Avalia a significância estatística das notas ao longo do tempo.")
    else:
        st.warning("Nenhum ASIN identificado na camada Gold.")

with tab3:
    st.subheader("Assimetria de Distribuição e Engajamento")
    st.markdown("""
    **Finalidade Técnica:** Segmentação do comportamento dos avaliadores através de histogramas agregados via DuckDB.
    """)
    
    df_rev_sample = con.execute("""
        SELECT total_reviews_written, avg_rating_given
        FROM v_reviewers
        USING SAMPLE 50000
    """).df()

    if not df_rev_sample.empty:
        p99 = int(df_rev_sample['total_reviews_written'].quantile(0.99))
        p99 = max(p99, 10)
        
        c_r1, c_r2 = st.columns(2)
        with c_r1:
            fig_user_vol = px.histogram(
                df_rev_sample[df_rev_sample['total_reviews_written'] <= p99],
                x='total_reviews_written',
                nbins=30,
                title=f"Histograma de Contribuição por Avaliador (Truncado no P99: {p99})",
                labels={'total_reviews_written': 'Reviews Escritos por Usuário'}
            )
            st.plotly_chart(fig_user_vol, width='stretch')
            st.caption("Interpretação: Demonstra o comportamento de cauda longa na geração de avaliações.")

        with c_r2:
            fig_user_rates = px.histogram(
                df_rev_sample,
                x='avg_rating_given',
                nbins=20,
                title="Distribuição das Notas Médias Atribuídas pelos Avaliadores",
                labels={'avg_rating_given': 'Nota Média Fornecida'}
            )
            st.plotly_chart(fig_user_rates, width='stretch')
            st.caption("Interpretação: Mensura viés de severidade ou leniência na comunidade.")
    else:
        st.warning("Tabela `reviewer_metrics` vazia ou colunas não compatíveis.")

with tab4:
    st.subheader("Auditoria dos Registros (Engine OLAP - Limit 100)")
    st.markdown("Inspeção paginada diretamente dos arquivos Parquet para evitar saturação de memória RAM.")
    
    inspect_table = st.radio(
        "Selecione o Data Lakehouse Layer para Inspeção:", 
        ["product_metrics", "monthly_product_metrics", "reviewer_metrics"], 
        horizontal=True
    )
    
    view_map = {
        "product_metrics": "v_products",
        "monthly_product_metrics": "v_monthly",
        "reviewer_metrics": "v_reviewers"
    }
    
    sample_df = con.execute(f"SELECT * FROM {view_map[inspect_table]} LIMIT 100").df()
    st.dataframe(sample_df, height=350)
