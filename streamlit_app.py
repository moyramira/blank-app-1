import streamlit as st
import pandas as pd
from io import BytesIO
import unicodedata

st.set_page_config(page_title="Análise Dental", layout="wide")
st.title("📊 Comparação Fatura x Folha")

# Função para normalizar texto
def normalizar(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().upper()
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII")
    texto = " ".join(texto.split())
    return texto

# Função para mapear colunas por similaridade
def mapear_colunas(colunas, candidatos):
    mapeadas = {}
    for chave, variações in candidatos.items():
        for col in colunas:
            if normalizar(col) in [normalizar(v) for v in variações]:
                mapeadas[chave] = col
                break
    return mapeadas

# Variações aceitas
variacoes_fatura = {
    "CPF": ["CPF"],
    "Titular": ["TITULAR", "BENEFICIARIO", "BENEFICIÁRIO", "NOME"],
    "Valor": ["PARTE DO SEGURADO", "IOF", "VALOR SEGURADO", "VALOR LANÇAMENTO", "VALOR LANCAMENTO", "VALOR COBRADO"]
}

variacoes_folha = {
    "CPF": ["CPF"],
    "Nome": ["NOME FUNCIONARIO", "NOME FUNCIONÁRIO", "FUNCIONARIO", "FUNCIONÁRIO", "NOME"],
    "Valor": ["VALOR TOTAL", "VALOR", "DESCONTO", "DESCONTOS"]
}

uploaded_file = st.file_uploader("📁 Envie o arquivo Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        # Tentar ler FATURA com header=None
        fatura_raw = pd.read_excel(uploaded_file, sheet_name="FATURA", header=None)
        folha_df = pd.read_excel(uploaded_file, sheet_name="FOLHA")

        # Detectar linha de cabeçalho na FATURA
        for i in range(5):
            tentativa = fatura_raw.iloc[i]
            colunas_norm = [normalizar(c) for c in tentativa]
            if any("CPF" in c for c in colunas_norm):
                fatura_df = pd.read_excel(uploaded_file, sheet_name="FATURA", skiprows=i)
                break
        else:
            st.error("❌ Não foi possível detectar o cabeçalho da aba 'FATURA'.")
            st.stop()

        # Normalizar colunas
        fatura_df.columns = [normalizar(c) for c in fatura_df.columns]
        folha_df.columns = [normalizar(c) for c in folha_df.columns]

        # Mapear colunas
        colunas_fatura = mapear_colunas(fatura_df.columns, variacoes_fatura)
        colunas_folha = mapear_colunas(folha_df.columns, variacoes_folha)

        if len(colunas_fatura) < 3:
            st.error("❌ A aba 'FATURA' está com colunas ausentes ou incorretas.")
            st.write("Colunas encontradas:", fatura_df.columns.tolist())
            st.stop()

        if len(colunas_folha) < 3:
            st.error("❌ A aba 'FOLHA' está com colunas ausentes ou incorretas.")
            st.write("Colunas encontradas:", folha_df.columns.tolist())
            st.stop()

        # Renomear colunas
        fatura_df = fatura_df.rename(columns={
            colunas_fatura["CPF"]: "CPF",
            colunas_fatura["Titular"]: "Titular",
            colunas_fatura["Valor"]: "Valor"
        })
        folha_df = folha_df.rename(columns={
            colunas_folha["CPF"]: "CPF",
            colunas_folha["Nome"]: "Nome",
            colunas_folha["Valor"]: "Valor"
        })

        # Limpar CPF e converter valores
        fatura_df["CPF"] = fatura_df["CPF"].astype(str).str.replace(r"\D", "", regex=True)
        folha_df["CPF"] = folha_df["CPF"].astype(str).str.replace(r"\D", "", regex=True)
        fatura_df["Valor"] = pd.to_numeric(fatura_df["Valor"], errors="coerce")
        folha_df["Valor"] = pd.to_numeric(folha_df["Valor"], errors="coerce")

        # Agrupamentos
        dinamica_fatura = fatura_df.groupby(["CPF", "Titular"], as_index=False)["Valor"].sum()
        dinamica_folha = folha_df.groupby(["CPF", "Nome"], as_index=False)["Valor"].sum()

        # Comparação
        comparacao_df = pd.merge(
            dinamica_folha,
            dinamica_fatura,
            on="CPF",
            how="outer",
            suffixes=("_Folha", "_Fatura")
        )
        comparacao_df["Valor_Folha"] = comparacao_df["Valor_Folha"].fillna(0)
        comparacao_df["Valor_Fatura"] = comparacao_df["Valor_Fatura"].fillna(0)
        comparacao_df["Diferença"] = comparacao_df["Valor_Fatura"] - comparacao_df["Valor_Folha"]
        comparacao_df = comparacao_df[["CPF", "Nome", "Titular", "Valor_Fatura", "Valor_Folha", "Diferença"]]
        comparacao_df = comparacao_df[comparacao_df["Diferença"] != 0]

        # Exibir resultados
        st.success("✅ Arquivo processado com sucesso!")
        st.subheader("📌 Dinâmica Fatura")
        st.dataframe(dinamica_fatura, use_container_width=True)
        st.subheader("📌 Dinâmica Folha")
        st.dataframe(dinamica_folha, use_container_width=True)
        st.subheader("📌 Diferenças")
        st.dataframe(comparacao_df, use_container_width=True)

        # Gerar arquivo para download
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            dinamica_fatura.to_excel(writer, sheet_name="dinamica fatura", index=False)
            dinamica_folha.to_excel(writer, sheet_name="dinamica folha", index=False)
            comparacao_df.to_excel(writer, sheet_name="diferenças", index=False)

        st.download_button(
            label="📥 Baixar arquivo analisado",
            data=output.getvalue(),
            file_name="DENTAL_ANALISADO.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {e}")
else:
    st.info("Por favor, envie um arquivo Excel com as abas 'FATURA' e 'FOLHA'.")
