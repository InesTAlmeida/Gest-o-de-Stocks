#!/usr/bin/env python
# coding: utf-8

# In[1]:

from datetime import datetime
import streamlit as st
import pandas as pd
import sqlite3

# In[2]:
# #### CONFIGURAÇÃO DA BASE DE DADOS
def criar_tabelas():
    conn = sqlite3.connect('Stock.db')
    c = conn.cursor()
    
    # 1. Tabela de produtos (Stock atual)
    c.execute('''CREATE TABLE IF NOT EXISTS produtos(
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        Nome TEXT UNIQUE, 
        Quantidade INTEGER, 
        Preco_Custo REAL,
        Preco_Venda REAL,      
        Categoria TEXT)''')

    # 2. Tabela de faturas
    c.execute('''CREATE TABLE IF NOT EXISTS faturas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_fatura TEXT,
        fornecedor TEXT,
        data_compra TEXT,
        nome_produto TEXT,
        quantidade INTEGER,
        preco_unitario REAL,
        lote TEXT,
        validade TEXT)''')
    
    # 3. Tabela de movimentos (Histórico de saídas e utilizações)
    c.execute('''CREATE TABLE IF NOT EXISTS movimentos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_movimento TEXT,
        nome_produto TEXT,
        quantidade INTEGER,
        tipo_movimento TEXT)''')
        
    conn.commit()
    conn.close()

# In[3]:
# #### DEFINIÇÕES DE MANIPULAÇÃO DA BASE DE DADOS
# Registar nova compra (entrada de stock) / Atualizar inventário
def registar_compra(num_fatura, fornecedor, data_compra, nome, quant, preco_un, venda_un, categoria, lote, validade):
    conn = sqlite3.connect('Stock.db')
    cursor = conn.cursor()
    
    # Inserir registos detalhados
    cursor.execute('''
        INSERT INTO faturas (numero_fatura, fornecedor, data_compra, nome_produto, quantidade, preco_unitario, lote, validade)
        VALUES (?,?,?,?,?,?,?,?)
    ''', (num_fatura, fornecedor, data_compra, nome, quant, preco_un, lote, validade))

    # Verificar se o produto já existe em stock para somar a quantidade / criar um novo
    cursor.execute('SELECT Quantidade FROM produtos WHERE Nome = ?', (nome,))
    resultado = cursor.fetchone()

    if resultado:
        nova_qtd = resultado[0] + quant
        cursor.execute('''
            UPDATE produtos
            SET Quantidade = ?, Preco_Custo = ?, Preco_Venda = ?, Categoria = ?
            WHERE Nome = ?
        ''', (nova_qtd, preco_un, venda_un, categoria, nome))
    else:
        cursor.execute('''
            INSERT INTO produtos (Nome, Quantidade, Preco_Custo, Preco_Venda, Categoria)
            VALUES (?,?,?,?,?)
        ''', (nome, quant, preco_un, venda_un, categoria))
        
    conn.commit()
    conn.close()

# Stock atual vs Dados da última fatura/lote
def visualizar_stock():
    conn = sqlite3.connect('Stock.db')
    query = '''
        SELECT 
            p.Nome, 
            p.Quantidade, 
            p.Preco_Custo, 
            p.Preco_Venda, 
            p.Categoria,
            f.numero_fatura AS [Nº Fatura],
            f.lote AS [Lote],
            f.validade AS [Validade]
        FROM produtos p
        LEFT JOIN faturas f ON p.Nome = f.nome_produto
        WHERE f.id = (SELECT MAX(id) FROM faturas WHERE nome_produto = p.Nome) OR f.id IS NULL
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Histórico de saídas
def visualizar_movimentos():
    conn = sqlite3.connect('Stock.db')
    query = '''
        SELECT
            data_movimento AS [Data],
            nome_produto AS [Produto],
            quantidade AS [Quantidade],
            tipo_movimento AS [Motivo]
        FROM movimentos
        ORDER BY id DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Histórico de compras
