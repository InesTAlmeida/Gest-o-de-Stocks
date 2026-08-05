#!/usr/bin/env python
# coding: utf-8

# In[1]:

import streamlit as st
import pandas as pd
import sqlite3

# #### CONFIGURAÇÃO DA BASE DE DADOS
def criar_tabela():
    conn = sqlite3.connect('Stock.db')
    c = conn.cursor()
    # Removidos espaços dos nomes das colunas e adicionados os tipos de dados corretos
    c.execute('''CREATE TABLE IF NOT EXISTS produtos(
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        Nome TEXT, 
        Quantidade INTEGER, 
        Preco_Custo REAL,
        Preco_Venda REAL,      
        Categoria TEXT)''')
    conn.commit()
    conn.close()

# #### FUNÇÕES DE MANIPULAÇÃO
def adicionar_produto(Nome, Quantidade, Preco_Custo, Preco_Venda, Categoria):
    conn = sqlite3.connect('Stock.db')
    c = conn.cursor()
    # Adicionados os 5 pontos de interrogação correspondentes às 5 colunas
    c.execute("INSERT INTO produtos (Nome, Quantidade, Preco_Custo, Preco_Venda, Categoria) VALUES (?,?,?,?,?)", 
              (Nome, Quantidade, Preco_Custo, Preco_Venda, Categoria))
    conn.commit()
    conn.close()

def visualizar_stock():
    conn = sqlite3.connect('Stock.db')
    # Nomes das colunas corrigidos para coincidir com a criação da tabela
    df = pd.read_sql_query("SELECT Nome, Quantidade, Preco_Custo, Preco_Venda, Categoria FROM produtos", conn)
    conn.close()
    return df

def eliminar_produto(nome):
    conn = sqlite3.connect('Stock.db')
    c = conn.cursor()
    c.execute("DELETE FROM produtos WHERE Nome = ?", (nome,))
    conn.commit()
    conn.close()

def baixar_stock(nome, quantidade_a_tirar):
    conn = sqlite3.connect('Stock.db')
    c = conn.cursor()
    c.execute("UPDATE produtos SET Quantidade = Quantidade - ? WHERE Nome = ? AND Quantidade >= ?",
            (quantidade_a_tirar, nome, quantidade_a_tirar))
    conn.commit()
    conn.close()

def repor_stock(nome, quantidade_a_adicionar):
    conn = sqlite3.connect('Stock.db')
    c = conn.cursor()
    c.execute("UPDATE produtos SET Quantidade = Quantidade + ? WHERE Nome = ?", 
              (quantidade_a_adicionar, nome))
    conn.commit()
    conn.close()

# #### INTERFACE STREAMLIT
criar_tabela()
st.set_page_config(page_title="Gestão de Stock", page_icon="📦")

st.title("📦 Gestão de Stock")

try:
    dados = visualizar_stock()
except:
    dados = pd.DataFrame(columns=["Nome", "Quantidade", "Preco_Custo", "Preco_Venda", "Categoria"])

# #### BARRA LATERAL
st.sidebar.title("Definições")

# 1: REGISTAR NOVO PRODUTO
with st.sidebar.expander("Novo Produto"):
    nome_input = st.text_input("Nome do Produto", key="novo_nome")
    qtd_input = st.number_input("Quantidade", min_value=0, step=1, key="novo_qtd")
    preco_c_input = st.number_input("Preço de Custo (€)", min_value=0.0, format="%.2f", key="novo_preco")
    preco_v_input = st.number_input("Preço de Venda (€)", min_value=0.0, format="%.2f", key="novo_precov")
    cat_input = st.selectbox("Categoria", ["Uso Técnico", "Revenda", "Acessórios"], key="novo_cat")

    if st.button("Registar no Sistema"):
        if nome_input:
            adicionar_produto(nome_input, qtd_input, preco_c_input, preco_v_input, cat_input)
            st.success(f"{nome_input} registado!")
            st.rerun()
        else:
            st.error("O nome é obrigatório.")

# 2: REPOSIÇÃO
with st.sidebar.expander("Reposição (Entrada)"):
    if not dados.empty:
        prod_repo = st.selectbox("Produto a repor:", dados['Nome'].unique(), key="repo_prod")
        qtd_repo = st.number_input("Quantidade a somar:", min_value=1, value=1, key="repo_qtd")
        if st.button("Confirmar Reposição"):
            repor_stock(prod_repo, qtd_repo)
            st.success(f"Reposto: {prod_repo}")
            st.rerun()
    else:
        st.write("Sem produtos.")

# 3: SAÍDA
with st.sidebar.expander("Saída (Utilização)"):
    if not dados.empty:
        prod_uso = st.selectbox("Produto utilizado:", dados['Nome'].unique(), key="uso_prod")
        qtd_uso = st.number_input("Quantidade a retirar:", min_value=1, value=1, key="uso_qtd")
        if st.button("Confirmar Saída"):
            baixar_stock(prod_uso, qtd_uso)
            st.warning(f"Retirado: {prod_uso}")
            st.rerun()
    else:
        st.write("Sem produtos.")

# 4: ELIMINAR PERMANENTEMENTE
with st.sidebar.expander("Eliminar do Inventário"):
    if not dados.empty:
        produto_a_eliminar = st.selectbox("Produto a apagar:", dados['Nome'].unique(), key="del_prod")   
        if st.button("Eliminar Permanentemente"):
            eliminar_produto(produto_a_eliminar)
            st.error(f"Sucesso: {produto_a_eliminar} removido!")
            st.rerun()
    else:
        st.write("Nada a eliminar.")

# #### ESTATISTICAS
if not dados.empty:
    st.subheader("📊 Resumo Financeiro")

    valor_total_custo = (dados['Preco_Custo'] * dados['Quantidade']).sum()
    valor_total_venda = (dados['Preco_Venda'] * dados['Quantidade']).sum()
    lucro = valor_total_venda - valor_total_custo
    quantidade_total = dados['Quantidade'].sum()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Investimento Total (Custo)", f"{valor_total_custo :.2f} €")

    with col2:
        st.metric("Total de Vendas", f"{valor_total_venda :.2f} €")

    with col3:
        st.metric("Lucro (Estimativa)", f"{lucro:.2f} €",)
        st.write(f"Itens em Stock: {int(quantidade_total)}")

    st.divider()


# #### RESULTADOS

st.subheader("📋 Inventário Atual")
dados = visualizar_stock() 

if not dados.empty:
    def cor_stock_baixo(row):
        qtd = row.get('Quantidade', 0) 
        if qtd < 3:
            return ['background-color: #ffcccc; color: black'] * len(row)
        elif 3 <= qtd <= 5:
            return ['background-color: #ffffcc; color: black'] * len(row)
        return [''] * len(row)

    try:
        estilo = dados.style.apply(cor_stock_baixo, axis=1)
        estilo = estilo.format({
            "Preco_Custo": "{:.2f} €",
            "Preco_Venda": "{:.2f} €"
        }, na_rep="-")
        
        st.dataframe(estilo, use_container_width=True)
    except Exception as e:
        st.dataframe(dados, use_container_width=True)
        st.error(f"Erro ao formatar visualmente: {e}")

    st.caption("🔴 Vermelho: Stock Crítico (< 3) | 🟡 Amarelo: Stock Baixo (3-5)")
else:
    st.info("O stock está vazio. Adiciona produtos na barra lateral.")

    
