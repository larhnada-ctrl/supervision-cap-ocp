import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import os

st.set_page_config(page_title="Alarmes CAP", layout="wide")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.markdown("## 🚨 Supervision des alarmes CAP")

@st.cache_data(ttl=60)
def load_alarmes():
    try:
        response = requests.get(f"{API_URL}/alarmes")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"count": 0, "data": []}

payload = load_alarmes()
df = pd.DataFrame(payload.get("data", []))

if df.empty:
    st.info("Aucune alarme enregistrée dans la base de données.")
else:
    nb_alarmes = len(df)

    # --- LIGNE 1 ---
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("##### Nombre total d'alarmes")
        st.markdown(f"""
        <div style="display: flex; justify-content: center; align-items: center; height: 250px; border: 1px solid #e5e7eb; border-radius: 8px; background-color: white;">
            <h1 style='color: #b91c1c; font-size: 140px; margin: 0;'>{nb_alarmes}</h1>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("##### Répartition des alarmes par criticité")
        if "criticite" in df.columns:
            crit_counts = df["criticite"].value_counts().reset_index()
            crit_counts.columns = ["Criticité", "Nombre"]
            fig_pie = px.pie(
                crit_counts, names="Criticité", values="Nombre", hole=0.0,
                color="Criticité",
                color_discrete_map={"Haute": "#d23449", "Critique": "#2ca02c"} # Couleurs Grafana
            )
            fig_pie.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- LIGNE 2 ---
    col3, col4 = st.columns([1, 1])
    
    with col3:
        st.markdown("##### Historique des alarmes")
        df_display = df[["debut", "fin", "tag", "alarme", "criticite", "acquittee"]].copy() if "debut" in df.columns else df
        st.dataframe(df_display, use_container_width=True, height=400)
        
    with col4:
        # Traitement pour l'acquittement (conversion en "Oui"/"Non" si booléen)
        if "acquittee" in df.columns:
            nb_acquittees = len(df[df["acquittee"].astype(str).str.lower().isin(["oui", "true", "1"])])
            nb_non_acquittees = nb_alarmes - nb_acquittees
            
            st.markdown("##### Alarmes acquittées")
            fig_acq = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = nb_acquittees,
                gauge = {'axis': {'range': [0, nb_alarmes], 'visible': False}, 'bar': {'color': "#2ca02c"}}
            ))
            fig_acq.update_layout(height=180, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig_acq, use_container_width=True)

            st.markdown("##### Alarmes non acquittées")
            fig_non_acq = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = nb_non_acquittees,
                gauge = {'axis': {'range': [0, nb_alarmes], 'visible': False}, 'bar': {'color': "#2ca02c" if nb_non_acquittees == 0 else "#b91c1c"}}
            ))
            fig_non_acq.update_layout(height=180, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig_non_acq, use_container_width=True)