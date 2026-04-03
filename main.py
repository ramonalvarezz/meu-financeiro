import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="Finanças Pro", layout="wide", page_icon="💳")

# --- CONEXÃO COM GOOGLE SHEETS ---
# Agora ele busca a URL automaticamente do arquivo .streamlit/config.toml
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CARREGAR DADOS COM TRATAMENTO DE ERRO ---
@st.cache_data(ttl=300)
def carregar_dados():
    try:
        # Lendo as abas (Certifique-se que os nomes no Sheets são EXATAMENTE esses)
        df_l = conn.read(worksheet="Lancamentos", ttl=0)
        df_m = conn.read(worksheet="Metas", ttl=0)
        df_c = conn.read(worksheet="Cartoes", ttl=0)
        
        # Garante que Datas sejam objetos de data e não texto
        for df in [df_l, df_m]:
            if not df.empty and "Data" in df.columns:
                df["Data"] = pd.to_datetime(df["Data"])
        
        # Garante que Valor seja número
        if not df_l.empty:
            df_l["Valor"] = pd.to_numeric(df_l["Valor"], errors='coerce').fillna(0)
            
        return df_l, df_m, df_c
    except Exception as e:
        st.error(f"🚨 Erro ao acessar as abas: {e}")
        st.info("Dica: Verifique se os nomes 'Lancamentos', 'Metas' e 'Cartoes' estão sem espaços extras na planilha.")
        st.stop()

df_lancamentos, df_metas, df_cartoes = carregar_dados()

# Listas auxiliares
lista_cartoes = df_cartoes["Nome"].tolist() if not df_cartoes.empty else ["Dinheiro", "Pix"]
lista_categorias = df_metas["Categoria"].unique().tolist() if not df_metas.empty else ["Geral"]

st.title("💳 Gestão Financeira Inteligente")

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
            desc = st.text_input("Descrição")
            pag = st.selectbox("Forma de Pagamento", lista_cartoes)
            val = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
        
        if st.form_submit_button("Salvar na Planilha"):
            novo_dado = pd.DataFrame([{
                "Data": data_lanc.strftime('%Y-%m-%d'), 
                "Tipo": tipo, "Categoria": cat, "Descricao": desc, "Pagamento": pag, "Valor": val
            }])
            df_atualizado = pd.concat([df_lancamentos, novo_dado], ignore_index=True)
            conn.update(worksheet="Lancamentos", data=df_atualizado)
            st.cache_data.clear()
            st.success("Lançamento registrado!")
            st.rerun()

# --- ABA 1: DASHBOARD ---
with aba1:
    if not df_lancamentos.empty:
        df_lancamentos['Mes_Ref'] = df_lancamentos['Data'].dt.strftime('%Y-%m')
        meses = sorted(df_lancamentos['Mes_Ref'].unique(), reverse=True)
        mes_ref = st.selectbox("Selecione o Mês", meses)
        
        df_mes = df_lancamentos[df_lancamentos['Mes_Ref'] == mes_ref]
        receitas = df_mes[df_mes['Tipo'] == 'Receita']['Valor'].sum()
        gastos = df_mes[df_mes['Tipo'] != 'Receita']['Valor'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Entradas", f"R$ {receitas:,.2f}")
        m2.metric("Saídas", f"R$ {gastos:,.2f}", delta_color="inverse")
        m3.metric("Saldo", f"R$ {receitas - gastos:,.2f}")

        # Gráfico Simples de Gastos
        if gastos > 0:
            df_pizza = df_mes[df_mes['Tipo'] != 'Receita'].groupby('Categoria')['Valor'].sum().reset_index()
            fig = px.pie(df_pizza, values='Valor', names='Categoria', title="Distribuição de Gastos")
            st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df_mes.drop(columns=['Mes_Ref']), use_container_width=True)
    else:
        st.warning("Adicione dados para ver o painel.")

# --- ABA 3: CONFIGURAÇÕES ---
with aba3:
    st.subheader("Edição de Dados")
    # Editores dinâmicos
    ed_c = st.data_editor(df_cartoes, num_rows="dynamic", key="ed_cartoes")
    ed_m = st.data_editor(df_metas, num_rows="dynamic", key="ed_metas")
    
    if st.button("Salvar Alterações de Configuração"):
        conn.update(worksheet="Cartoes", data=ed_c)
        conn.update(worksheet="Metas", data=ed_m)
        st.cache_data.clear()
        st.success("Configurações atualizadas!")
        st.rerun()
