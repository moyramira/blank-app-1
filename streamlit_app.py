import streamlit as st
import pandas as pd
import unicodedata
from io import BytesIO

st.set_page_config(page_title="Análise Dental", layout="wide")
st.title("📊 Comparação Fatura x Folha")

def normalize_label(s: str) -> str:
    if pd.isna(s):
        return ""
    s = str(s)
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = s.upper().strip()
    s = " ".join(s.split())  # colapsa espaços
    return s

def read_with_fallback(uploaded_file, sheet, skiprows_first=1):
    # 1ª tentativa: com skiprows
    try:
        df = pd.read_excel(uploaded_file, sheet_name=sheet, skiprows=skiprows_first)
        return df
    except Exception:
        pass
    # 2ª tentativa: sem skiprows
    df = pd.read_excel(uploaded_file, sheet_name=sheet)
    return df

uploaded_file = st.file_uploader("📁 Envie o arquivo Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        # Ler abas com fallback
        fatura_df = read_with_fallback(uploaded_file, "FATURA", skiprows_first=1)
        folha_df = read_with_fallback(uploaded_file, "FOLHA", skiprows_first=0)

        # Exibir colunas lidas (ajuda no diagnóstico)
        st.caption("Colunas FATURA (originais):")
        st.write(list(fatura_df.columns))
        st.caption("Colunas FOLHA (originais):")
        st.write(list(folha_df.columns))

        # Normalizar nomes das colunas
        fatura_df.columns = [normalize_label(c) for c in fatura_df.columns]
        folha_df.columns  = [normalize_label(c) for c in folha_df.columns]

        # Mapas flexíveis para localizar as colunas necessárias
        mapa_fatura = {
            "CPF": ["CPF"],
            "TITULAR": ["TITULAR", "NOME TITULAR", "NOME", "BENEFICIARIO", "BENEFICIÁRIO"],
            "PARTE DO SEGURADO": ["PARTE DO SEGURADO", "PARTE SEGURADO", "VALOR SEGURADO", "VALOR", "COPARTICIPACAO", "COPARTICIPAÇÃO"]
        }
        mapa_folha = {
            "CPF": ["CPF"],
            "NOME FUNCIONARIO": ["NOME FUNCIONARIO", "NOME FUNCIONÁRIO", "NOME", "FUNCIONARIO", "FUNCIONÁRIO"],
            "VALOR TOTAL": ["VALOR TOTAL", "VALOR", "DESCONTO", "DESCONTOS"]
        }

        def resolver_colunas(df, mapa):
            resolved = {}
            cols = list(df.columns)
            for destino, candidatos in mapa.items():
                match = next((c for c in cols if c in candidatos), None)
                resolved[destino] = match
            return resolved

        res_fatura = resolver_colunas(fatura_df, mapa_fatura)
        res_folha  = resolver_colunas(folha_df,  mapa_folha)

        faltando_fatura = [k for k, v in res_fatura.items() if v is None]
        faltando_folha  = [k for k, v in res_folha.items()  if v is None]

        if faltando_fatura:
            st.error(f"❌ A aba 'FATURA' está com colunas ausentes ou incorretas: {faltando_fatura}")
            st.stop()
        if faltando_folha:
            st.error(f"❌ A aba 'FOLHA' está com colunas ausentes ou incorretas: {faltando_folha}")
            st.stop()

        # Renomear para nomes padronizados
        fatura_df = fatura_df.rename(columns={
            res_fatura["CPF"]: "CPF",
            res_fatura["TITULAR"]: "Titular",
            res_fatura["PARTE DO SEGURADO"]: "Valor"
        })
        folha_df = folha_df.rename(columns={
            res_folha["CPF"]: "CPF",
            res_folha["NOME FUNCIONARIO"]: "Nome",
            res_folha["VALOR TOTAL"]: "Valor"
        })

        # Normalizar CPF e Valor
        fatura_df["CPF"] = fatura_df["CPF"].astype(str).str.replace(r"\D", "", regex=True)
        folha_df["CPF"] = folha_df["CPF"].astype(str).str.replace(r"\D", "", regex=True)
        fatura_df["Valor"] = pd.to_numeric(fatura_df["Valor"], errors="coerce")
        folha_df["Valor"] = pd.to_numeric(folha_df["Valor"], errors="coerce")

        # Agrupar
        dinamica_fatura = fatura_df.groupby(["CPF", "Titular"], as_index=False)["Valor"].sum()
        dinamica_folha  = folha_df.groupby(["CPF", "Nome"], as_index=False)["Valor"].sum()

        # Comparar
        comparacao_df = pd.merge(
            dinamica_folha, dinamica_fatura, on="CPF", how="outer", suffixes=("_Folha", "_Fatura")
        )
        comparacao_df["Valor_Folha"]  = comparacao_df["Valor_Folha"].fillna(0)
        comparacao_df["Valor_Fatura"] = comparacao_df["Valor_Fatura"].fillna(0)
        comparacao_df["Diferença"]    = comparacao_df["Valor_Fatura"] - comparacao_df["Valor_Folha"]

        comparacao_df = comparacao_df[["CPF", "Nome", "Titular", "Valor_Fatura", "Valor_Folha", "Diferença"]]
        comparacao_df = comparacao_df[comparacao_df["Diferença"] != 0]

        # Exibir
        st.success("✅ Arquivo processado com sucesso!")
        st.subheader("📌 Dinâmica Fatura")
        st.dataframe(dinamica_fatura, use_container_width=True)
        st.subheader("📌 Dinâmica Folha")
        st.dataframe(dinamica_folha, use_container_width=True)
        st.subheader("📌 Diferenças")
        st.dataframe(comparacao_df, use_container_width=True)

        # Download
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
