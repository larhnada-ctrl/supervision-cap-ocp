import streamlit as st
import requests
import pandas as pd


st.set_page_config(
    page_title="Alarmes CAP",
    page_icon="🚨",
    layout="wide"
)


API_URL = "http://127.0.0.1:8000"


@st.cache_data
def get_alarmes():

    response = requests.get(
        f"{API_URL}/alarmes",
        timeout=60
    )

    response.raise_for_status()

    result = response.json()

    return pd.DataFrame(
        result["data"]
    )


st.title("🚨 Alarmes CAP")

df = get_alarmes()


st.metric(
    "Nombre total d'alarmes",
    len(df)
)


if df.empty:

    st.info(
        "Aucune alarme disponible."
    )

    st.stop()


# ==========================
# FILTRE CRITICITE
# ==========================

if "criticite" in df.columns:

    criticites = st.multiselect(
        "Filtrer par criticité",
        options=df["criticite"].dropna().unique()
    )

    if criticites:

        df_filtre = df[
            df["criticite"].isin(criticites)
        ]

    else:

        df_filtre = df.copy()

else:

    df_filtre = df.copy()


# ==========================
# RESULTAT
# ==========================

st.subheader(
    "Toutes les alarmes"
)

st.dataframe(
    df_filtre,
    use_container_width=True,
    height=600
)