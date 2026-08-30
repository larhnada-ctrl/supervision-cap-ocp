import streamlit as st
import requests
import base64
from pathlib import Path
import os

# En local, .env fournit API_URL et les identifiants.
# Sur Streamlit Community Cloud, il n'y a pas de .env :
# load_dotenv ne fait rien et les secrets du tableau de bord
# sont deja presents dans os.environ.
from dotenv import load_dotenv

load_dotenv(override=False)


# ============================================================
# CONFIGURATION DE LA PAGE
# ============================================================

st.set_page_config(
    page_title="CAP Supervision | OCP",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# CHEMINS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ASSETS_DIR = BASE_DIR / "assets"

LOGO_PATH = ASSETS_DIR / "ocp_logo.png"
BACKGROUND_PATH = ASSETS_DIR / "background.jpg"


# ============================================================
# CONFIGURATION API
# ============================================================

# En local, la valeur par defaut suffit. En production, la
# variable API_URL pointe vers le service Render.
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


# ============================================================
# IDENTIFIANTS DE CONNEXION
# ============================================================

# Les identifiants ne doivent jamais figurer dans le code source.
# Ils sont fournis par APP_USER_EMAIL / APP_USER_PASSWORD
# (fichier .env en local, secrets Streamlit en production).
AUTHORIZED_EMAIL = os.getenv(
    "APP_USER_EMAIL",
    "ocp@gmail.com",
)

AUTHORIZED_PASSWORD = os.getenv(
    "APP_USER_PASSWORD",
    "changeme-en-local",
)


# ============================================================
# SESSION UTILISATEUR
# ============================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user_email" not in st.session_state:
    st.session_state.user_email = ""


# ============================================================
# FONCTION IMAGE BASE64
# ============================================================

def get_base64_image(image_path):
    if not image_path.exists():
        return None
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except Exception:
        return None


# ============================================================
# RECUPERATION DES DONNEES API
# ============================================================

def get_api_data(endpoint):
    try:
        response = requests.get(
            f"{API_URL}{endpoint}",
            timeout=15
        )
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "count": result.get("count", 0),
                "data": result.get("data", []),
                "error": None
            }
        return {
            "success": False,
            "count": 0,
            "data": [],
            "error": f"Erreur API {response.status_code}"
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "count": 0,
            "data": [],
            "error": "API non accessible"
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "count": 0,
            "data": [],
            "error": "Temps de réponse dépassé"
        }
    except Exception as error:
        return {
            "success": False,
            "count": 0,
            "data": [],
            "error": str(error)
        }


# ============================================================
# STYLE DE LA PAGE DE CONNEXION
# ============================================================

def apply_login_style():
    background_base64 = get_base64_image(BACKGROUND_PATH)

    if background_base64:
        background_css = f'url("data:image/jpg;base64,{background_base64}")'
    else:
        background_css = """
        linear-gradient(
            135deg,
            #123c2f,
            #1b5e4b
        )
        """

    st.markdown(
f"""<style>
/* ELEMENTS STREAMLIT */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
header {{ visibility: hidden; }}
[data-testid="stSidebar"] {{ display: none; }}

/* ARRIERE-PLAN */
.stApp {{ background: transparent; }}
.stApp::before {{
    content: "";
    position: fixed;
    top: 0; left: 0;
    width: 100vw; height: 100vh;
    background-image: {background_css};
    background-size: cover;
    background-position: center;
    filter: blur(6px);
    transform: scale(1.03);
    z-index: -2;
}}
.stApp::after {{
    content: "";
    position: fixed;
    top: 0; left: 0;
    width: 100vw; height: 100vh;
    background: linear-gradient(135deg, rgba(10, 40, 30, 0.60), rgba(0, 0, 0, 0.30));
    z-index: -1;
}}

/* CONTAINER PRINCIPAL */
.block-container {{
    max-width: 1200px;
    padding-top: 2rem;
    padding-bottom: 2rem;
}}

/* HEADER */
.login-header {{
    background-color: rgba(255, 255, 255, 0.96);
    border-radius: 12px;
    padding: 15px 30px;
    margin-bottom: 45px;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.20);
}}
.company-title {{
    font-size: 24px;
    font-weight: 700;
    color: #173f34;
    margin-top: 10px;
}}
.company-subtitle {{
    font-size: 13px;
    color: #6b7280;
}}

/* CARTE LOGIN */
.login-title {{
    text-align: center;
    font-size: 30px;
    font-weight: 700;
    color: #173f34;
    margin-bottom: 8px;
}}
.login-subtitle {{
    text-align: center;
    font-size: 15px;
    color: #64748b;
    margin-bottom: 25px;
}}
.login-badge {{
    display: block;
    width: fit-content;
    margin: 0 auto 20px auto;
    background-color: #315f52;
    color: white;
    padding: 7px 20px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}

/* FORMULAIRE */
[data-testid="stTextInput"] label {{ color: #374151; font-weight: 600; }}
[data-testid="stTextInput"] input {{
    background-color: white;
    color: #1f2937;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 12px;
}}
[data-testid="stTextInput"] input:focus {{ border: 2px solid #2f7d5c; }}

/* BOUTON */
[data-testid="stButton"] button {{
    width: 100%;
    background-color: #245c4b;
    color: white;
    border: none;
    border-radius: 8px;
    height: 48px;
    font-size: 15px;
    font-weight: 700;
    transition: 0.3s;
}}
[data-testid="stButton"] button:hover {{ background-color: #173f34; color: white; border: none; }}

/* FOOTER */
.login-footer {{
    text-align: center;
    color: white;
    margin-top: 30px;
    font-size: 13px;
    text-shadow: 0 2px 5px rgba(0, 0, 0, 0.5);
}}
</style>""",
        unsafe_allow_html=True
    )


