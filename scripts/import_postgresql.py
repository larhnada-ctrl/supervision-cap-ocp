"""
Importe les fichiers Excel nettoyés dans PostgreSQL.

Ce script est destiné à être lancé ponctuellement, à la main,
depuis un poste de développement ou un job unique. Il n'est pas
appelé au démarrage de l'application : chaque table est recréée
(if_exists="replace"), un lancement accidentel effacerait les
données existantes.

Usage :
    python scripts/import_postgresql.py
"""

import sys
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import text


# ---------------------------------------------------------
# Chemins du projet
# ---------------------------------------------------------
# La racine du dépôt est ajoutée au chemin d'import pour que
# "python scripts/import_postgresql.py" trouve le paquet common.

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_DIR = BASE_DIR / "data" / "cleaned"


from common.db import (  # noqa: E402  (import après ajustement de sys.path)
    check_connection,
    describe_target,
    get_engine,
)


# ---------------------------------------------------------
# Réglages d'insertion
# ---------------------------------------------------------
# method="multi" regroupe plusieurs lignes dans une seule
# instruction INSERT. Sur une base distante comme Neon, cela
# remplace des dizaines de milliers d'allers-retours réseau par
# quelques requêtes : l'import passe de plusieurs minutes à
# quelques secondes.

CHUNK_SIZE = 5000

# PostgreSQL n'accepte pas plus de 65535 paramètres liés par
# instruction. Avec method="multi", le nombre de paramètres vaut
# lignes x colonnes : on borne la taille des lots en conséquence.
MAX_BOUND_PARAMETERS = 60000


# ---------------------------------------------------------
# Correspondance fichiers Excel / tables PostgreSQL
# ---------------------------------------------------------

FILES_TO_TABLES = {
    "mesures_dcs.xlsx": "mesures_dcs",
    "etats_scada.xlsx": "etats_scada",
    "alarmes.xlsx": "alarmes",
    "arrets_cap.xlsx": "arrets_cap",
    "laboratoire.xlsx": "laboratoire",
    "Regles_Simples.xlsx": "regles_simples",
    "Regles_Croisees.xlsx": "regles_croisees",
}


# ---------------------------------------------------------
# Colonnes contenant des dates
# ---------------------------------------------------------

DATE_COLUMNS = {
    "mesures_dcs.xlsx": ["timestamp"],
    "etats_scada.xlsx": ["timestamp"],
    "alarmes.xlsx": ["debut", "fin"],
    "arrets_cap.xlsx": ["debut_arret", "fin_arret"],
    "laboratoire.xlsx": ["timestamp"],
}


# ---------------------------------------------------------
# Index à créer après l'import
# ---------------------------------------------------------
# to_sql(if_exists="replace") supprime puis recrée la table :
# les index sont donc perdus à chaque import et doivent être
# reconstruits ensuite, dans la même transaction.
#
# mesures_dcs est la seule table volumineuse interrogée avec un
# filtre : /mesures?tag=... puis ORDER BY timestamp DESC.
# L'index composite couvre le filtre et le tri en une seule
# structure ; le second sert au tri sans filtre.

INDEXES = {
    "mesures_dcs": [
        (
            "idx_mesures_dcs_tag_timestamp",
            'mesures_dcs (tag, "timestamp" DESC)',
        ),
        (
            "idx_mesures_dcs_timestamp",
            'mesures_dcs ("timestamp" DESC)',
        ),
    ],
}


# ---------------------------------------------------------
# Lecture d'un fichier Excel nettoyé
# ---------------------------------------------------------

def read_cleaned_excel(filename: str) -> pd.DataFrame:
    file_path = DATA_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"Le fichier est introuvable : {file_path}"
        )

    dataframe = pd.read_excel(
        file_path,
        sheet_name=0,
        engine="openpyxl",
    )

    # Nettoyage de sécurité des noms de colonnes
    dataframe.columns = (
        dataframe.columns
        .astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.replace("ï»¿", "", regex=False)
        .str.strip()
        .str.lower()
    )

    return dataframe


# ---------------------------------------------------------
# Conversion des colonnes de date
# ---------------------------------------------------------

def convert_date_columns(
    filename: str,
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    columns_to_convert = DATE_COLUMNS.get(filename, [])

    for column in columns_to_convert:
        if column in dataframe.columns:
            dataframe[column] = pd.to_datetime(
                dataframe[column],
                dayfirst=True,
                errors="coerce",
            )

    return dataframe


# ---------------------------------------------------------
# Taille de lot adaptée au nombre de colonnes
# ---------------------------------------------------------

def compute_chunk_size(column_count: int) -> int:

    if column_count <= 0:
        return CHUNK_SIZE

    limit = max(1, MAX_BOUND_PARAMETERS // column_count)

    return min(CHUNK_SIZE, limit)


# ---------------------------------------------------------
# Création des index
# ---------------------------------------------------------

def create_indexes(connection) -> None:

    for table_name, definitions in INDEXES.items():

        for index_name, target in definitions:

            connection.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} "
                    f"ON {target}"
                )
            )

        # Rafraîchit les statistiques du planificateur pour que
        # les nouveaux index soient réellement utilisés.
        connection.execute(
            text(f"ANALYZE {table_name}")
        )

        print(
            f"  {table_name:<18} "
            f"{len(definitions):>6} index    "
            f"statistiques mises à jour"
        )


# ---------------------------------------------------------
# Programme principal
# ---------------------------------------------------------

def main() -> None:
    engine = None
    total_rows = 0

    try:
        engine = get_engine()

        check_connection(engine)

        print(f"Connexion PostgreSQL réussie : {describe_target()}")
        print()

        # L'ensemble de l'import tient dans une seule transaction :
        # en cas d'échec, aucune table n'est laissée à moitié
        # remplie.
        with engine.begin() as connection:

            for filename, table_name in FILES_TO_TABLES.items():

                started_at = time.perf_counter()

                dataframe = read_cleaned_excel(filename)

                dataframe = convert_date_columns(
                    filename,
                    dataframe,
                )

                chunk_size = compute_chunk_size(
                    len(dataframe.columns)
                )

                dataframe.to_sql(
                    name=table_name,
                    con=connection,
                    if_exists="replace",
                    index=False,
                    chunksize=chunk_size,
                    method="multi",
                )

                elapsed = time.perf_counter() - started_at
                total_rows += len(dataframe)

                print(
                    f"  {table_name:<18} "
                    f"{len(dataframe):>6} lignes  "
                    f"{len(dataframe.columns)} colonnes  "
                    f"{elapsed:5.2f}s"
                )

            print()

            create_indexes(connection)

        print()
        print(
            f"Importation terminée : {total_rows} lignes "
            f"dans {len(FILES_TO_TABLES)} tables."
        )

    except FileNotFoundError as error:
        print(f"Erreur de fichier : {error}", file=sys.stderr)
        sys.exit(1)

    except Exception as error:
        print(
            f"Erreur pendant l'importation : {error}",
            file=sys.stderr,
        )
        sys.exit(1)

    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()