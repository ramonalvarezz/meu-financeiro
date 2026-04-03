import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("Teste de Conexão Direta")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1O5KTzEw-p45y-8zEmkAIee92jv85GrLSEzFvtdm1wRo/edit?usp=sharing"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Teste 1: Tentar ler sem especificar aba (ele lê a primeira)
    st.write("Tentando ler a primeira aba disponível...")
    df_teste = conn.read(spreadsheet=URL_PLANILHA)
    st.success("Consegui ler a primeira aba!")
    st.dataframe(df_teste.head())

    # Teste 2: Tentar ler a aba específica com o nome exato
    st.write("Tentando ler a aba 'Lancamentos'...")
    df_lanc = conn.read(spreadsheet=URL_PLANILHA, worksheet="Lancamentos")
    st.success("Consegui ler a aba Lancamentos!")
    
except Exception as e:
    st.error(f"Erro detalhado: {e}")
    st.info("Se o erro acima mencionar 'API key' ou 'Credentials', o problema é autenticação.")