# ============================================================
# PAGE DE CONNEXION
# ============================================================

def login_page():
    apply_login_style()

    # HEADER
    header_left, header_right = st.columns([1, 7])
    
    with header_left:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=85)
        else:
            st.markdown("## 🟢 OCP")

    with header_right:
        st.markdown(
"""<div class="company-title">OCP GROUP</div>
<div class="company-subtitle">CAP Supervision • Plateforme de supervision industrielle</div>""",
            unsafe_allow_html=True
        )

    st.markdown("<br><br>", unsafe_allow_html=True)

    # CENTRAGE DU FORMULAIRE
    left_space, login_column, right_space = st.columns([1.5, 2, 1.5])

    with login_column:
        st.markdown(
"""<div class="login-badge">ESPACE UTILISATEUR</div>
<div class="login-title">CAP SUPERVISION</div>
<div class="login-subtitle">Accédez à votre espace de supervision industrielle</div>""",
            unsafe_allow_html=True
        )

        with st.form("login_form"):
            email = st.text_input("Email professionnel", placeholder="exemple@ocp.com")
            password = st.text_input("Mot de passe", type="password", placeholder="Entrez votre mot de passe")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            submitted = st.form_submit_button("ACCÉDER AU TABLEAU DE BORD", use_container_width=True)

            if submitted:
                if email == AUTHORIZED_EMAIL and password == AUTHORIZED_PASSWORD:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.rerun()
                elif not email or not password:
                    st.warning("Veuillez renseigner votre email et votre mot de passe.")
                else:
                    st.error("Email ou mot de passe incorrect.")

    # FOOTER
    st.markdown(
"""<div class="login-footer">
    OCP Group • CAP Supervision<br>Plateforme de supervision industrielle
</div>""",
        unsafe_allow_html=True
    )


# ============================================================
# STYLE DASHBOARD
# ============================================================

def apply_dashboard_style():
    st.markdown(
"""<style>
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.stApp { background-color: #f4f6f8; }
.block-container { max-width: 1400px; padding-top: 2rem; }

/* HEADER */
.dashboard-header {
    background-color: white;
    padding: 15px 25px;
    border-radius: 12px;
    box-shadow: 0 3px 12px rgba(0, 0, 0, 0.06);
    margin-bottom: 30px;
}

/* TITRES */
.dashboard-title {
    font-size: 34px;
    font-weight: 700;
    color: #173f34;
    margin-bottom: 5px;
}
.dashboard-subtitle {
    font-size: 16px;
    color: #64748b;
    margin-bottom: 30px;
}

/* KPI */
.kpi-card {
    background-color: white;
    padding: 25px;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.05);
    min-height: 130px;
}
.kpi-label {
    font-size: 15px;
    color: #64748b;
    margin-bottom: 12px;
}
.kpi-value {
    font-size: 34px;
    font-weight: 700;
    color: #173f34;
}

/* SECTION */
.section-title {
    font-size: 22px;
    font-weight: 700;
    color: #173f34;
    margin-top: 30px;
    margin-bottom: 15px;
}
</style>""",
        unsafe_allow_html=True
    )


