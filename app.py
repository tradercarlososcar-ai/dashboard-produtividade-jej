import streamlit as st
import pandas as pd
import altair as alt
from supabase import create_client, Client

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="J&J Dash", page_icon="🚧", layout="wide")

# 2. CREDENCIAIS DO BANCO DE DADOS
SUPABASE_URL = "https://tmtumapreafsfuuyfjiv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRtdHVtYXByZWFmc2Z1dXlmaml2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MDUxNjU1MSwiZXhwIjoyMDk2MDkyNTUxfQ.wHOR-Iye1iy01EoQrtY3CdnbxnUfDGzoYKhzbNL36PE"

@st.cache_resource
def iniciar_conexao():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = iniciar_conexao()

# 3. INTERFACE GRÁFICA
st.title("🚧 Painel de Produtividade - J&J Perfurações")
st.markdown("Visão de Gestão: Distribuição de Metragem por Equipe e Equipamento")
st.markdown("---")

# 4. BUSCA E CRUZAMENTO DE DADOS (JOINS LÓGICOS)
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
    df_fato['Ano'] = df_fato['data_registro'].dt.year
    df_fato['Mês_Num'] = df_fato['data_registro'].dt.month
    
    meses_ptbr = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 
                  7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    df_fato['Mês'] = df_fato['Mês_Num'].map(meses_ptbr)

    # 6. BARRA LATERAL (FILTROS)
    st.sidebar.header("📅 Filtros de Período")
    
    anos_disponiveis = ["Todos"] + sorted(df_fato['Ano'].unique().tolist())
    ano_selecionado = st.sidebar.selectbox("Filtre por Ano", anos_disponiveis)

    if ano_selecionado != "Todos":
        meses_disp_num = df_fato[df_fato['Ano'] == ano_selecionado]['Mês_Num'].unique().tolist()
    else:
        meses_disp_num = df_fato['Mês_Num'].unique().tolist()
        
    meses_disponiveis = ["Todos"] + [meses_ptbr[m] for m in sorted(meses_disp_num)]
    mes_selecionado = st.sidebar.selectbox("Filtre por Mês", meses_disponiveis)

    # 7. APLICANDO OS FILTROS
    df_filtrado = df_fato.copy()
    if ano_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Ano'] == ano_selecionado]
    if mes_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Mês'] == mes_selecionado]

    # 8. O MOTOR MATEMÁTICO
    map_func = {f['id_funcionario']: f['nome_completo'] for f in dados_func}
    map_maq = {m['id_maquina']: m['modelo'] for m in dados_maq}

    produtividade_equipe = {}
    produtividade_maquina = {}

    dados_filtrados = df_filtrado.to_dict('records')

    if not dados_filtrados:
        st.info("Nenhum dado de produção encontrado para este período.")
    else:
        for linha in dados_filtrados:
            metros = float(linha.get('producao_metros', 0) or 0)
            
            id_op = linha.get('id_operador')
            id_nav = linha.get('id_navegador')
            ids_aux = linha.get('ids_auxiliares') or []
            id_maq = linha.get('id_maquina')

            if id_op in map_func:
                nome = map_func[id_op]
                produtividade_equipe[nome] = produtividade_equipe.get(nome, 0) + metros
                
            if id_nav in map_func:
                nome = map_func[id_nav]
                produtividade_equipe[nome] = produtividade_equipe.get(nome, 0) + metros

            for id_a in ids_aux:
                if id_a in map_func:
                    nome = map_func[id_a]
                    produtividade_equipe[nome] = produtividade_equipe.get(nome, 0) + metros

            if id_maq in map_maq:
                modelo = map_maq[id_maq]
                produtividade_maquina[modelo] = produtividade_maquina.get(modelo, 0) + metros

        # 9. TRANSFORMAÇÃO VISUAL CORPORATIVA (ALTAIR)
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏆 Ranking de Produção (Equipe)")
            if produtividade_equipe:
                df_equipe = pd.DataFrame(list(produtividade_equipe.items()), columns=['Funcionário', 'Metros']).sort_values(by='Metros', ascending=False)
                
                grafico_eqp = alt.Chart(df_equipe).mark_bar(color='#1f77b4').encode(
                    x=alt.X('Metros:Q', title='Metros Produzidos'),
                    y=alt.Y('Funcionário:N', sort='-x', title=''),
                    tooltip=['Funcionário', 'Metros']
                ).properties(height=350)
                
                st.altair_chart(grafico_eqp, use_container_width=True)
            else:
                st.write("Sem dados de equipe para este período.")

        with col2:
            st.subheader("🚜 Produção por Máquina")
            if produtividade_maquina:
                df_maquina = pd.DataFrame(list(produtividade_maquina.items()), columns=['Máquina', 'Metros']).sort_values(by='Metros', ascending=False)
                
                grafico_maq = alt.Chart(df_maquina).mark_bar(color='#ff7f0e').encode(
                    x=alt.X('Metros:Q', title='Metros Produzidos'),
                    y=alt.Y('Máquina:N', sort='-x', title=''),
                    tooltip=['Máquina', 'Metros']
                ).properties(height=350)
                
                st.altair_chart(grafico_maq, use_container_width=True)
            else:
                st.write("Sem dados de máquina para este período.")

        # 10. TABELA RESUMIDA (HISTÓRICO RECENTE)
        st.markdown("---")
        st.subheader("📋 Histórico de Obras (Auditoria)")
        
        # Filtra as colunas, ordena da mais nova para a mais velha e formata a data
        df_resumo = df_filtrado[['data_registro', 'nome_obra', 'producao_metros']].copy()
        df_resumo = df_resumo.sort_values(by='data_registro', ascending=False)
        df_resumo['Data'] = df_resumo['data_registro'].dt.strftime('%d/%m/%Y %H:%M')
        
        df_resumo_final = df_resumo[['Data', 'nome_obra', 'producao_metros']].rename(columns={
            'nome_obra': 'Obra',
            'producao_metros': 'Produção (m)'
        })
        
        st.dataframe(df_resumo_final, hide_index=True, use_container_width=True)

else:
    st.warning("Nenhum dado encontrado na base.")