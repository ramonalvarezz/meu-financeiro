import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="Debug Finanças", layout="wide", page_icon="💳")

# --- CONEXÃO COM GOOGLE SHEETS ---
# Verifique se esta URL termina em /edit ou se é o link de compartilhamento completo
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1O5KTzEw-p45y-8zEmkAIee92jv85GrLSEzFvtdm1wRo/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🔍 Diagnóstico de Conexão")

# --- BLOCO DE TESTE DE ABAS ---
try:
    with st.status("Verificando abas da planilha...", expanded=True) as status:
        st.write("1. Tentando ler aba: **Lancamentos**...")
        df_lancamentos = conn.read(spreadsheet=URL_PLANILHA, worksheet="Lancamentos", ttl=0)
        st.write("✅ Aba 'Lancamentos' lida com sucesso!")

        st.write("2. Tentando ler aba: **Metas**...")
        df_metas = conn.read(spreadsheet=URL_PLANILHA, worksheet="Metas", ttl=0)
        st.write("✅ Aba 'Metas' lida com sucesso!")

        st.write("3. Tentando ler aba: **Cartoes**...")
        df_cartoes = conn.read(spreadsheet=URL_PLANILHA, worksheet="Cartoes", ttl=0)
        st.write("✅ Aba 'Cartoes' lida com sucesso!")
        
        status.update(label="Conexão estabelecida com sucesso!", state="complete", expanded=False)
except Exception as e:
    st.error(f"❌ O erro 400 aconteceu aqui: {e}")
    st.info("""
    **Causas prováveis do Erro 400:**
    1. **Nome da Aba:** Verifique se o nome na planilha é exatamente igual ao do código (maiúsculas, minúsculas e sem espaços extras).
    2. **Planilha Vazia:** A aba precisa ter pelo menos o cabeçalho (a primeira linha preenchida).
    3. **Permissão:** Verifique se o compartilhamento está como 'Qualquer pessoa com o link' e 'Editor'.
    """)
    st.stop()

# --- TRATAMENTO DE DADOS (Após passar no teste) ---
if not df_lancamentos.empty and "Data" in df_lancamentos.columns:
    df_lancamentos["Data"] = pd.to_datetime(df_lancamentos["Data"])
    df_lancamentos["Valor"] = pd.to_numeric(df_lancamentos["Valor"], errors='coerce').fillna(0)

if not df_metas.empty and "Data" in df_metas.columns:
    df_metas["Data"] = pd.to_datetime(df_metas["Data"])

# Listas auxiliares
lista_cartoes = df_cartoes["Nome"].tolist() if not df_cartoes.empty else ["Dinheiro", "Pix"]
lista_categorias = df_metas["Categoria"].unique().tolist() if not df_metas.empty else ["Geral"]

# --- INTERFACE (ABAS) ---
aba1, aba2, aba3 = st.tabs(["📊 Visão Mensal", "📝 Novo Lançamento", "⚙️ Configurações"])

with aba2:
    st.subheader("Registrar Movimentação")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_lanc = st.date_input("Data do Gasto")
            tipo = st.selectbox("Tipo", ["Gasto Variável", "Gasto Fixo", "Receita"])
            cat = st.selectbox("Categoria", lista_categorias)
        with col2:
            desc = st.text_input("Descrição")
            pag = st.selectbox("Forma de Pagamento", lista_cartoes)
            val = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
        
        if st.form_submit_button("Salvar na Planilha"):
            novo_dado = pd.DataFrame([{
                "Data": data_lanc.strftime('%Y-%m-%d'), 
                "Tipo": tipo, "Categoria": cat, "Descricao": desc, "Pagamento": pag, "Valor": val
            }])
            df_atualizado = pd.concat([df_lancamentos, novo_dado], ignore_index=True)
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Lancamentos", data=df_atualizado)
            st.success("Salvo! Recarregue a página.")

with aba1:
    if not df_lancamentos.empty:
        df_lancamentos['Mes_Ref'] = df_lancamentos['Data'].dt.strftime('%Y-%m')
        mes_ref = st.selectbox("Selecione o Mês", sorted(df_lancamentos['Mes_Ref'].unique(), reverse=True))
        df_mes = df_lancamentos[df_lancamentos['Mes_Ref'] == mes_ref]
        
        receitas = df_mes[df_mes['Tipo'] == 'Receita']['Valor'].sum()
        gastos = df_mes[df_mes['Tipo'] != 'Receita']['Valor'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Entradas", f"R$ {receitas:,.2f}")
        m2.metric("Saídas", f"R$ {gastos:,.2f}")
        m3.metric("Saldo", f"R$ {receitas - gastos:,.2f}")
        st.dataframe(df_mes.drop(columns=['Mes_Ref']), use_container_width=True)
    else:
        st.info("Nenhum dado para exibir no Dashboard.")

with aba3:
    st.write("Edição Direta")
    ed_c = st.data_editor(df_cartoes, num_rows="dynamic", key="ed_c")
    ed_m = st.data_editor(df_metas, num_rows="dynamic", key="ed_m")
    
    if st.button("Salvar Configurações"):
        conn.update(spreadsheet=URL_PLANILHA, worksheet="Cartoes", data=ed_c)
        conn.update(spreadsheet=URL_PLANILHA, worksheet="Metas", data=ed_m)
        st.success("Configurações atualizadas!")
