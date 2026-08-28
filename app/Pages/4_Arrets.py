import streamlit as st
import requests
import pandas as pd


st.set_page_config(
    page_title="Arrêts CAP",
    page_icon="⏹️",
    layout="wide"
)


API_URL = "http://127.0.0.1:8000"


@st.cache_data
def get_arrets():

    response = requests.get(
        f"{API_URL}/arrets",
        timeout=60
    )

    response.raise_for_status()

    result = response.json()

    return pd.DataFrame(
        result["data"]
    )


st.title("⏹️ Arrêts de l'unité CAP")

df = get_arrets()


st.metric(
    "Nombre total d'arrêts",
    len(df)
)


if df.empty:

    st.info(
        "Aucun arrêt disponible."
    )

else:

    st.subheader(
        "Tous les arrêts"
    )

    st.dataframe(
        df,
        use_container_width=True,
        height=600
    )