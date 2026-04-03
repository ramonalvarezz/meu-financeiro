import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="Finanças Pro", layout="wide", page_icon="💳")

# --- CONEXÃO COM GOOGLE SHEETS ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1O5KTzEw-p45y-8zEmkAIee92jv85GrLSEzFvtdm1wRo/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO PARA CARREGAR DADOS COM CACHE ---
@st.cache_data(ttl=300)  # Mantém os dados em cache por 5 minutos
def carregar_dados_completos():
    try:
        df_l = conn.read(spreadsheet=URL_PLANILHA, worksheet="Lancamentos")
        df_m = conn.read(spreadsheet=URL_PLANILHA, worksheet="Metas")
        df_c = conn.read(spreadsheet=URL_PLANILHA, worksheet="Cartoes")
        
        # Tratamento de Tipagem (Garante que datas e números funcionem)
        for df in [df_l, df_m]:
            if not df.empty and "Data" in df.columns:
                df["Data"] = pd.to_datetime(df["Data"])
        
        if not df_l.empty:
            df_l["Valor"] = pd.to_numeric(df_l["Valor"], errors='coerce').fillna(0)
        
        return df_l, df_m, df_c
    except Exception as e:
        st.error(f"🚨 Erro ao ler abas: {e}")
        st.stop()

df_lancamentos, df_metas, df_cartoes = carregar_dados_completos()

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
            # Cria o novo registro garantindo o formato de data
            novo_dado = pd.DataFrame([{
                "Data": data_lanc.strftime('%Y-%m-%d'), 
                "Tipo": tipo, 
                "Categoria": cat, 
                "Descricao": desc, 
                "Pagamento": pag, 
                "Valor": val
            }])
            
            # Concatena e salva
            df_atualizado = pd.concat([df_lancamentos, novo_dado], ignore_index=True)
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Lancamentos", data=df_atualizado)
            
            st.cache_data.clear() # Limpa o cache para que o novo dado apareça no Dashboard
            st.success("Lançamento registrado com sucesso!")
            st.rerun()

# --- ABA 1: DASHBOARD ---
with aba1:
    if not df_lancamentos.empty:
        # Criar coluna de Mês Referência para o filtro
        df_lancamentos['Mes_Ref'] = df_lancamentos['Data'].dt.strftime('%Y-%m')
        meses_disponiveis = sorted(df_lancamentos['Mes_Ref'].unique(), reverse=True)
        mes_ref = st.selectbox("Selecione o Mês", meses_disponiveis)
        
        df_mes = df_lancamentos[df_lancamentos['Mes_Ref'] == mes_ref]

        # Métricas de Topo
        receitas = df_mes[df_mes['Tipo'] == 'Receita']['Valor'].sum()
        gastos = df_mes[df_mes['Tipo'] != 'Receita']['Valor'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Entradas", f"R$ {receitas:,.2f}")
        m2.metric("Saídas", f"R$ {gastos:,.2f}", delta=f"R$ {gastos:,.2f}", delta_color="inverse")
        m3.metric("Saldo do Mês", f"R$ {receitas - gastos:,.2f}")

        st.divider()

        # Gráficos
        col_esq, col_dir = st.columns(2)

        with col_esq:
            st.subheader("💳 Gastos por Cartão")
            df_gastos_pag = df_mes[df_mes['Tipo'] != 'Receita'].groupby('Pagamento')['Valor'].sum().reset_index()
            if not df_gastos_pag.empty:
                fig_cartao = px.bar(df_gastos_pag, x='Pagamento', y='Valor', text_auto='.2f', 
                                   color='Pagamento', template="plotly_white")
                st.plotly_chart(fig_cartao, use_container_width=True)
            else:
                st.info("Sem gastos registrados neste mês.")

        with col_dir:
            st.subheader("🎯 Planejado vs Realizado")
            # Filtrar metas do mês selecionado
            if not df_metas.empty:
                df_metas['Mes_Ref'] = df_metas['Data'].dt.strftime('%Y-%m')
                metas_mes = df_metas[df_metas['Mes_Ref'] == mes_ref]
                realizado_cat = df_mes[df_mes['Tipo'] != 'Receita'].groupby('Categoria')['Valor'].sum().reset_index()
                
                if not metas_mes.empty:
                    comp = pd.merge(metas_mes, realizado_cat, on='Categoria', how='left').fillna(0)
                    fig_meta = go.Figure()
                    fig_meta.add_trace(go.Bar(name='Planejado', x=comp['Categoria'], y=comp['Planejado'], marker_color='#D3D3D3'))
                    fig_meta.add_trace(go.Bar(name='Realizado', x=comp['Categoria'], y=comp['Valor'], marker_color='#1E90FF'))
                    fig_meta.update_layout(barmode='group', template="plotly_white")
                    st.plotly_chart(fig_meta, use_container_width=True)
                else:
                    st.info("Nenhuma meta cadastrada para este mês.")
            else:
                st.info("Cadastre metas na aba Configurações.")

        # Tabela Detalhada
        st.subheader("📑 Extrato Detalhado")
        st.dataframe(df_mes.drop(columns=['Mes_Ref']).sort_values('Data', ascending=False), use_container_width=True)
    else:
        st.warning("Adicione seu primeiro lançamento para ver o painel!")

# --- ABA 3: CONFIGURAÇÕES E EDIÇÃO ---
with aba3:
    st.subheader("⚙️ Gerenciar Estrutura")
    st.write("Edite os valores abaixo e clique no botão no final da página para salvar.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("1. Seus Cartões/Contas")
        ed_cartoes = st.data_editor(df_cartoes, num_rows="dynamic", key="editor_cartoes", use_container_width=True)
    with col_b:
        st.write("2. Suas Metas por Mês")
        ed_metas = st.data_editor(df_metas, num_rows="dynamic", key="editor_metas", use_container_width=True)
    
    st.divider()
    st.write("3. Histórico de Lançamentos")
    ed_lanc = st.data_editor(df_lancamentos.drop(columns=['Mes_Ref']) if 'Mes_Ref' in df_lancamentos.columns else df_lancamentos, 
                             num_rows="dynamic", key="editor_lancamentos", use_container_width=True)
    
    if st.button("Confirmar e Salvar Todas as Alterações"):
        try:
            # Ao salvar do editor, garantir que datas voltem a ser string para o Sheets
            if "Data" in ed_metas.columns: ed_metas["Data"] = ed_metas["Data"].astype(str)
            if "Data" in ed_lanc.columns: ed_lanc["Data"] = ed_lanc["Data"].astype(str)
            
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Cartoes", data=ed_cartoes)
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Metas", data=ed_metas)
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Lancamentos", data=ed_lanc)
            
            st.cache_data.clear()
            st.success("Planilha atualizada com sucesso!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
