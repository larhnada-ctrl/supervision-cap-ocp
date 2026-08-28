import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text


# ---------------------------------------------------------
# Chemins du projet
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "cleaned"


# ---------------------------------------------------------
# Paramètres PostgreSQL
# ---------------------------------------------------------

DB_USER = "postgres"
DB_PASSWORD = os.getenv("CAP_DB_PASSWORD")
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "cap_supervision"


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
# Création de la connexion PostgreSQL
# ---------------------------------------------------------

def create_postgresql_engine():
    if not DB_PASSWORD:
        raise ValueError(
            "Le mot de passe PostgreSQL n'est pas défini. "
            "Définissez la variable CAP_DB_PASSWORD."
        )

    password_encoded = quote_plus(DB_PASSWORD)

    database_url = (
        f"postgresql+psycopg2://{DB_USER}:"
        f"{password_encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    return create_engine(database_url)


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
# Programme principal
# ---------------------------------------------------------

def main() -> None:
    engine = None

    try:
        engine = create_postgresql_engine()

        # Test de connexion
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        print("Connexion PostgreSQL réussie.")

        # Importation des fichiers Excel
        with engine.begin() as connection:
            for filename, table_name in FILES_TO_TABLES.items():
                dataframe = read_cleaned_excel(filename)

                dataframe = convert_date_columns(
                    filename,
                    dataframe,
                )

                print(
                    f"{filename} - Colonnes détectées : "
                    f"{list(dataframe.columns)}"
                )

                dataframe.to_sql(
                    name=table_name,
                    con=connection,
                    if_exists="replace",
                    index=False,
                )

                print(
                    f"{table_name} : "
                    f"{len(dataframe)} lignes importées"
                )

        print("Importation terminée avec succès.")

    except FileNotFoundError as error:
        print(f"Erreur de fichier : {error}")

    except Exception as error:
        print(f"Erreur pendant l'importation : {error}")

    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()