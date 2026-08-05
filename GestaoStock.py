#!/usr/bin/env python
# coding: utf-8

# In[1]:


import streamlit as st
import pandas as pd
import sqlite3


# #### CONFIGURAÇÃO DA BASE DE DAD OS

# In[2]:

def criar_tabela():
    conn = sqlite3.connect('Stock.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS produtos(
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nome TEXT, 
        quantidade INTEGER, 
        preco_custo REAL)''')
    conn.commit()
    conn.close()


# #### FUNÇÕES DE MANIPULAÇÃO

# In[3]:


def adicionar_produto (nome, quantidade, preco):
    conn = sqlite3.connect('Stock.db')
    c = conn.cursor()
    c.execute("INSERT INTO produtos (nome, quantidade, preco_custo) VALUES (?,?,?)", (nome, quantidade, preco))
    conn.commit()
    conn.close()

def visualizar_stock():
    conn = sqlite3.connect('Stock.db')
    df = pd.read_sql_query("SELECT nome, quantidade, preco_custo FROM produtos", conn)
    conn.close()
    return df

def eliminar_produto(nome):
    conn = sqlite3.connect('Stock.db')
    c = conn.cursor ()
    c.execute ("DELETE FROM produtos WHERE nome = ?", (nome,))
    conn.commit()
    conn.close()

def baixar_stock (nome, quantidade_a_tirar):
    conn = sqlite3.connect('Stock.db')
    c = conn.cursor()
    c.execute ("UPDATE produtos SET quantidade = quantidade - ? WHERE nome = ? AND quantidade >= ?",
            (quantidade_a_tirar, nome, quantidade_a_tirar))
    conn.commit()
    conn.close()

# #### INTERFACE STREAMLITE

# In[4]:

criar_tabela()
st.set_page_config(page_title = "Gestão de Stock", page_icon = "📦")

st.title("📦 Gestão de Stock")
dados = visualizar_stock()

# #### BARRA LATERAL

# In[5]:

st.sidebar.title ("Configurações")

with st.sidebar.expander ("Novo Produto"):
    nome = st.text_input ("Nome do Produto")
    qtd = st.number_input ("Quantidade", min_value = 0, step = 1)
    preco = st.number_input ("Preço de Custo (€)", min_value = 0.0, format = "%.2f")

    if st.button ("Registar Stock"):
        if nome:
            adicionar_produto (nome, qtd, preco)
            st.success(f"Successo: {nome} registado!")
        else:
            st.error ("Erro: O nome é obrigatório.")

st.sidebar.divider()
st.sidebar.subheader ("Eliminar Produtos")

if not dados.empty:
    produto_a_eliminar = st.sidebar.selectbox ("Escolha o Produto a Eliminar", dados['nome'].unique())   

if st.sidebar.button ("Eliminar Permanentemente"):
        eliminar_produto (produto_a_eliminar)
        st.sidebar.error (f"'{produto_a_eliminar} Removido!")

else:
    st.sidebar.write ("Não existem produtos a eliminar")

st.sidebar.divider ()
st.sidebar.subheader ("Saída de Produtos")

dados = visualizar_stock()

if not dados.empty:
    prod_uso = st.sidebar.selectbox("Produto utilizado:", dados['nome'].unique(), key="Utilizado")
    qtd_uso = st.sidebar.number_input("Quantidade usada:", min_value=1, value=1)

    if st.sidebar.button("Confirmar Saída"):
        baixar_stock(prod_uso, qtd_uso)
        st.sidebar.warning(f"Retiradas {qtd_uso} unidades de {prod_uso}")
        st.rerun()

# #### BARRA LATERAL

# In[6]:

st.subheader ("Inventário Atual")
dados = visualizar_stock()

if not dados.empty:
    st.dataframe (dados, use_container_width = True)

else:
    st.info ("Stock vazio. Adicionar produtos na barra lateral.")