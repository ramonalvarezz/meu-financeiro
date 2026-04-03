import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuração inicial
st.set_page_config(page_title="Finanças Pro", layout="wide", page_icon="💰")

# 2. Conexão (Busca a URL direto do secrets.toml)
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Função para carregar dados (com limpeza de cache para atualizações reais)
def carregar_dados():
    try:
        df_l = conn.read(worksheet="Lancamentos", ttl=0)
        df_m = conn.read(worksheet="Metas", ttl=0)
        df_c = conn.read(worksheet="Cartoes", ttl=0)
        return df_l, df_m, df_c
    except Exception as e:
        st.error(f"Erro ao ler planilha: {e}")
        st.stop()

df_l, df_m, df_c = carregar_dados()

# Garantir tipos de dados
if not df_l.empty:
    df_l['Data'] = pd.to_datetime(df_l['Data'])
    df_l['Valor'] = pd.to_numeric(df_l['Valor'])

# --- INTERFACE ---
st.title("💳 Controle Financeiro Inteligente")
aba_dash, aba_novo, aba_conf = st.tabs(["📊 Dashboard", "📝 Novo Lançamento", "⚙️ Configurações"])

# --- ABA: NOVO LANÇAMENTO ---
with aba_novo:
    st.subheader("Registrar Movimentação")
    with st.form("form_novo"):
        c1, c2 = st.columns(2)
        data = c1.date_input("Data")
        tipo = c1.selectbox("Tipo", ["Gasto Variável", "Gasto Fixo", "Receita"])
        cat = c1.selectbox("Categoria", df_m["Categoria"].unique() if not df_m.empty else ["Geral"])
        
        desc = c2.text_input("Descrição")
        pag = c2.selectbox("Forma de Pagamento", df_c["Nome"].unique() if not df_c.empty else ["Dinheiro"])
        val = c2.number_input("Valor (R$)", min_value=0.0, step=0.01)
        
        if st.form_submit_button("Salvar na Planilha"):
            novo_item = pd.DataFrame([{
                "Data": data.strftime("%Y-%m-%d"),
                "Tipo": tipo,
                "Categoria": cat,
                "Descricao": desc,
                "Pagamento": pag,
                "Valor": val
            }])
            df_final = pd.concat([df_l, novo_item], ignore_index=True)
            conn.update(worksheet="Lancamentos", data=df_final)
            st.success("Lançamento salvo com sucesso!")
            st.rerun()

# --- ABA: DASHBOARD ---
with aba_dash:
    if not df_l.empty:
        df_l['Mes'] = df_l['Data'].dt.strftime('%Y-%m')
        mes_ref = st.selectbox("Selecione o Mês", sorted(df_l['Mes'].unique(), reverse=True))
        
        df_mes = df_l[df_l['Mes'] == mes_ref]
        
        # Métricas
        rec = df_mes[df_mes['Tipo'] == 'Receita']['Valor'].sum()
        gas = df_mes[df_mes['Tipo'] != 'Receita']['Valor'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Receitas", f"R$ {rec:,.2f}")
        m2.metric("Despesas", f"R$ {gas:,.2f}", delta_color="inverse")
        m3.metric("Saldo", f"R$ {rec - gas:,.2f}")
        
        st.divider()
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            fig_pizza = px.pie(df_mes[df_mes['Tipo'] != 'Receita'], values='Valor', names='Categoria', title="Gastos por Categoria")
            st.plotly_chart(fig_pizza, use_container_width=True)
            
        with col_graf2:
            st.write("### Detalhes do Mês")
            st.dataframe(df_mes[['Data', 'Descricao', 'Valor', 'Pagamento']], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum dado cadastrado ainda.")

# --- ABA: CONFIGURAÇÕES ---
with aba_conf:
    st.subheader("Gerenciar Categorias e Cartões")
    st.info("Edite as tabelas abaixo e clique em 'Salvar Configurações'")
    
    col_ed1, col_ed2 = st.columns(2)
    with col_ed1:
        ed_cartoes = st.data_editor(df_c, num_rows="dynamic", key="ed_c", use_container_width=True)
    with col_ed2:
        ed_metas = st.data_editor(df_m, num_rows="dynamic", key="ed_m", use_container_width=True)
        
    if st.button("Salvar Configurações"):
        conn.update(worksheet="Cartoes", data=ed_cartoes)
        conn.update(worksheet="Metas", data=ed_metas)
        st.success("Configurações atualizadas!")
        st.rerun()
