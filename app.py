import streamlit as st
from mock_data import get_mock_inventory

# Configuração da página
st.set_page_config(
    page_title="Gestão de Stocks (Demo)",
    page_icon="📦",
    layout="wide"
)

# Título e Descrição
st.title("📦 Sistema de Gestão de Stocks — Salão de Beleza")
st.caption("Versão de demonstração para portfólio (Dados Fictícios)")

# Carregar dados
df_stocks = get_mock_inventory()

# --- KPI METRICS ---
col1, col2, col3, col4 = st.columns(4)

total_produtos = len(df_stocks)
produtos_alerta = len(df_stocks[df_stocks["quantidade_stock"] <= df_stocks["stock_minimo"]])
valor_total_custo = (df_stocks["quantidade_stock"] * df_stocks["preco_custo"]).sum()
valor_total_venda = (df_stocks["quantidade_stock"] * df_stocks["preco_venda"]).sum()

col1.metric("Total de Produtos", total_produtos)
col2.metric("Produtos em Alerta", produtos_alerta, delta_color="inverse")
col3.metric("Valor em Stock (Custo)", f"{valor_total_custo:.2f} €")
col4.metric("Valor Potencial (Venda)", f"{valor_total_venda:.2f} €")

st.divider()

# --- FILTROS ---
st.subheader("Filtros")
categorias = ["Todas"] + list(df_stocks["categoria"].unique())
categoria_selecionada = st.selectbox("Filtrar por Categoria:", categorias)

df_filtrado = df_stocks.copy()
if categoria_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado["categoria"] == categoria_selecionada]

# --- TABELA DE DADOS ---
st.subheader("Inventário Atual")
st.dataframe(
    df_filtrado,
    use_container_width=True,
    column_config={
        "preco_custo": st.column_config.NumberColumn("Preço Custo", format="%.2f €"),
        "preco_venda": st.column_config.NumberColumn("Preço Venda", format="%.2f €"),
    }
)