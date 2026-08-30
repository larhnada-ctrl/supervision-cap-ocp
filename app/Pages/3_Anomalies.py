import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import os

st.set_page_config(page_title="Anomalies CAP", layout="wide")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.markdown("## ⚠ Détection des anomalies CAP")

# --- RECUPERATION DES DONNEES ---
@st.cache_data(ttl=60)
def load_anomalies():
    try:
        response = requests.get(f"{API_URL}/anomalies")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"count": 0, "data": []}

payload = load_anomalies()
df = pd.DataFrame(payload.get("data", []))

if df.empty:
    st.info("Aucune anomalie enregistrée dans la base de données.")
else:
    # --- CALCUL DES METRIQUES ---
    nb_evenements = len(df)
    nb_occurrences = df["nombre_occurrences"].sum() if "nombre_occurrences" in df.columns else 0

    # --- LIGNE 1 : KPI ET JAUGE ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Nombre d'événements d'anomalie")
        st.markdown(f"<h1 style='color: #2ca02c; font-size: 80px; text-align: center;'>{nb_evenements}</h1>", unsafe_allow_html=True)
        
    with col2:
        st.markdown("##### Nombre d'occurrences anormales")
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = nb_occurrences,
            number = {'font': {'size': 60, 'color': "#333"}},
            gauge = {
                'axis': {'range': [0, max(200, nb_occurrences + 50)], 'visible': False},
                'bar': {'color': "#2ca02c", 'thickness': 0.8},
                'bgcolor': "#f2f2f2",
            }
        ))
        fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

    # --- LIGNE 2 : BAR CHART ET TABLEAU ---
    col3, col4 = st.columns([1, 1])
    
    with col3:
        st.markdown("##### Événements par criticité")
        crit_counts = df["criticite"].value_counts().reset_index()
        crit_counts.columns = ["Criticité", "Nombre"]
        fig_bar = px.bar(
            crit_counts, x="Criticité", y="Nombre", 
            color_discrete_sequence=["#d23449"] # Rouge similaire à Grafana
        )
        fig_bar.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col4:
        st.markdown("##### Historique")
        # Formatage du dataframe pour correspondre à l'image
        df_display = df[["debut_anomalie", "fin_anomalie", "duree_min", "nombre_occurrences"]].copy()
        df_display.columns = ["Début", "Fin", "Durée (min)", "Occurrences"]
        st.dataframe(df_display, use_container_width=True, height=300)

    # --- LIGNE 3 : DIAGRAMME CIRCULAIRE ---
    col5, col6 = st.columns(2)
    
    with col5:
        st.markdown("##### Événements par type de règle")
        type_counts = df["type_regle"].value_counts().reset_index()
        type_counts.columns = ["Type", "Nombre"]
        fig_pie = px.pie(
            type_counts, names="Type", values="Nombre", 
            hole=0.4, # Pour faire un "Donut" comme sur Grafana
            color="Type",
            color_discrete_map={"Simple": "#d23449", "Croisée": "#2ca02c"}
        )
        fig_pie.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)