import streamlit as st
import pandas as pd
from scipy import stats
import os

# --- Configurações Iniciais ---
st.set_page_config(page_title="Efetividade de Mosaicos", layout="wide")

# --- Nomes dos Arquivos Excel ---
FILE_EFETIVIDADE_XLSX = "Efetividade.xlsx"
FILE_RECOMENDA_XLSX = "Recomenda.xlsx"
FILE_DB = "respostas_mosaicos.csv"

# --- Mapeamento de Palavras-Chave para encontrar as abas ---
# O sistema vai procurar abas que contenham esses textos (ex: 'Govern' acha 'GOVERNANÇA' ou 'Recomendações Governança')
SCOPE_KEYWORDS = {
    "GOVERNANÇA": "govern",
    "GESTÃO": "gest",
    "SOCIODIVERSIDADE": "socio",
    "BIODIVERSIDADE": "bio"
}

# --- Funções de Carregamento Inteligente ---
def find_sheet_by_keyword(excel_file, keyword):
    """Procura uma aba no Excel que contenha a palavra-chave."""
    try:
        xls = pd.ExcelFile(excel_file)
        for sheet in xls.sheet_names:
            if keyword.lower() in sheet.lower():
                return sheet
    except Exception as e:
        return None
    return None

@st.cache_data
def load_indicators_from_excel():
    """Lê todas as abas relevantes do arquivo de Efetividade."""
    if not os.path.exists(FILE_EFETIVIDADE_XLSX):
        return pd.DataFrame(), f"Arquivo não encontrado: {FILE_EFETIVIDADE_XLSX}"

    dfs = []
    error_msg = ""
    
    for scope, keyword in SCOPE_KEYWORDS.items():
        sheet_name = find_sheet_by_keyword(FILE_EFETIVIDADE_XLSX, keyword)
        if sheet_name:
            try:
                df = pd.read_excel(FILE_EFETIVIDADE_XLSX, sheet_name=sheet_name)
                # Garante que a coluna Âmbito está correta/uniforme
                df['Âmbito'] = scope 
                df.columns = df.columns.str.strip()
                dfs.append(df)
            except Exception as e:
                error_msg += f"Erro ao ler aba {sheet_name}: {e} | "
        else:
            # Se não achar a aba, tenta procurar CSVs soltos como fallback (plano B)
            csv_name = f"{FILE_EFETIVIDADE_XLSX} - {scope}.csv"
            if os.path.exists(csv_name):
                try:
                    df = pd.read_csv(csv_name)
                    df['Âmbito'] = scope
                    dfs.append(df)
                except:
                    pass

    if dfs:
        return pd.concat(dfs, ignore_index=True), error_msg
    return pd.DataFrame(), "Nenhuma aba ou arquivo correspondente encontrado."

@st.cache_data
def load_recommendations_from_excel():
    """Lê todas as abas relevantes do arquivo de Recomendações."""
    if not os.path.exists(FILE_RECOMENDA_XLSX):
        return pd.DataFrame()

    dfs = []
    for scope, keyword in SCOPE_KEYWORDS.items():
        sheet_name = find_sheet_by_keyword(FILE_RECOMENDA_XLSX, keyword)
        if sheet_name:
            try:
                # header=1 pois a linha 0 costuma ser título nas planilhas de recomendação
                df = pd.read_excel(FILE_RECOMENDA_XLSX, sheet_name=sheet_name, header=1)
                
                # Limpeza básica das colunas
                if len(df.columns) >= 2:
                    df = df.iloc[:, :2]
                    df.columns = ["Problema", "Sugestão"]
                    df["Âmbito"] = scope
                    dfs.append(df)
            except Exception as e:
                st.error(f"Erro ao ler recomendações {scope}: {e}")
    
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

def save_response(data):
    df_new = pd.DataFrame([data])
    if not os.path.exists(FILE_DB):
        df_new.to_csv(FILE_DB, index=False)
    else:
        df_new.to_csv(FILE_DB, mode='a', header=False, index=False)

def load_responses():
    if os.path.exists(FILE_DB):
        return pd.read_csv(FILE_DB)
    return pd.DataFrame()

# --- Interface Principal ---
st.title("🧩 Análise de Efetividade de Mosaicos de Áreas Protegidas")
st.markdown("---")

menu = st.sidebar.radio("Navegação", ["Coleta de Dados", "Painel de Análise e Relatórios"])

# Carregamento dos dados
df_indicators, error_log = load_indicators_from_excel()
df_recomenda = load_recommendations_from_excel()

if df_indicators.empty:
    st.error("❌ Não foi possível carregar os indicadores.")
    st.warning(f"Certifique-se de que o arquivo **{FILE_EFETIVIDADE_XLSX}** está na mesma pasta do script.")
    if error_log:
        st.caption(f"Detalhes técnicos: {error_log}")
    st.stop()

