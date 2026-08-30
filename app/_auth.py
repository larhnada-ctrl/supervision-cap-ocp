"""
Garde d'authentification partagée par les pages Streamlit.

Streamlit expose chaque fichier de app/pages/ à sa propre URL.
Sans contrôle explicite, un visiteur peut donc atteindre
directement /1_Mesures et consulter les données sans jamais
passer par l'écran de connexion de home.py.

Chaque page appelle require_auth() juste après
st.set_page_config() pour fermer ce contournement.
"""

# Importe par chaque page : c'est le point ou .env est charge
# lorsqu'une page est ouverte directement en local.
from dotenv import load_dotenv

load_dotenv(override=False)

import streamlit as st


def is_authenticated() -> bool:
    """Indique si la session courante est authentifiée."""

    return bool(
        st.session_state.get("authenticated", False)
    )


def require_auth() -> None:
    """
    Interrompt le rendu de la page si l'utilisateur n'est pas
    authentifié.

    st.stop() met fin à l'exécution du script : aucun appel à
    l'API n'est effectué et aucune donnée n'est affichée.
    """

    if is_authenticated():
        return

    st.warning(
        "Accès restreint. Veuillez vous connecter depuis la "
        "page d'accueil pour consulter cette section."
    )

    # st.page_link n'existe que sur les versions récentes de
    # Streamlit : on reste tolérant si elle est absente.
    try:
        st.page_link(
            "home.py",
            label="Aller à la page de connexion",
            icon="🔐",
        )

    except Exception:
        st.info(
            "Ouvrez la page « home » dans le menu latéral."
        )

    st.stop()