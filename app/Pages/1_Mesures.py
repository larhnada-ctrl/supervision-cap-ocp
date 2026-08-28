import streamlit as st
import requests
import pandas as pd
import plotly.express as px


# ==========================
# CONFIGURATION
# ==========================

st.set_page_config(
    page_title="Mesures CAP",
    page_icon="📈",
    layout="wide"
)

API_URL = "http://127.0.0.1:8000"


# ==========================
# RECUPERATION
# ==========================

@st.cache_data
def get_mesures():

    response = requests.get(
        f"{API_URL}/mesures",
        timeout=60
    )

    response.raise_for_status()

    result = response.json()

    return pd.DataFrame(
        result["data"]
    )


# ==========================
# TITRE
# ==========================

st.title("📈 Mesures de l'unité CAP")

df = get_mesures()


# ==========================
# INFORMATIONS
# ==========================

st.metric(
    "Nombre total de mesures",
    len(df)
)


# ==========================
# VERIFICATION
# ==========================

if df.empty:

    st.warning(
        "Aucune mesure disponible."
    )

    st.stop()


# ==========================
# DATE
# ==========================

if "timestamp" in df.columns:

    df["timestamp"] = pd.to_datetime(
        df["timestamp"]
    )


# ==========================
# CHOIX DES COLONNES
# ==========================

colonnes_numeriques = df.select_dtypes(
    include=["number"]
).columns.tolist()


if len(colonnes_numeriques) == 0:

    st.error(
        "Aucune colonne numérique trouvée."
    )

    st.dataframe(df)

    st.stop()


parametre = st.selectbox(
    "Choisir un paramètre",
    colonnes_numeriques
)


# ==========================
# GRAPHIQUE
# ==========================

if "timestamp" in df.columns:

    fig = px.line(
        df,
        x="timestamp",
        y=parametre,
        title=f"Évolution de {parametre}"
    )

else:

    fig = px.line(
        df,
        y=parametre,
        title=f"Évolution de {parametre}"
    )


st.plotly_chart(
    fig,
    use_container_width=True
)


# ==========================
# TABLEAU COMPLET
# ==========================

st.subheader(
    "Toutes les mesures"
)

st.dataframe(
    df,
    use_container_width=True,
    height=500
)