# ==============================================================================
# MÓDULO 1: COLETA
# ==============================================================================
if menu == "Coleta de Dados":
    st.header("📝 Inserção de Dados")
    st.info("Preencha os dados abaixo para contribuir com a análise do Mosaico.")

    with st.form("form_coleta"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome Completo")
            contato = st.text_input("Email ou Telefone")
        with col2:
            mosaico = st.text_input("Qual Mosaico você representa?")

        st.markdown("### Avaliação")
        st.caption("0: Sem efetividade | 1: Pouco | 2: Média | 3: Alta | NS: Não Sei")

        answers = {}
        scopes = df_indicators['Âmbito'].unique()
        
        for scope in scopes:
            with st.expander(f"Âmbito: {scope}", expanded=False):
                # Garante ordem correta se possível
                scope_data = df_indicators[df_indicators['Âmbito'] == scope]
                principles = scope_data['Princípio'].unique()
                
                for principle in principles:
                    st.markdown(f"**{principle}**")
                    principle_data = scope_data[scope_data['Princípio'] == principle]
                    criterions = principle_data['Critério'].unique()
                    
                    for criterion in criterions:
                        st.markdown(f"_{criterion}_")
                        criterion_data = principle_data[principle_data['Critério'] == criterion]
                        
                        for idx, row in criterion_data.iterrows():
                            indicador_txt = row['Indicador']
                            key = f"{scope}_{idx}"
                            val = st.radio(
                                label=indicador_txt,
                                options=["0", "1", "2", "3", "NS"],
                                index=4,
                                horizontal=True,
                                key=key
                            )
                            answers[indicador_txt] = val
                        st.divider()

        submitted = st.form_submit_button("Enviar Respostas")
        
        if submitted:
            if not nome or not mosaico:
                st.warning("Preencha Nome e Mosaico.")
            else:
                data_to_save = {
                    "Nome": nome, 
                    "Contato": contato, 
                    "Mosaico": mosaico, 
                    "Timestamp": pd.Timestamp.now()
                }
                data_to_save.update(answers)
                save_response(data_to_save)
                st.success("Respostas salvas com sucesso!")

# ==============================================================================
# MÓDULO 2: PAINEL
# ==============================================================================
elif menu == "Painel de Análise e Relatórios":
    st.header("📊 Painel de Resultados")
    
    df_resp = load_responses()
    
    if df_resp.empty:
        st.info("Nenhuma resposta coletada ainda.")
    else:
        mosaicos = df_resp['Mosaico'].unique()
        sel_mosaico = st.selectbox("Selecione o Mosaico:", mosaicos)
        
        df_filtered = df_resp[df_resp['Mosaico'] == sel_mosaico].copy()
        
        # Limpeza e conversão numérica
        meta_cols = ["Nome", "Contato", "Mosaico", "Timestamp"]
        q_cols = [c for c in df_filtered.columns if c not in meta_cols]
        
        df_num = df_filtered.copy()
        for col in q_cols:
            df_num[col] = df_num[col].replace("NS", None)
            df_num[col] = pd.to_numeric(df_num[col], errors='coerce')
        
        # Merge com indicadores
        df_long = df_num.melt(id_vars=meta_cols, value_vars=q_cols, var_name="Indicador", value_name="Nota")
        df_long = df_long.dropna(subset=["Nota"])
        df_merged = pd.merge(df_long, df_indicators, on="Indicador", how="left")
        
        tipo_relatorio = st.radio("Tipo de Relatório:", [
            "1) Efetividade Geral (T-Student)",
            "2) Respostas Individuais",
            "3) Estatísticas por Indicador",
            "4) Recomendações"
        ])
        
        st.divider()
        
        if "1)" in tipo_relatorio:
            st.subheader("Efetividade Geral por Âmbito")
            results = []
            for scope in df_indicators['Âmbito'].unique():
                scope_data = df_merged[df_merged['Âmbito'] == scope]
                if scope_data.empty: continue
                
                # Média por usuário para garantir independência no T-Test
                user_means = scope_data.groupby("Nome")['Nota'].mean()
                sample = user_means.values
                n = len(sample)
                mean_val = sample.mean() if n > 0 else 0
                
                if n > 1:
                    # Teste T Unicaudal (Alternative='greater' testa se media > popmean)
                    # Queremos saber se é >= 2. O teste verifica "maior que".
                    # Se p < 0.05, rejeitamos H0 (que é < 2), logo é >= 2 com confiança.
                    t, p = stats.ttest_1samp(sample, 2.0, alternative='greater')
                else:
                    p = 1.0
                
                status = "🔴 Baixa"
                if mean_val >= 2.0 and p < 0.05:
                    status = "🟢 Efetivo"
                elif mean_val >= 2.0:
                    status = "🟡 Incerto (N baixo)"
                
                results.append({
                    "Âmbito": scope,
                    "Média": round(mean_val, 2),
                    "N Respondentes": n,
                    "P-valor": round(p, 4),
                    "Status": status
                })
            st.dataframe(pd.DataFrame(results))
            
        elif "2)" in tipo_relatorio:
            st.dataframe(df_filtered)
            
        elif "3)" in tipo_relatorio:
            st.write(df_merged.groupby(['Âmbito', 'Indicador'])['Nota'].describe()[['count', 'mean', 'std']])
            
        elif "4)" in tipo_relatorio:
            st.subheader("Recomendações para Âmbitos com Baixa Efetividade")
            medias_ambito = df_merged.groupby("Âmbito")['Nota'].mean()
            
            for scope, nota in medias_ambito.items():
                if nota < 2.0:
                    st.error(f"🚨 {scope} (Média: {nota:.2f})")
                    recs = df_recomenda[df_recomenda['Âmbito'] == scope]
                    if not recs.empty:
                        for _, row in recs.iterrows():
                            with st.expander(row.get('Problema', 'Problema Geral')):
                                st.write(row.get('Sugestão', ''))
                    else:
                        st.info("Sem recomendações específicas cadastradas.")