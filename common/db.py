"""
Source unique de verite pour la connexion PostgreSQL.

Ce module est importe par l'API (api/main.py) et par les scripts
du dossier scripts/. Il centralise :

  - le chargement du fichier .env en developpement local ;
  - la lecture et la normalisation de DATABASE_URL ;
  - la construction du moteur SQLAlchemy avec des reglages
    adaptes a Neon (PostgreSQL serverless).
"""

from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import (
    parse_qsl,
    quote_plus,
    urlencode,
    urlsplit,
    urlunsplit,
)

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


# =========================================================
# CHARGEMENT DU FICHIER .env
# =========================================================
# En local, .env fournit DATABASE_URL.
# En production (Render / Streamlit Cloud), les variables sont
# deja presentes dans l'environnement : load_dotenv ne fait rien
# et n'ecrase jamais une variable existante.

load_dotenv(override=False)


# =========================================================
# CONSTANTES
# =========================================================

DRIVER = "postgresql+psycopg2"

# Neon suspend les connexions inactives. pool_pre_ping teste la
# connexion avant chaque emprunt au pool et remplace en silence
# celles qui ont ete fermees par le serveur : c'est ce qui evite
# les erreurs "SSL connection has been closed unexpectedly".
POOL_SETTINGS = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_size": 5,
    "max_overflow": 5,
}

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", ""}


class DatabaseConfigError(RuntimeError):
    """Configuration de base de donnees absente ou invalide."""


# =========================================================
# CONSTRUCTION DE L'URL A PARTIR DE VARIABLES SEPAREES
# =========================================================

def _url_from_discrete_variables() -> str | None:
    """
    Solution de repli : reconstruit une URL a partir de
    DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME.
    """

    host = os.getenv("DB_HOST")
    password = os.getenv("DB_PASSWORD") or os.getenv("CAP_DB_PASSWORD")

    if not host or not password:
        return None

    user = os.getenv("DB_USER", "postgres")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "cap_supervision")

    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{name}"
    )


# =========================================================
# NORMALISATION DE L'URL
# =========================================================

def normalise_database_url(raw_url: str) -> str:
    """
    Rend une URL fournie par un hebergeur utilisable par SQLAlchemy 2.

    Deux corrections sont appliquees :

    1. Le schema. Neon, Render et Railway distribuent des URL en
       'postgres://' ou 'postgresql://'. SQLAlchemy 2 a besoin du
       pilote explicite : 'postgresql+psycopg2://'.

    2. Le TLS. Si l'hote est distant et que sslmode est absent,
       on ajoute sslmode=require.

    Le netloc (identifiants, hote, port) est recopie tel quel afin
    de ne pas casser un mot de passe deja encode par l'hebergeur.
    """

    url = raw_url.strip().strip('"').strip("'")

    if not url:
        raise DatabaseConfigError("DATABASE_URL est vide.")

    parts = urlsplit(url)
    scheme = parts.scheme.lower()

    if scheme in ("postgres", "postgresql"):
        scheme = DRIVER

    elif scheme.startswith("postgresql+"):
        # Le pilote est deja precise, on n'y touche pas.
        pass

    else:
        raise DatabaseConfigError(
            f"Schema d'URL non supporte : '{parts.scheme}'. "
            "Une URL PostgreSQL est attendue."
        )

    query = dict(parse_qsl(parts.query, keep_blank_values=True))

    host = (parts.hostname or "").lower()

    if host not in LOCAL_HOSTS:
        query.setdefault("sslmode", "require")

    return urlunsplit(
        (
            scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        )
    )


# =========================================================
# LECTURE DE LA CONFIGURATION
# =========================================================

def get_database_url(prefer_pooled: bool = False) -> str:
    """
    Retourne l'URL de connexion normalisee.

    prefer_pooled=True privilegie DATABASE_URL_POOLED lorsqu'elle
    existe. Le pooler Neon (PgBouncer, mode transaction) convient
    a l'API, qui enchaine de nombreuses requetes courtes.

    Les scripts de traitement par lots gardent la connexion directe
    (prefer_pooled=False) : ils ouvrent de longues transactions et
    executent du DDL, deux usages mal adaptes au mode transaction.
    """

    raw_url = None

    if prefer_pooled:
        raw_url = os.getenv("DATABASE_URL_POOLED")

    raw_url = raw_url or os.getenv("DATABASE_URL")
    raw_url = raw_url or _url_from_discrete_variables()

    if not raw_url:
        raise DatabaseConfigError(
            "Aucune configuration de base de donnees trouvee. "
            "Definissez DATABASE_URL (ou DB_HOST / DB_USER / "
            "DB_PASSWORD / DB_NAME) dans l'environnement ou "
            "dans un fichier .env."
        )

    return normalise_database_url(raw_url)


# =========================================================
# MOTEUR SQLALCHEMY
# =========================================================

@lru_cache(maxsize=2)
def get_engine(prefer_pooled: bool = False) -> Engine:
    """
    Retourne le moteur SQLAlchemy partage.

    La creation est paresseuse et mise en cache : le moteur n'est
    construit qu'au premier appel, jamais a l'import du module.
    Un demarrage de conteneur ne peut donc pas echouer a cause
    d'une variable d'environnement manquante.
    """

    return create_engine(
        get_database_url(prefer_pooled=prefer_pooled),
        **POOL_SETTINGS,
    )


def check_connection(engine: Engine) -> None:
    """Execute SELECT 1. Leve une exception si la base est injoignable."""

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def describe_target(prefer_pooled: bool = False) -> str:
    """
    Decrit la cible de connexion sans divulguer le mot de passe.
    Utile dans les journaux et les scripts.
    """

    parts = urlsplit(get_database_url(prefer_pooled=prefer_pooled))

    database = parts.path.lstrip("/") or "(defaut)"

    return f"{parts.hostname}:{parts.port or 5432}/{database}"