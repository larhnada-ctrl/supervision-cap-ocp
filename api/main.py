import logging
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.db import DatabaseConfigError, get_engine


logger = logging.getLogger("cap.api")


# =========================================================
# CONFIGURATION FASTAPI
# =========================================================

app = FastAPI(
    title="CAP Supervision API",
    description="API d'accès aux données de l'unité CAP",
    version="1.0.0",
)


# =========================================================
# CONFIGURATION CORS
# =========================================================
# CORS_ORIGINS accepte une liste d'origines séparées par des
# virgules. Exemple :
#     CORS_ORIGINS=https://cap-supervision.streamlit.app
# La valeur par défaut "*" ouvre l'API à toutes les origines.

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials="*" not in CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# CONNEXION POSTGRESQL
# =========================================================
# La configuration vient de common/db.py, qui lit DATABASE_URL.
# Le moteur est construit au premier appel, pas à l'import : si
# la base est injoignable au démarrage, le processus démarre
# quand même et /health répond. Cela évite les redémarrages en
# boucle et laisse un point d'observation exploitable.


def engine():
    """Retourne le moteur partagé (connexion via le pooler Neon)."""

    return get_engine(prefer_pooled=True)


# =========================================================
# FONCTION UTILITAIRE
# =========================================================

def execute_query(query, parameters=None):

    try:

        with engine().connect() as connection:

            result = connection.execute(
                text(query),
                parameters or {}
            )

            rows = [
                dict(row._mapping)
                for row in result
            ]

        return {
            "count": len(rows),
            "data": rows
        }

    except DatabaseConfigError as error:

        logger.error("Configuration base de données invalide : %s", error)

        raise HTTPException(
            status_code=500,
            detail="Configuration de la base de données invalide."
        )

    except SQLAlchemyError as error:

        # Le détail technique va dans les journaux du serveur ;
        # le client reçoit un message générique.
        logger.exception("Erreur PostgreSQL : %s", error)

        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'accès à la base de données."
        )


# =========================================================
# PAGE PRINCIPALE
# =========================================================

@app.get("/")
def root():

    return {
        "message": "API de supervision de l'unité CAP opérationnelle"
    }


# =========================================================
# HEALTH CHECK - LIVENESS
# =========================================================
# Ne touche pas à la base. Répond 200 tant que le processus est
# vivant. C'est cette route qu'il faut donner au health check de
# Render : elle ne provoque pas de redémarrage lorsque Neon met
# la base en veille.

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "cap-supervision-api"
    }


# =========================================================
# HEALTH CHECK - READINESS
# =========================================================
# Vérifie réellement la base avec un SELECT 1.

@app.get("/health/db")
def health_db():

    try:

        with engine().connect() as connection:

            connection.execute(
                text("SELECT 1")
            )

        return {
            "status": "ok",
            "database": "connectée"
        }

    except DatabaseConfigError as error:

        logger.error("Configuration base de données invalide : %s", error)

        raise HTTPException(
            status_code=503,
            detail="Configuration de la base de données invalide."
        )

    except SQLAlchemyError as error:

        logger.exception("Base injoignable : %s", error)

        raise HTTPException(
            status_code=503,
            detail="Base de données injoignable."
        )


# =========================================================
# MESURES DCS
# =========================================================

@app.get("/mesures")
def get_mesures(
    tag: str | None = Query(default=None)
):

    query = """
        SELECT
            timestamp,
            tag,
            parametre,
            valeur,
            unite,
            qualite
        FROM mesures_dcs
    """

    parameters = {}

    if tag:

        query += """
            WHERE tag = :tag
        """

        parameters["tag"] = tag

    query += """
        ORDER BY timestamp DESC
    """

    return execute_query(
        query,
        parameters
    )


# =========================================================
# MESURES PAR TAG
# =========================================================

@app.get("/mesures/{tag}")
def get_mesures_by_tag(
    tag: str
):

    query = """
        SELECT
            timestamp,
            tag,
            parametre,
            valeur,
            unite,
            qualite
        FROM mesures_dcs
        WHERE tag = :tag
        ORDER BY timestamp DESC
    """

    result = execute_query(
        query,
        {
            "tag": tag
        }
    )

    if result["count"] == 0:

        raise HTTPException(
            status_code=404,
            detail=f"Aucune mesure trouvée pour le tag {tag}"
        )

    return result


# =========================================================
# ALARMES
# =========================================================

@app.get("/alarmes")
def get_alarmes():

    query = """
        SELECT
            debut,
            fin,
            tag,
            alarme,
            criticite,
            acquittee
        FROM alarmes
        ORDER BY debut DESC
    """

    return execute_query(query)


# =========================================================
# ARRETS
# =========================================================

@app.get("/arrets")
def get_arrets():

    query = """
        SELECT
            debut_arret,
            fin_arret,
            duree_min,
            categorie,
            cause,
            equipement
        FROM arrets_cap
        ORDER BY debut_arret DESC
    """

    return execute_query(query)


# =========================================================
# ANOMALIES
# =========================================================

@app.get("/anomalies")
def get_anomalies():

    query = """
        SELECT
            debut_anomalie,
            fin_anomalie,
            duree_min,
            nombre_occurrences,
            rule_id,
            type_regle,
            regle,
            interpretation,
            cause_probable,
            criticite
        FROM anomalies_detectees
        ORDER BY debut_anomalie DESC
    """

    return execute_query(query)


# =========================================================
# LABORATOIRE
# =========================================================

@app.get("/laboratoire")
def get_laboratoire():

    query = """
        SELECT
            timestamp,
            echantillon,
            parametre,
            valeur,
            unite,
            conforme
        FROM laboratoire
        ORDER BY timestamp DESC
    """

    return execute_query(query)


# =========================================================
# ETATS SCADA
# =========================================================

@app.get("/etats-scada")
def get_etats_scada():

    query = """
        SELECT
            timestamp,
            equipement,
            tag,
            etat,
            mode,
            defaut
        FROM etats_scada
        ORDER BY timestamp DESC
    """

    return execute_query(query)