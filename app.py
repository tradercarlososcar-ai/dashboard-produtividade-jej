import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="J&J Dash", page_icon="🚧", layout="wide")

# 2. CREDENCIAIS DO BANCO DE DADOS
SUPABASE_URL = "https://tmtumapreafsfuuyfjiv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MDUxNjU1MSwiZXhwIjoyMDk2MDkyNTUxfQ.wHOR-Iye1iy01EoQrtY3CdnbxnUfDGzoYKhzbNL36PE"

@st.cache_resource
def iniciar_conexao():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = iniciar_conexao()

# 3. INTERFACE GRÁFICA
st.title("🚧 Painel de Produtividade - J&J Perfurações")
st.markdown("Visão de Gestão: Distribuição de Metragem por Equipe, Máquina e Obra")
st.markdown("---")

# 4. BUSCA E CRUZAMENTO DE DADOS
try:
    req_fato = supabase.table('fato_producao').select('*').execute()
    req_func = supabase.table('dim_funcionarios').select('id_funcionario, nome_completo').execute()
    req_maq = supabase.table('dim_maquinas').select('id_maquina, modelo').execute()

    dados_fato = req_fato.data
    dados_func = req_func.data
    dados_maq = req_maq.data
except Exception as e:
    st.error(f"Erro ao buscar dados: {e}")
    dados_fato = []

if dados_fato:
    df_fato = pd.DataFrame(dados_fato)
    
    # 5. INTELIGÊNCIA TEMPORAL
    df_fato['data_registro'] = pd.to_datetime(df_fato['created_at'])
    if 'data_obra' in df_fato.columns:
        df_fato['data_exibicao'] = pd.to_datetime(df_fato['data_obra'])
    else:
        df_fato['data_exibicao'] = df_fato['data_registro']
        
    df_fato['Ano'] = df_fato['data_exibicao'].dt.year
    df_fato['Mês_Num'] = df_fato['data_exibicao'].dt.month
    
    meses_ptbr = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 
                  7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    df_fato['Mês'] = df_fato['Mês_Num'].map(meses_ptbr)

    # 6. BARRA LATERAL
    st.sidebar.header("📅 Filtros")
    anos_disp = ["Todos"] + sorted(df_fato['Ano'].unique().tolist())
    ano_sel = st.sidebar.selectbox("Filtre por Ano", anos_disp)
    meses_disp_num = df_fato[df_fato['Ano'] == ano_sel]['Mês_Num'].unique().tolist() if ano_sel != "Todos" else df_fato['Mês_Num'].unique().tolist()
    meses_disp = ["Todos"] + [meses_ptbr[m] for m in sorted(meses_disp_num)]
    mes_sel = st.sidebar.selectbox("Filtre por Mês", meses_disp)

    # 7. FILTRAGEM
    df_f = df_fato.copy()
    if ano_sel != "Todos": df_f = df_f[df_f['Ano'] == ano_sel]
    if mes_sel != "Todos": df_f = df_f[df_f['Mês'] == mes_sel]

    # 8. MOTOR DE CÁLCULO
    map_func = {f['id_funcionario']: f['nome_completo'] for f in dados_func}
    map_maq = {m['id_maquina']: m['modelo'] for m in dados_maq}
    prod_equipe, prod_maq, prod_obra = {}, {}, {}

    for _, linha in df_f.iterrows():
        mts = float(linha.get('producao_metros', 0) or 0)
        obra = linha.get('nome_obra', 'Obra não especificada')
        prod_obra[obra] = prod_obra.get(obra, 0) + mts
        
        for key in ['id_operador', 'id_navegador']:
            if linha.get(key) in map_func:
                nome = map_func[linha[key]]
                prod_equipe[nome] = prod_equipe.get(nome, 0) + mts
        for aux_id in (linha.get('ids_auxiliares') or []):
            if aux_id in map_func:
                prod_equipe[map_func[aux_id]] = prod_equipe.get(map_func[aux_id], 0) + mts
        if linha.get('id_maquina') in map_maq:
            prod_maq[map_maq[linha['id_maquina']]] = prod_maq.get(map_maq[linha['id_maquina']], 0) + mts

    # 9. EXIBIÇÃO GRÁFICA (Colunas Padronizadas)
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Ranking de Equipe")
        df_eq = pd.DataFrame(list(prod_equipe.items()), columns=['Funcionário', 'Metros']).sort_values('Metros', ascending=False)
        grafico_eq = alt.Chart(df_eq).mark_bar(color='#1f77b4').encode(x='Metros:Q', y=alt.Y('Funcionário:N', sort='-x')).properties(height=300)
        st.altair_chart(grafico_eq, use_container_width=True)
        st.markdown("---")
        st.dataframe(df_eq.rename(columns={'Metros': 'Metros Totais'}), hide_index=True, use_container_width=True)

    with col2:
        st.subheader("🚜 Ranking de Máquina")
        df_mq = pd.DataFrame(list(prod_maq.items()), columns=['Máquina', 'Metros']).sort_values('Metros', ascending=False)
        grafico_mq = alt.Chart(df_mq).mark_bar(color='#ff7f0e').encode(x='Metros:Q', y=alt.Y('Máquina:N', sort='-x')).properties(height=300)
        st.altair_chart(grafico_mq, use_container_width=True)
        st.markdown("---")
        st.dataframe(df_mq.rename(columns={'Metros': 'Metros Totais'}), hide_index=True, use_container_width=True)

    # 10. GRÁFICO OBRAS
    st.markdown("---")
    st.subheader("🏢 Produção Consolidada por Obra")
    df_ob = pd.DataFrame(list(prod_obra.items()), columns=['Obra', 'Metros']).sort_values('Metros', ascending=False)
    grafico_ob = alt.Chart(df_ob).mark_bar(color='#2ca02c').encode(x='Metros:Q', y=alt.Y('Obra:N', sort='-x')).properties(height=250)
    st.altair_chart(grafico_ob, use_container_width=True)

    # 11. HISTÓRICO AUDITORIA
    st.markdown("---")
    st.subheader("📋 Histórico de Obras (Auditoria)")
    df_resumo = df_f.sort_values('data_exibicao', ascending=False)[['data_exibicao', 'nome_obra', 'producao_metros']]
    df_resumo['Data'] = df_resumo['data_exibicao'].dt.strftime('%d/%m/%Y')
    st.dataframe(df_resumo[['Data', 'nome_obra', 'producao_metros']].rename(columns={'nome_obra':'Obra', 'producao_metros':'Produção (m)'}), hide_index=True, use_container_width=True)
else:
    st.warning("Nenhum dado encontrado na base.")