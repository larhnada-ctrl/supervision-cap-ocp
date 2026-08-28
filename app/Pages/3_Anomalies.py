import streamlit as st
import requests
import pandas as pd


st.set_page_config(
    page_title="Anomalies CAP",
    page_icon="⚠️",
    layout="wide"
)


API_URL = "http://127.0.0.1:8000"


@st.cache_data
def get_anomalies():

    response = requests.get(
        f"{API_URL}/anomalies",
        timeout=60
    )

    response.raise_for_status()

    result = response.json()

    return pd.DataFrame(
        result["data"]
    )


st.title("⚠️ Anomalies détectées")

df = get_anomalies()


st.metric(
    "Nombre total d'anomalies",
    len(df)
)


if df.empty:

    st.success(
        "Aucune anomalie détectée."
    )

    st.stop()


# ==========================
# FILTRE
# ==========================

if "criticite" in df.columns:

    criticites = st.multiselect(
        "Criticité",
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
# TABLEAU
# ==========================

st.subheader(
    "Toutes les anomalies"
)

st.dataframe(
    df_filtre,
    use_container_width=True,
    height=500
)


# ==========================
# DETAIL
# ==========================

st.subheader(
    "Détail d'une anomalie"
)

index_selectionne = st.selectbox(
    "Choisir une anomalie",
    df_filtre.index
)

anomalie = df_filtre.loc[
    index_selectionne
]

st.json(
    anomalie.to_dict()
)