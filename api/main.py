import os
from urllib.parse import quote_plus

from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


# =========================================================
# CONFIGURATION FASTAPI
# =========================================================

app = FastAPI(
    title="CAP Supervision API",
    description="API d'accès aux données de l'unité CAP",
    version="1.0.0",
)


# =========================================================
# CONFIGURATION POSTGRESQL
# =========================================================

DB_USER = "postgres"
DB_PASSWORD = os.getenv("CAP_DB_PASSWORD")
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "cap_supervision"


def create_postgresql_engine():

    if not DB_PASSWORD:
        raise RuntimeError(
            "La variable CAP_DB_PASSWORD n'est pas définie."
        )

    password_encoded = quote_plus(DB_PASSWORD)

    database_url = (
        f"postgresql+psycopg2://{DB_USER}:"
        f"{password_encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    return create_engine(database_url)


engine = create_postgresql_engine()


# =========================================================
# FONCTION UTILITAIRE
# =========================================================

def execute_query(query, parameters=None):

    try:

        with engine.connect() as connection:

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

    except SQLAlchemyError as error:

        raise HTTPException(
            status_code=500,
            detail=f"Erreur PostgreSQL : {error}"
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
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    try:

        with engine.connect() as connection:

            connection.execute(
                text("SELECT 1")
            )

        return {
            "status": "ok",
            "database": "connectée"
        }

    except SQLAlchemyError as error:

        raise HTTPException(
            status_code=500,
            detail=f"Erreur de connexion : {error}"
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