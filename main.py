import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="Finanças Pro", layout="wide", page_icon="💳")

# --- CONEXÃO COM GOOGLE SHEETS ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1O5KTzEw-p45y-8zEmkAIee92jv85GrLSEzFvtdm1wRo/edit?gid=0#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CARREGAR DADOS ---
df_lancamentos = conn.read(spreadsheet=URL_PLANILHA, worksheet="Lancamentos")
df_metas = conn.read(spreadsheet=URL_PLANILHA, worksheet="Metas")
df_cartoes = conn.read(spreadsheet=URL_PLANILHA, worksheet="Cartoes")

# Listas auxiliares para os menus
lista_cartoes = df_cartoes["Nome"].tolist() if not df_cartoes.empty else ["Dinheiro", "Pix"]
lista_categorias = df_metas["Categoria"].unique().tolist() if not df_metas.empty else ["Geral"]

st.title("💳 Gestão Financeira Inteligente")

# Abas de Navegação
aba1, aba2, aba3 = st.tabs(["📊 Visão Mensal", "📝 Novo Lançamento", "⚙️ Configurações"])

# --- ABA 2: REGISTRO ---
with aba2:
    st.subheader("Registrar Movimentação")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_lanc = st.date_input("Data do Gasto")
            tipo = st.selectbox("Tipo", ["Gasto Variável", "Gasto Fixo", "Receita"])
            cat = st.selectbox("Categoria", lista_categorias)
        with col2:
            desc = st.text_input("Descrição (Ex: Almoço)")
            pag = st.selectbox("Forma de Pagamento / Cartão", lista_cartoes)
            val = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
        
        if st.form_submit_button("Salvar na Planilha"):
            novo_dado = pd.DataFrame([{"Data": str(data_lanc), "Tipo": tipo, "Categoria": cat, 
                                       "Descricao": desc, "Pagamento": pag, "Valor": val}])
            df_atualizado = pd.concat([df_lancamentos, novo_dado], ignore_index=True)
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Lancamentos", data=df_atualizado)
            st.success("Lançamento registrado com sucesso!")
            st.rerun()

# --- ABA 1: DASHBOARD ---
with aba1:
    if not df_lancamentos.empty:
        df_lancamentos['Data'] = pd.to_datetime(df_lancamentos['Data'])
        meses_disponiveis = df_lancamentos['Data'].dt.strftime('%Y-%m').unique()
        mes_ref = st.selectbox("Selecione o Mês", meses_disponiveis)
        
        df_mes = df_lancamentos[df_lancamentos['Data'].dt.strftime('%Y-%m') == mes_ref]

        # Métricas de Topo
        receitas = df_mes[df_mes['Tipo'] == 'Receita']['Valor'].sum()
        gastos = df_mes[df_mes['Tipo'] != 'Receita']['Valor'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Entradas", f"R$ {receitas:,.2f}")
        m2.metric("Saídas", f"R$ {gastos:,.2f}", delta_color="inverse")
        m3.metric("Saldo do Mês", f"R$ {receitas - gastos:,.2f}")

        st.divider()

        # Gráficos
        col_esq, col_dir = st.columns(2)

        with col_esq:
            st.subheader("💳 Gastos por Cartão")
            df_gastos_pag = df_mes[df_mes['Tipo'] != 'Receita'].groupby('Pagamento')['Valor'].sum().reset_index()
            fig_cartao = px.bar(df_gastos_pag, x='Pagamento', y='Valor', text_auto='.2f', color='Pagamento')
            st.plotly_chart(fig_cartao, use_container_width=True)

        with col_dir:
            st.subheader("🎯 Planejado vs Realizado")
            df_metas['Data'] = pd.to_datetime(df_metas['Data'])
            metas_mes = df_metas[df_metas['Data'].dt.strftime('%Y-%m') == mes_ref]
            realizado_cat = df_mes[df_mes['Tipo'] != 'Receita'].groupby('Categoria')['Valor'].sum().reset_index()
            
            if not metas_mes.empty:
                comp = pd.merge(metas_mes, realizado_cat, on='Categoria', how='left').fillna(0)
                fig_meta = go.Figure()
                fig_meta.add_trace(go.Bar(name='Planejado', x=comp['Categoria'], y=comp['Planejado'], marker_color='lightgray'))
                fig_meta.add_trace(go.Bar(name='Realizado', x=comp['Categoria'], y=comp['Valor'], marker_color='royalblue'))
                st.plotly_chart(fig_meta, use_container_width=True)
            else:
                st.info("Cadastre metas para este mês na aba Configurações.")

        # Tabela Detalhada
        st.subheader("📑 Extrato Detalhado")
        st.dataframe(df_mes.sort_values('Data', ascending=False), use_container_width=True)
    else:
        st.warning("Adicione seu primeiro lançamento para ver o painel!")

# --- ABA 3: CONFIGURAÇÕES E EDIÇÃO ---
with aba3:
    st.subheader("⚙️ Gerenciar Estrutura")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("1. Seus Cartões/Contas")
        ed_cartoes = st.data_editor(df_cartoes, num_rows="dynamic")
    with col_b:
        st.write("2. Suas Metas por Mês")
        ed_metas = st.data_editor(df_metas, num_rows="dynamic")
    
    st.divider()
    st.write("3. Histórico de Lançamentos")
    ed_lanc = st.data_editor(df_lancamentos, num_rows="dynamic")
    
    if st.button("Salvar Todas as Alterações"):
        conn.update(spreadsheet=https:URL_PLANILHA, worksheet="Cartoes", data=ed_cartoes)
        conn.update(spreadsheet=URL_PLANILHA, worksheet="Metas", data=ed_metas)
        conn.update(spreadsheet=URL_PLANILHA, worksheet="Lancamentos", data=ed_lanc)
        st.success("Planilha atualizada!")
        st.rerun()
