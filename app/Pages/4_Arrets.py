import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import os

st.set_page_config(page_title="Arrêts CAP", layout="wide")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.markdown("## ⏹ Analyse des arrêts CAP")

# --- RECUPERATION DES DONNEES ---
@st.cache_data(ttl=60)
def load_arrets():
    try:
        response = requests.get(f"{API_URL}/arrets")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"count": 0, "data": []}

payload = load_arrets()
df = pd.DataFrame(payload.get("data", []))

if df.empty:
    st.info("Aucun arrêt enregistré dans la base de données.")
else:
    nb_arrets = len(df)

    # --- LIGNE 1 : KPI ET HISTORIQUE ---
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("##### Nombre total d'arrêts")
        # Reproduit le grand 30 vert de Grafana
        st.markdown(f"""
        <div style="display: flex; justify-content: center; align-items: center; height: 300px; border: 1px solid #e5e7eb; border-radius: 8px; background-color: white;">
            <h1 style='color: #2ca02c; font-size: 140px; margin: 0;'>{nb_arrets}</h1>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("##### Historique des arrêts CAP")
        df_display = df[["debut_arret", "fin_arret", "duree_min", "categorie"]].copy()
        # Tri pour afficher les plus récents en premier comme sur l'image
        df_display = df_display.sort_values(by="debut_arret", ascending=False)
        st.dataframe(df_display, use_container_width=True, height=300)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- LIGNE 2 : GRAPHIQUE EN BARRES ---
    st.markdown("##### Durée des arrêts par catégorie")
    
    # Calcul de la durée totale par catégorie
    df_grouped = df.groupby("categorie")["duree_min"].sum().reset_index()
    # Conversion en heures pour correspondre à l'axe Y de l'image ("hours")
    df_grouped["duree_heures"] = df_grouped["duree_min"] / 60
    # Tri décroissant
    df_grouped = df_grouped.sort_values(by="duree_heures", ascending=False)
    
    fig_bar = px.bar(
        df_grouped, 
        x="categorie", 
        y="duree_heures",
        labels={"categorie": "", "duree_heures": "Heures"},
        color_discrete_sequence=["#cc3d55"] # Rouge rosâtre similaire à Grafana
    )
    
    fig_bar.update_layout(
        height=400,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title=None,
        yaxis_title="Durée (hours)",
        bargap=0.1
    )
    st.plotly_chart(fig_bar, use_container_width=True)