# ============================================================
# PAGE TABLEAU DE BORD
# ============================================================

def dashboard_page():
    apply_dashboard_style()

    # HEADER
    col_logo, col_title, col_user, col_logout = st.columns([1, 5, 2, 1.5])

    with col_logo:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), width=80)

    with col_title:
        st.markdown(
            """
            ### CAP SUPERVISION
            Plateforme intelligente de supervision industrielle
            """
        )

    with col_user:
        st.write("")
        st.markdown(f"👤 **{st.session_state.user_email}**")

    with col_logout:
        st.write("")
        if st.button("Déconnexion", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_email = ""
            st.rerun()

    st.divider()

    # TITRE
    st.markdown(
"""<div class="dashboard-title">Tableau de bord de supervision</div>
<div class="dashboard-subtitle">Vue globale des données de l'unité de concentration d'acide phosphorique</div>""",
        unsafe_allow_html=True
    )

    # RECUPERATION DES DONNEES
    alarmes = get_api_data("/alarmes")
    anomalies = get_api_data("/anomalies")
    arrets = get_api_data("/arrets")
    mesures = get_api_data("/mesures")

    # KPI
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
f"""<div class="kpi-card">
    <div class="kpi-label">🚨 Alarmes</div>
    <div class="kpi-value">{alarmes["count"]}</div>
</div>""",
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
f"""<div class="kpi-card">
    <div class="kpi-label">⚠ Anomalies</div>
    <div class="kpi-value">{anomalies["count"]}</div>
</div>""",
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
f"""<div class="kpi-card">
    <div class="kpi-label">⏹ Arrêts</div>
    <div class="kpi-value">{arrets["count"]}</div>
</div>""",
            unsafe_allow_html=True
        )

    with col4:
        st.markdown(
f"""<div class="kpi-card">
    <div class="kpi-label">📊 Mesures</div>
    <div class="kpi-value">{mesures["count"]}</div>
</div>""",
            unsafe_allow_html=True
        )

    # ETAT DES SERVICES
    st.markdown(
        '<div class="section-title">État des sources de données</div>',
        unsafe_allow_html=True
    )

    status_col1, status_col2, status_col3, status_col4 = st.columns(4)

    with status_col1:
        if alarmes["success"]:
            st.success("Alarmes : connecté")
        else:
            st.error("Alarmes : indisponible")

    with status_col2:
        if anomalies["success"]:
            st.success("Anomalies : connecté")
        else:
            st.error("Anomalies : indisponible")

    with status_col3:
        if arrets["success"]:
            st.success("Arrêts : connecté")
        else:
            st.error("Arrêts : indisponible")

    with status_col4:
        if mesures["success"]:
            st.success("Mesures : connecté")
        else:
            st.error("Mesures : indisponible")

    # ETAT GLOBAL
    st.markdown(
        '<div class="section-title">État global de l\'unité</div>',
        unsafe_allow_html=True
    )

    if not all([alarmes["success"], anomalies["success"], arrets["success"], mesures["success"]]):
        st.warning("Certaines sources de données ne sont pas accessibles. Vérifiez que FastAPI est démarré.")
    elif anomalies["count"] == 0:
        st.success("L'unité fonctionne normalement.")
    elif anomalies["count"] < 10:
        st.warning(f"Attention : {anomalies['count']} anomalies détectées.")
    else:
        st.error(f"Situation à surveiller : {anomalies['count']} anomalies détectées.")

    # MODULES
    st.markdown(
        '<div class="section-title">Modules de supervision</div>',
        unsafe_allow_html=True
    )

    module_col1, module_col2 = st.columns(2)

    with module_col1:
        st.info("📊 Mesures — Consultation et suivi des variables du procédé.")
        st.warning("⚠ Anomalies — Détection des comportements anormaux.")

    with module_col2:
        st.error("🚨 Alarmes — Suivi des alarmes et de leur criticité.")
        st.success("⏹ Arrêts — Analyse des arrêts et de leurs causes.")

    # FOOTER
    st.markdown("---")
    st.caption("OCP Group • CAP Supervision • Plateforme de supervision industrielle")


# ============================================================
# APPLICATION PRINCIPALE
# ============================================================

if st.session_state.authenticated:
    dashboard_page()
else:
    login_page()