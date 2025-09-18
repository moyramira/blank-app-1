import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Análise Dental", layout="wide")
st.title("📊 Comparação Fatura x Folha")

uploaded_file = st.file_uploader("📁 Envie o arquivo Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        # Carregar as abas
        fatura_df = pd.read_excel(uploaded_file, sheet_name="FATURA", skiprows=1)
        folha_df = pd.read_excel(uploaded_file, sheet_name="FOLHA")

        # Verificar colunas essenciais
        colunas_fatura = ["CPF", "TITULAR", "PARTE DO SEGURADO"]
        colunas_folha = ["CPF", "Nome Funcionário", "Valor Total"]

        if not all(col in fatura_df.columns for col in colunas_fatura):
            st.error("❌ A aba 'FATURA' está com colunas ausentes ou incorretas.")
        elif not all(col in folha_df.columns for col in colunas_folha):
            st.error("❌ A aba 'FOLHA' está com colunas ausentes ou incorretas.")
        else:
            # Padronizar nomes
            fatura_df.rename(columns={
                "CPF": "CPF",
                "TITULAR": "Titular",
                "PARTE DO SEGURADO": "Valor"
            }, inplace=True)

            folha_df.rename(columns={
                "CPF": "CPF",
                "Nome Funcionário": "Nome",
                "Valor Total": "Valor"
            }, inplace=True)

            # Dinâmica Fatura
            dinamica_fatura = fatura_df.groupby(["CPF", "Titular"], as_index=False)["Valor"].sum()

            # Dinâmica Folha
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

            # 🔍 Remover registros com diferença zero
            comparacao_df = comparacao_df[comparacao_df["Diferença"] != 0]

            # Exibir resultados
            st.subheader("📌 Dinâmica Fatura")
            st.dataframe(dinamica_fatura)

            st.subheader("📌 Dinâmica Folha")
            st.dataframe(dinamica_folha)

            st.subheader("📌 Diferenças")
            st.dataframe(comparacao_df)

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