def visualizar_compras():
    conn = sqlite3.connect('Stock.db')
    query = '''
        SELECT
            data_compra AS [Data],
            numero_fatura AS [Nº Fatura],
            fornecedor AS [Fornecedor],
            nome_produto AS [Produto],
            quantidade AS [Quantidade],
            preco_unitario AS [Preço Unit. (€)],
            lote AS [Lote],
            validade AS [Validade]
        FROM faturas
        ORDER BY id DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Eliminar permanentemente um artigo e histórico
def eliminar_produto(nome):
    conn = sqlite3.connect('Stock.db')
    c = conn.cursor()
    c.execute("DELETE FROM produtos WHERE Nome = ?", (nome,))
    c.execute("DELETE FROM faturas WHERE nome_produto = ?", (nome,))
    c.execute("DELETE FROM movimentos WHERE nome_produto = ?", (nome,))
    conn.commit()
    conn.close()

# Saídas de artigos e motivo no histórico de movimentos
def baixar_stock(nome, quantidade_a_tirar, motivo):
    conn = sqlite3.connect('Stock.db')
    c = conn.cursor()
    
    # Reduzir a quantidade no stock ativo
    c.execute("UPDATE produtos SET Quantidade = Quantidade - ? WHERE Nome = ? AND Quantidade >= ?",
            (quantidade_a_tirar, nome, quantidade_a_tirar))
    
    # Registar no histórico de movimentos
    data_hoje = datetime.today().strftime('%d-%m-%Y')
    c.execute('''
        INSERT INTO movimentos (data_movimento, nome_produto, quantidade, tipo_movimento)
        VALUES (?,?,?,?)
    ''', (data_hoje, nome, quantidade_a_tirar, motivo))
    
    conn.commit()
    conn.close()

# In[4]:
# #### INTERFACE - CONFIGURAÇÕES
criar_tabelas()
st.set_page_config(page_title="Gestão de Stock", page_icon="📦", layout="wide")

# Carregar base de dados para o Streamlit
try:
    dados = visualizar_stock()
except:
    dados = pd.DataFrame(columns=["Nome", "Quantidade", "Preco_Custo", "Preco_Venda", "Categoria"])

# In[5]:
# #### BARRA LATERAL
st.sidebar.title("Definições")

# 1: REGISTAR NOVA FATURA / COMPRA
with st.sidebar.expander("📥 Compras (Fatura / Documento)", expanded=False):
    with st.form(key="Nova_compra"):
        n_fatura = st.text_input("Nº da Fatura / Documento")
        fornecedor = st.text_input("Fornecedor")
        data_compra = st.date_input("Data da Compra", datetime.today())
        
        st.markdown("---")
        
        if not dados.empty:
            novo_produto = ["-- Criar Novo Produto --"] + list(dados['Nome'].unique())
            produto_escolhido = st.selectbox("Escolha o Produto:", novo_produto)
            
            if produto_escolhido == "-- Criar Novo Produto --":
                nome_produto = st.text_input("Nome do Novo Produto")
            else:
                nome_produto = produto_escolhido
        else:
            nome_produto = st.text_input("Nome do Produto")

        categoria = st.selectbox("Categoria", ["Uso Técnico", "Revenda", "Acessórios"])
        qtd = st.number_input("Qtd Comprada", min_value=1, step=1)
        custo_un = st.number_input("Custo Unitário (€)", min_value=0.0, step=0.5)
        venda_un = st.number_input("Preço de Venda (€)", min_value=0.0, step=0.5)
        lote = st.text_input("Número do Lote")
        validade = st.date_input("Data de Validade", datetime.today())
        
        submetido = st.form_submit_button(label="Dar Entrada no Stock")

if submetido:
    if n_fatura and fornecedor and nome_produto:
        registar_compra(
            n_fatura, fornecedor, data_compra.strftime('%d-%m-%Y'), 
            nome_produto, qtd, custo_un, venda_un, categoria, lote, validade.strftime('%d-%m-%Y')
        )
        st.sidebar.success(f"Entrada de {nome_produto} registada!")
        st.rerun()
    else:
        st.sidebar.error("Preencher Fatura, Fornecedor e Nome do Produto.")

# 2: REGISTAR SAÍDA COM MOTIVO
with st.sidebar.expander("📤 Saídas (Utilização / Venda)"):
    if not dados.empty:
        prod_uso = st.selectbox("Produto utilizado:", dados['Nome'].unique(), key="uso_prod")
        qtd_uso = st.number_input("Quantidade a retirar:", min_value=1, value=1, key="uso_qtd")
        motivo_uso = st.selectbox("Motivo da Saída:", ["Uso em Cliente", "Venda a Cliente", "Desperdício/Quebra"])
        
        if st.button("Confirmar Saída"):
            # Consulta para validação
            conn = sqlite3.connect('Stock.db')
            c = conn.cursor()
            c.execute("SELECT Quantidade FROM produtos WHERE Nome = ?", (prod_uso,))
            resultado_qtd = c.fetchone()
            conn.close()
            
            if resultado_qtd and resultado_qtd[0] >= qtd_uso:
                baixar_stock(prod_uso, qtd_uso, motivo_uso)
                st.success(f"Saída de {prod_uso} registada com sucesso!")
                st.rerun()
            else:
                qtd_disponivel = resultado_qtd[0] if resultado_qtd else 0
                st.error(f"Erro: Stock insuficiente! Tens apenas {int(qtd_disponivel)} unidades.")
    else:
        st.write("Sem produtos disponíveis.")

# 3: ELIMINAR PERMANENTEMENTE
with st.sidebar.expander("🗑️ Eliminar do Inventário"):
    if not dados.empty:
        produto_a_eliminar = st.selectbox("Produto a apagar:", dados['Nome'].unique(), key="del_prod")   
        if st.button("Eliminar Permanentemente"):
            eliminar_produto(produto_a_eliminar)
            st.error(f"Sucesso: {produto_a_eliminar} removido!")
            st.rerun()
    else:
        st.write("Nada a eliminar.")

# In[6]:
# #### ESTATISTICAS E RESUMO FINANCEIRO
if not dados.empty:
    dados['Quantidade'] = pd.to_numeric(dados['Quantidade'], errors='coerce').fillna(0)
    dados['Preco_Custo'] = pd.to_numeric(dados['Preco_Custo'], errors='coerce').fillna(0)
    dados['Preco_Venda'] = pd.to_numeric(dados['Preco_Venda'], errors='coerce').fillna(0)

    st.subheader("📊 Resumo Financeiro")

    valor_total_custo = (dados['Preco_Custo'] * dados['Quantidade']).sum()
    produtos_para_venda = dados[dados['Preco_Venda'] > 0]
    valor_total_venda = (produtos_para_venda['Preco_Venda'] * produtos_para_venda['Quantidade']).sum()
    
    custo_dos_produtos_vendidos = (produtos_para_venda['Preco_Custo'] * produtos_para_venda['Quantidade']).sum()
    lucro = valor_total_venda - custo_dos_produtos_vendidos
    quantidade_total = dados['Quantidade'].sum()

    # Criação de 3 colunas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Investimento em Stock", f"{valor_total_custo:.2f} €")
    with col2:
        st.metric("Potencial de Venda", f"{valor_total_venda:.2f} €")
    with col3:
        st.metric("Lucro Estimado", f"{lucro:.2f} €")
        st.caption(f"Total de itens: {int(quantidade_total)}")

    st.divider()

# In[7]:
# #### RESULTADOS E VISUALIZAÇÃO DO INVENTÁRIO

st.subheader("📋 Inventário e Gestão de Stock")

if not dados.empty:
    tab_stock, tab_financeiro, tab_detalhes, tab_movimentos, tab_compras = st.tabs([
        "📦 Stock Disponível", 
        "💰 Preços e Margens", 
        "🔍 Lotes e Validades",
        "📋 Histórico de Saídas",
        "📥 Histórico de Compras"
    ])

# --- TAB 1: STOCK DISPONÍVEL ---
    with tab_stock:
        st.markdown("### Stock")
        
        # Função para aplicar cores de alerta visual de stock
        def cor_stock_baixo(row):
            qtd = row.get('Quantidade', 0)
            if qtd < 3:
                return ['background-color: #ffcccc; color: black'] * len(row)
            elif 3 <= qtd <= 5:
                return ['background-color: #ffffcc; color: black'] * len(row)
            return [''] * len(row)

        df_stock = dados[['Nome', 'Quantidade', 'Categoria']]
        
        try:
            estilo_stock = df_stock.style.apply(cor_stock_baixo, axis=1).format({
                "Quantidade": "{:.0f}"
            })
            st.dataframe(estilo_stock, use_container_width=True, hide_index=True)
        except:
            st.dataframe(df_stock, use_container_width=True, hide_index=True)

        st.caption("🔴 Vermelho: Stock Crítico (< 3) | 🟡 Amarelo: Stock Baixo (3-5)")

# --- TAB 2: PREÇOS E MARGENS ---
    with tab_financeiro:
        st.markdown("### Análise de Preços e Lucro")
        dados_fin = dados.copy()
        dados_fin['Margem (€)'] = dados_fin['Preco_Venda'] - dados_fin['Preco_Custo']
        df_financeiro = dados_fin[['Nome', 'Preco_Custo', 'Preco_Venda', 'Margem (€)', 'Categoria']]
        
        try:
            estilo_fin = df_financeiro.style.format({
                "Preco_Custo": "{:.2f} €",
                "Preco_Venda": "{:.2f} €",
                "Margem (€)": "{:.2f} €"
            }, na_rep="-")
            st.dataframe(estilo_fin, use_container_width=True, hide_index=True)
        except:
            st.dataframe(df_financeiro, use_container_width=True, hide_index=True)

# --- TAB 3: LOTES E VALIDADES ---
    with tab_detalhes:
        st.markdown("### Detalhes de Faturas")
        df_detalhes = dados[['Nome', 'Nº Fatura', 'Lote', 'Validade']]
        st.dataframe(df_detalhes, use_container_width=True, hide_index=True)
        st.caption("Informação de faturas e validades associadas à última entrada de cada produto.")

# --- TAB 4: HISTÓRICO DE MOVIMENTOS ---
    with tab_movimentos:
        st.markdown("### Registo de Saídas de Stock")
        
        # AQUI estava o erro: tens de chamar a função das SAÍDAS
        dados_movimentos = visualizar_movimentos()

        if not dados_movimentos.empty:
            st.dataframe(dados_movimentos, use_container_width=True, hide_index=True)
            st.caption("Lista de produtos utilizados / vendidos no salão.")
        else:
            st.info("Ainda não foram registadas saídas de stock.")

# --- TAB 5: HISTÓRICO DE COMPRAS (ENTRADAS) ---
    with tab_compras:
        st.markdown("### Registo de Entradas e Faturas")
        
        # AQUI chamas a função das COMPRAS
        dados_compras = visualizar_compras()

        if not dados_compras.empty:
            st.dataframe(dados_compras, use_container_width=True, hide_index=True)
            st.caption("Lista de todas as faturas e produtos que deram entrada no stock.")
        else:
            st.info("Ainda não foram registadas faturas de compras.")
