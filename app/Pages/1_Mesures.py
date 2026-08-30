import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import os

st.set_page_config(page_title="Mesures CAP", layout="wide")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.markdown("## 📊 Suivi des mesures CAP")

@st.cache_data(ttl=60)
def load_mesures():
    try:
        response = requests.get(f"{API_URL}/mesures")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"count": 0, "data": []}

payload = load_mesures()
df = pd.DataFrame(payload.get("data", []))

if df.empty:
    st.info("Aucune mesure enregistrée dans la base de données.")
else:
    # S'assurer que le timestamp est au format datetime pour Plotly
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by="timestamp")

    # Liste des paramètres uniques à tracer (basé sur la colonne 'parametre' ou 'tag')
    parametres = df["parametre"].unique() if "parametre" in df.columns else []

    # Affichage en grille (2 colonnes)
    cols = st.columns(2)
    
    for i, param in enumerate(parametres):
        col = cols[i % 2] # Alterne entre la colonne 1 et 2
        df_param = df[df["parametre"] == param]
        
        with col:
            st.markdown(f"##### {param}")
            fig = px.line(
                df_param, 
                x="timestamp", 
                y="valeur",
                color_discrete_sequence=["#cc3d55"] # Rouge Grafana
            )
            fig.update_layout(
                height=250,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis_title=None,
                yaxis_title=None,
                xaxis=dict(showgrid=True, gridcolor='#e5e7eb'),
                yaxis=dict(showgrid=True, gridcolor='#e5e7eb'),
                plot_bgcolor='white'
            )
            st.plotly_chart(fig, use_container_width=True)