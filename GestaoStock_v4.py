from datetime import datetime
import streamlit as st
import pandas as pd
import sqlite3
import io
import plotly.express as px
from supabase import create_client, Client


# INTERFACE
st.set_page_config(
    page_title="Gestão de Stock", 
    page_icon="📦", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Adaptação de visualização para Android
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }
        div.stButton > button {
            width: 100%;
            border-radius: 8px;
            height: 3rem;
            font-weight: bold;
        }
            
        [data-testid="stMetricValue"] {
            font-size: 1.5rem;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
        @media (max-width: 640px) {
            [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }
        }
    </style>
""", unsafe_allow_html=True)

# LIGAÇÃO AO SUPABASE
@st.cache_resource
def init_supabase() -> Client:
    # Procurar as chaves nos Secrets do Streamlit
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client (url, key)

supabase = init_supabase()

# CONFIGURAÇÃO DA BASE DE DADOS
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
        
# DEFINIÇÕES DE MANIPULAÇÃO DA BASE DE DADOS
# Registar nova compra (entrada de stock) / Atualizar inventário
def registar_compra(num_fatura, fornecedor, data_compra, nome, quant, preco_un, venda_un, categoria, lote, validade):
    # 1. Registar fatura na tabela faturas
    fatura_data = {
        "numero_fatura": num_fatura,
        "fornecedor": fornecedor,
        "data_compra": data_compra,
        "nome_produto": nome,
        "quantidade": quant,
        "preco_unitario": preco_un,
        "lote": lote,
        "validade": validade
    }
    supabase.table("faturas").insert(fatura_data).execute()

    # 2. Verificar se o produto já existe em stock
    res = supabase.table("produtos").select("*").eq("nome", nome).execute()
    
    if res.data:
        prod_atual = res.data[0]
        qtd_atual = prod_atual.get("quantidade", 0)
        custo_atual = prod_atual.get("preco_custo") or 0.0

        nova_qtd = qtd_atual + quant

        # Cálculo do custo médio ponderado
        if nova_qtd > 0:
            novo_custo_medio = ((qtd_atual * custo_atual) + (quant * preco_un)) / nova_qtd
        else:
            novo_custo_medio = preco_un

        p_venda_antigo = prod_atual.get("preco_venda", 0.0)
        preco_venda_final = venda_un if venda_un > 0 else p_venda_antigo

        supabase.table("produtos").update({
            "quantidade": nova_qtd,
            "preco_custo": novo_custo_medio,
            "preco_venda": preco_venda_final,
            "categoria": categoria
        }).eq("nome", nome).execute()
    else:
        # Novo produto
        supabase.table("produtos").insert({
            "nome": nome,
            "quantidade": quant,
            "preco_custo": preco_un,
            "preco_venda": venda_un,
            "categoria": categoria
        }).execute()

# Stock atual
def visualizar_stock_geral():
    res = supabase.table("produtos").select("nome, quantidade, preco_custo, preco_venda, categoria").order("nome").execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return pd.DataFrame(columns=['Nome', 'Quantidade', 'Preco_Custo', 'Preco_Venda', 'Categoria'])
    
    df = df.rename(columns={
        'nome': 'Nome',
        'quantidade': 'Quantidade',
        'preco_custo': 'Preco_Custo',
        'preco_venda': 'Preco_Venda',
        'categoria': 'Categoria'
    })
    return df

def converter_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Stock Atual')
    return output.getvalue()

# Lotes e Faturas
def visualizar_lotes():
    # Vai buscar faturas e produtos do Supabase
    res_faturas = supabase.table("faturas").select("*").execute()
    res_produtos = supabase.table("produtos").select("nome, categoria").execute()
    
    df_f = pd.DataFrame(res_faturas.data)
    df_p = pd.DataFrame(res_produtos.data)
    
    if df_f.empty:
        return pd.DataFrame()
    
    if not df_p.empty:
        df_merged = pd.merge(df_f, df_p, left_on="nome_produto", right_on="nome", how="left")
    else:
        df_merged = df_f
        df_merged['categoria'] = '-'

    df_res = pd.DataFrame({
        'Nome': df_merged.get('nome_produto', ''),
        'Nº Fatura': df_merged.get('numero_fatura', ''),
        'Fornecedor': df_merged.get('fornecedor', ''),
        'Quantidade Comprada: Lote': df_merged.get('quantidade', 0),
        'Lote': df_merged.get('lote', ''),
        'Validade': df_merged.get('validade', ''),
        'Categoria': df_merged.get('categoria', '-')
    })
    return df_res

# Histórico de saídas
def visualizar_movimentos():
    res = supabase.table("movimentos").select("data_movimento, nome_produto, quantidade, tipo_movimento").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return pd.DataFrame()
    
    df = df.rename(columns={
        'data_movimento': 'Data',
        'nome_produto': 'Produto',
        'quantidade': 'Quantidade',
        'tipo_movimento': 'Motivo'
    })
    return df

# Histórico de compras
def visualizar_compras():
    res = supabase.table("faturas").select("data_compra, numero_fatura, fornecedor, nome_produto, quantidade, preco_unitario, lote, validade").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return pd.DataFrame()
    
    df = df.rename(columns={
        'data_compra': 'Data',
        'numero_fatura': 'Nº Fatura',
        'fornecedor': 'Fornecedor',
        'nome_produto': 'Produto',
        'quantidade': 'Quantidade',
        'preco_unitario': 'Preço Unit. (€)',
        'lote': 'Lote',
        'validade': 'Validade'
    })
    return df

# Eliminar permanentemente um artigo e histórico
def eliminar_produto(nome):
    supabase.table("produtos").delete().eq("nome", nome).execute()
    supabase.table("faturas").delete().eq("nome_produto", nome).execute()
    supabase.table("movimentos").delete().eq("nome_produto", nome).execute()

# Saídas e motivos no histórico de movimentos
def baixar_stock(nome, quantidade_a_tirar, motivo):
    res = supabase.table("produtos").select("quantidade").eq("nome", nome).execute()
    if res.data:
        qtd_atual = res.data[0]['quantidade']
        nova_qtd = qtd_atual - quantidade_a_tirar
        
        # Reduzir no stock ativo
        supabase.table("produtos").update({"quantidade": nova_qtd}).eq("nome", nome).execute()
        
        # Registar no histórico de movimentos
        data_hoje = datetime.today().strftime('%d-%m-%Y')
        supabase.table("movimentos").insert({
            "data_movimento": data_hoje,
            "nome_produto": nome,
            "quantidade": quantidade_a_tirar,
            "tipo_movimento": motivo
        }).execute()

# --- CARREGAR DADOS ---
dados = visualizar_stock_geral()

# BARRA LATERAL
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

        categoria = st.text_input("Categoria do Produto", placeholder="Ex: Escritório, Limpeza, Ferramentas")
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
            res = supabase.table("produtos").select("quantidade").eq("nome", prod_uso).execute()
            if res.data and res.data[0]['quantidade'] >= qtd_uso:
                baixar_stock(prod_uso, qtd_uso, motivo_uso)
                st.success(f"Saída de {prod_uso} registada com sucesso!")
                st.rerun()
            else:
                qtd_disponivel = res.data[0]['quantidade'] if res.data else 0
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

# ESTATISTICAS E RESUMO FINANCEIRO
if not dados.empty:
    for col in ['Quantidade', 'Preco_Custo', 'Preco_Venda']:
        if col in dados.columns:
            dados[col] = pd.to_numeric(dados[col], errors='coerce').fillna(0)
        else:
            dados[col] = 0.00

    st.subheader("📊 Resumo Financeiro")

    valor_total_custo = (dados['Preco_Custo'] * dados['Quantidade']).sum()
    produtos_para_venda = dados[dados['Preco_Venda'] > 0].copy()
    valor_total_venda = (produtos_para_venda['Preco_Venda'] * produtos_para_venda['Quantidade']).sum()
    
    custo_dos_produtos_vendidos = (produtos_para_venda['Preco_Custo'] * produtos_para_venda['Quantidade']).sum()
    lucro = valor_total_venda - custo_dos_produtos_vendidos
    quantidade_total = dados['Quantidade'].sum()

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Investimento em Stock", f"{valor_total_custo:.2f} €")
    with col2:
        st.metric("Potencial de Venda", f"{valor_total_venda:.2f} €")
    with col3:
        st.metric("Lucro Estimado", f"{lucro:.2f} €")
        st.caption(f"Total de itens: {int(quantidade_total)}")

    st.divider()

# RESULTADOS E VISUALIZAÇÃO DO INVENTÁRIO
st.subheader("📋 Inventário e Gestão de Stock")

if not dados.empty:
    tab_stock, tab_financeiro, tab_detalhes, tab_movimentos, tab_compras, tab_dashboard = st.tabs([
        "📦 Stock Disponível", 
        "💰 Preços e Margens", 
        "🔍 Lotes e Validades",
        "📋 Histórico de Saídas",
        "📥 Histórico de Compras",
        "📊 Dashboard"
    ])

# --- TAB 1: STOCK DISPONÍVEL (POR TIPO DE PRODUTO) ---
    with tab_stock:
        st.subheader("📋 Inventário e Gestão de Stock")
        st.markdown("### Visão Geral de Stock")
        
        # Cruzar com faturas para saber o último fornecedor de cada produto
        res_faturas = supabase.table("faturas").select("nome_produto, fornecedor").execute()
        df_fornecedores = pd.DataFrame(res_faturas.data)

        df_stock_base = dados[['Nome', 'Quantidade', 'Categoria']].copy()

        # Se existirem faturas, junta o fornecedor
        if not df_fornecedores.empty:
            df_fornecedores_unicos = df_fornecedores.drop_duplicates(subset=['nome_produto'], keep='last')
            df_stock_base = pd.merge (
                df_stock_base,
                df_fornecedores_unicos,
                left_on = 'Nome',
                right_on = 'nome_produto',
                how = 'left'
            )
            df_stock_base ['Fornecedor'] = df_stock_base['fornecedor'].fillna('-')
            df_stock_base = df_stock_base.drop(columns=['nome_produto', 'fornecedor'])
        else:
            df_stock_base['Fornecedor'] = '-'

        # Cores
        def cor_stock_baixo(row):
            qtd = row.get('Quantidade', 0)
            if qtd < 3:
                return ['background-color: #ffcccc; color: black'] * len(row)
            elif 3 <= qtd <= 5:
                return ['background-color: #ffffcc; color: black'] * len(row)
            return [''] * len(row)

        # Eliminar categorias vazias e ordenar
        df_stock_base['Categoria'] = df_stock_base['Categoria'].fillna('Tintas').replace('', 'Tintas')
        df_stock_base['Categoria'] = df_stock_base['Categoria'].replace('Geral', 'Tintas')
        categorias = sorted (df_stock_base['Categoria'].unique())

        # Criar uma tabela por categoria
        for cat in categorias:
            st.markdown(f"#### Stock de {cat}")
            
            # Filtra apenas os produtos desta categoria e escolhe as colunas (sem Categoria!)
            df_cat = df_stock_base[df_stock_base['Categoria'] == cat][['Nome', 'Fornecedor', 'Quantidade']].copy()
            
            try:
                estilo_cat = df_cat.style.apply(cor_stock_baixo, axis=1).format({"Quantidade": "{:.0f}"})
                st.dataframe(estilo_cat, use_container_width=True, hide_index=True)
            except:
                st.dataframe(df_cat, use_container_width=True, hide_index=True)
            
            st.markdown("---")

        st.caption("🔴 Vermelho: Stock Crítico (< 3) | 🟡 Amarelo: Stock Baixo (3-5)")
        st.divider()

        # Botão de download
        st.download_button(
            label="📥 Download do Stock Disponível (Excel)",
            data=converter_para_excel(df_stock_base[['Nome', 'Categoria', 'Fornecedor', 'Quantidade']]),
            file_name=f"Stock_Por_Categoria_{datetime.today().strftime('%d.%m.%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_download_stock"
        )




# --- TAB 2: PREÇOS E MARGENS ---
    with tab_financeiro:
        st.markdown("### Análise de Preços e Margens")
        dados_fin = dados.copy()
        dados_fin['Margem (€)'] = dados_fin['Preco_Venda'] - dados_fin['Preco_Custo']
        
        df_financeiro = dados_fin[['Nome', 'Preco_Custo', 'Preco_Venda', 'Margem (€)']]

        linha_total_fin = pd.DataFrame([{
            'Nome': 'Total Geral',
            'Preco_Custo': dados_fin['Preco_Custo'].sum(),
            'Preco_Venda': dados_fin['Preco_Venda'].sum(),
            'Margem (€)': dados_fin['Margem (€)'].sum()
        }])

        df_financeiro_final = pd.concat([df_financeiro, linha_total_fin], ignore_index=True)

        st.dataframe(df_financeiro_final.style.format({
            "Preco_Custo": "€ {:.2f}",
            "Preco_Venda": "€ {:.2f}",
            "Margem (€)": "€ {:.2f}"
        }).apply(lambda x: ['font-weight: bold' if x.Nome == 'Total Geral' else '' for i in x], axis=1), 
        use_container_width=True, hide_index=True)
        
        st.divider()
        st.download_button(
            label="📥 Download de Preços e Margens (Excel)",
            data=converter_para_excel(df_financeiro_final),
            file_name=f"Financeiro_Geral_{datetime.today().strftime('%d.%m.%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_download_fin"
        )

# --- TAB 3: LOTES E VALIDADES ---
    with tab_detalhes:
        st.markdown("### Detalhes de Faturas, Lotes e Validades")
        df_detalhes = visualizar_lotes()
        
        if not df_detalhes.empty:
            st.dataframe(df_detalhes, use_container_width=True, hide_index=True)
            st.caption("Lista detalhada de cada entrada de stock e respetivos lotes/validades.")

            st.divider()
            st.download_button(
                label="📥 Download Detalhado de Lotes (Excel)",
                data=converter_para_excel(df_detalhes),
                file_name=f"Detalhes_Lotes_{datetime.today().strftime('%d.%m.%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_download_detalhes"
            )
        else:
            st.info("Sem registo de lotes disponível.")

# --- TAB 4: HISTÓRICO DE MOVIMENTOS ---
    with tab_movimentos:
        st.markdown("### Registo de Saídas")
        dados_movimentos = visualizar_movimentos()

        if not dados_movimentos.empty:
            st.dataframe(dados_movimentos, use_container_width=True, hide_index=True)
            
            st.divider()
            st.download_button(
                label="📥 Download Histórico de Saídas (Excel)",
                data=converter_para_excel(dados_movimentos),
                file_name=f"Historico_Saidas_{datetime.today().strftime('%d.%m.%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_download_mov"
            )
        else:
            st.info("Ainda não foram registadas saídas de stock.")

# --- TAB 5: HISTÓRICO DE COMPRAS ---
    with tab_compras:
        st.markdown("### Registo de Compras")
        dados_compras = visualizar_compras()

        if not dados_compras.empty:
            total_investido = (pd.to_numeric(dados_compras['Quantidade'], errors='coerce') * pd.to_numeric(dados_compras['Preço Unit. (€)'], errors='coerce')).sum()

            linha_total_compra = pd.DataFrame([{
                'Data': '-', 'Nº Fatura': '-', 'Fornecedor': 'TOTAL INVESTIDO',
                'Produto': '-', 'Quantidade': '-', 'Preço Unit. (€)': total_investido,
                'Lote': '-', 'Validade': '-'
            }])

            df_compras_visual = pd.concat([dados_compras, linha_total_compra], ignore_index=True)
            
            st.dataframe(df_compras_visual.style.format({"Preço Unit. (€)": "€ {:.2f}"}), 
                         use_container_width=True, hide_index=True)

            st.divider()
            st.download_button(
                label="📥 Download Histórico de Compras (Excel)",
                data=converter_para_excel(dados_compras),
                file_name=f"Historico_Compras_{datetime.today().strftime('%d.%m.%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_download_compras"
            )
        else:
            st.info("Ainda não foram registadas faturas de compras.")

# --- TAB 6: DASHBOARD E ANÁLISE VISUAL ---
    with tab_dashboard:
        st.markdown("### 📈 Painel de Análise")
        
        col_graph1, col_graph2 = st.columns(2)

        with col_graph1:
            df_cat = dados.groupby('Categoria').apply(
                lambda x: (x['Preco_Custo'] * x['Quantidade']).sum()
            ).reset_index(name='Valor Total')
            
            fig_pie = px.pie(df_cat, values='Valor Total', names='Categoria', 
                             title="Investimento por Categoria (€)",
                             hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_graph2:
            dados_lucro = dados.copy()
            dados_lucro['Lucro_Total'] = (dados_lucro['Preco_Venda'] - dados_lucro['Preco_Custo']) * dados_lucro['Quantidade']
            top_lucro = dados_lucro.nlargest(5, 'Lucro_Total')
            
            fig_bar = px.bar(top_lucro, x='Nome', y='Lucro_Total',
                             title="Top 5: Produtos mais Lucrativos",
                             labels={'Lucro_Total': 'Lucro Potencial (€)'},
                             color='Lucro_Total', 
                             color_continuous_scale='Viridis')
            st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.info("O inventário está vazio. Adiciona stock para começar.")