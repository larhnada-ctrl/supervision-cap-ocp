import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import os

st.set_page_config(page_title="Laboratoire CAP", layout="wide")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.markdown("## 🧪 Laboratoire et qualité")

@st.cache_data(ttl=60)
def load_labo():
    try:
        response = requests.get(f"{API_URL}/laboratoire")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"count": 0, "data": []}

payload = load_labo()
df = pd.DataFrame(payload.get("data", []))

if df.empty:
    st.info("Aucune analyse enregistrée dans la base de données.")
else:
    # CORRECTION ICI : Remplacement de "date" par "timestamp"
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="timestamp")

    # --- LIGNE 1 : COURBES P2O5 et Conductivité ---
    col1, col2 = st.columns(2)
    
    def plot_labo_line(df_filtered, y_col, y_label):
        # CORRECTION ICI : x="timestamp"
        fig = px.line(df_filtered, x="timestamp", y=y_col, markers=True, color_discrete_sequence=["#cc3d55"])
        fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), xaxis_title=None, yaxis_title=y_label)
        return fig

    with col1:
        st.markdown("##### Évolution du taux de P₂O₅")
        df_p2o5 = df[df["parametre"] == "P₂O₅"] if "parametre" in df.columns else pd.DataFrame()
        if not df_p2o5.empty:
            st.plotly_chart(plot_labo_line(df_p2o5, "valeur", "P₂O₅ (%)"), use_container_width=True)

    with col2:
        st.markdown("##### Conductivité des condensats")
        df_cond = df[df["parametre"] == "Conductivité"] if "parametre" in df.columns else pd.DataFrame()
        if not df_cond.empty:
            st.plotly_chart(plot_labo_line(df_cond, "valeur", "Conductivité (µS/cm)"), use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- LIGNE 2 : COURBE pH et JAUGE NON-CONFORMES ---
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("##### Évolution du pH des condensats")
        df_ph = df[df["parametre"] == "pH"] if "parametre" in df.columns else pd.DataFrame()
        if not df_ph.empty:
            st.plotly_chart(plot_labo_line(df_ph, "valeur", "pH"), use_container_width=True)

    with col4:
        st.markdown("##### Nombre d'analyses non conformes")
        # Calcul des non-conformités
        if "conforme" in df.columns:
            nb_non_conformes = len(df[df["conforme"].astype(str).str.lower().isin(["non", "false", "0"])])
        else:
            nb_non_conformes = 0

        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = nb_non_conformes,
            gauge = {
                'axis': {'range': [0, max(10, nb_non_conformes + 2)], 'visible': False},
                'bar': {'color': "#2ca02c" if nb_non_conformes == 0 else "#2ca02c"} # Vert
            }
        ))
        fig_gauge.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_gauge, use_container_width=True)

    # --- LIGNE 3 : TABLEAU HISTORIQUE ---
    st.markdown("##### Historique des analyses non conformes")
    if "conforme" in df.columns:
        df_non_conformes = df[df["conforme"].astype(str).str.lower().isin(["non", "false", "0"])]
        st.dataframe(df_non_conformes, use_container_width=True)
    else:
        st.dataframe(df, use_container_width=True)