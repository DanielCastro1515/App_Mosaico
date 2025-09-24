import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import ttest_1samp

# Carregar os dados de efetividade e recomendações
efetividade_df = pd.read_excel("Efetividade.xlsx", sheet_name=0, engine="openpyxl")
try:
    recomendacoes_df = pd.read_excel("Recomendações.xlsx", engine="openpyxl")
except Exception:
    recomendacoes_df = pd.DataFrame(columns=["Âmbito", "Recomendação"])

# Função para identificar linhas de indicadores
def is_indicator(row):
    return isinstance(row, str) and row.strip().split(".")[0].isdigit()

# Interface Streamlit
st.title("Análise de Efetividade dos Mosaicos de Áreas Protegidas")

st.markdown("### Entrada de Dados pelos Usuários")
usuarios = [col for col in efetividade_df.columns if "Usuário" in str(col)]
dados_entrada = {}

for idx, row in efetividade_df.iterrows():
    if is_indicator(str(row[0])):
        indicador = str(row[0])
        dados_entrada[indicador] = {}
        for usuario in usuarios:
            nota = st.selectbox(f"{indicador} - {usuario}", options=[0, 1, 2, 3, "NA"], key=f"{indicador}_{usuario}")
            dados_entrada[indicador][usuario] = nota

# Processar os dados
st.markdown("### Cálculo das Médias Hierárquicas")

notas_indicadores = {}
for indicador, respostas in dados_entrada.items():
    valores = [v for v in respostas.values() if v != "NA"]
    if valores:
        notas_indicadores[indicador] = np.mean(valores)
    else:
        notas_indicadores[indicador] = np.nan

# Criar DataFrame com as médias dos indicadores
indicadores_df = pd.DataFrame(list(notas_indicadores.items()), columns=["Indicador", "Média"])
st.dataframe(indicadores_df)

# Agrupar por hierarquia
hierarquia = {}
ambito_atual = principio_atual = criterio_atual = None

for idx, row in efetividade_df.iterrows():
    texto = str(row[0])
    if texto.startswith("Ambito"):
        ambito_atual = texto.replace("Ambito ", "").strip()
        hierarquia[ambito_atual] = {}
    elif texto.startswith("PRINCÍPIO"):
        principio_atual = texto.strip()
        hierarquia[ambito_atual][principio_atual] = {}
    elif texto.startswith("CRITÉRIO"):
        criterio_atual = texto.strip()
        hierarquia[ambito_atual][principio_atual][criterio_atual] = []
    elif is_indicator(texto):
        hierarquia[ambito_atual][principio_atual][criterio_atual].append(texto)

# Calcular médias por critério, princípio e âmbito
media_ambitos = {}
for ambito, principios in hierarquia.items():
    principios_medias = []
    for principio, criterios in principios.items():
        criterios_medias = []
        for criterio, indicadores in criterios.items():
            medias = [notas_indicadores.get(ind, np.nan) for ind in indicadores]
            medias = [m for m in medias if not np.isnan(m)]
            if medias:
                criterios_medias.append(np.mean(medias))
        if criterios_medias:
            principios_medias.append(np.mean(criterios_medias))
    if principios_medias:
        media_ambitos[ambito] = np.mean(principios_medias)

media_ambitos_df = pd.DataFrame(list(media_ambitos.items()), columns=["Âmbito", "Média Efetividade"])
st.markdown("### Média de Efetividade por Âmbito")
st.dataframe(media_ambitos_df)

# Teste T de Student
st.markdown("### Teste T de Student por Âmbito")
teste_t_resultados = []
for ambito, principios in hierarquia.items():
    todas_notas = []
    for principio, criterios in principios.items():
        for criterio, indicadores in criterios.items():
            for ind in indicadores:
                notas = [v for v in dados_entrada[ind].values() if v != "NA"]
                todas_notas.extend(notas)
    if len(todas_notas) >= 2:
        t_stat, p_val = ttest_1samp(todas_notas, popmean=1.5)
        teste_t_resultados.append((ambito, t_stat, p_val, len(todas_notas)))

teste_t_df = pd.DataFrame(teste_t_resultados, columns=["Âmbito", "t-stat", "p-valor", "N respostas"])
st.dataframe(teste_t_df)

# Recomendações
st.markdown("### Recomendações para Âmbitos com Efetividade Baixa")
recomendacoes = []
for ambito, media in media_ambitos.items():
    if media < 1.5:
        recomendacao = recomendacoes_df[recomendacoes_df["Âmbito"] == ambito]["Recomendação"].values
        texto = recomendacao[0] if len(recomendacao) > 0 else "Sem recomendação disponível"
        recomendacoes.append((ambito, media, texto))

if recomendacoes:
    recomendacoes_df_final = pd.DataFrame(recomendacoes, columns=["Âmbito", "Média", "Recomendação"])
    st.dataframe(recomendacoes_df_final)
else:
    st.success("Todos os âmbitos apresentaram efetividade satisfatória (>= 1.5). Nenhuma recomendação necessária.")
