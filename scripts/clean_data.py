from pathlib import Path

import pandas as pd


# Chemins du projet
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = DATA_DIR / "cleaned"

OUTPUT_DIR.mkdir(exist_ok=True)



# Fichiers Excel à nettoyer
FILES = [
    "mesures_dcs.xlsx",

    
    "etats_scada.xlsx",
    "alarmes.xlsx",
    "arrets_cap.xlsx",
    "laboratoire.xlsx",
    "Regles_Simples.xlsx",
    "Regles_Croisees.xlsx",
]



# Colonnes contenant des dates

DATE_COLUMNS = {
    "mesures_dcs.xlsx": ["timestamp"],
    "etats_scada.xlsx": ["timestamp"],
    "alarmes.xlsx": ["debut", "fin"],
    "arrets_cap.xlsx": ["debut_arret", "fin_arret"],
    "laboratoire.xlsx": ["timestamp"],
}



# Colonnes numériques

NUMERIC_COLUMNS = {
    "mesures_dcs.xlsx": ["valeur"],
    "etats_scada.xlsx": ["defaut"],
    "arrets_cap.xlsx": ["duree_min"],
    "laboratoire.xlsx": ["valeur"],
}



# Lecture d'un fichier Excel


def read_excel_file(filename: str) -> pd.DataFrame:
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

    return dataframe



# Nettoyage général

def clean_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    # Nettoyage des noms de colonnes
    dataframe.columns = (
        dataframe.columns
        .astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.replace("ï»¿", "", regex=False)
        .str.strip()
        .str.lower()
    )

    # Nettoyage des colonnes texte
    text_columns = dataframe.select_dtypes(
        include=["object", "string"]
    ).columns

    for column in text_columns:
        dataframe[column] = (
            dataframe[column]
            .astype("string")
            .str.strip()
        )

    # Suppression des lignes entièrement vides
    dataframe = dataframe.dropna(how="all")

    # Suppression des doublons
    dataframe = dataframe.drop_duplicates()

    return dataframe



# Conversion des dates

def convert_dates(
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


# Conversion des valeurs numériques

def convert_numeric_columns(
    filename: str,
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    columns_to_convert = NUMERIC_COLUMNS.get(filename, [])

    for column in columns_to_convert:
        if column in dataframe.columns:
            # Gère les valeurs écrites avec une virgule dans Excel
            dataframe[column] = (
                dataframe[column]
                .astype(str)
                .str.replace(",", ".", regex=False)
            )

            dataframe[column] = pd.to_numeric(
                dataframe[column],
                errors="coerce",
            )

    return dataframe



# Vérification des valeurs manquantes

def check_missing_values(
    filename: str,
    dataframe: pd.DataFrame,
) -> None:

    missing_values = dataframe.isna().sum()
    missing_values = missing_values[missing_values > 0]

    if missing_values.empty:
        print(f"{filename} : aucune valeur manquante.")
    else:
        print(f"{filename} : valeurs manquantes détectées :")
        print(missing_values)



# Programme principal

def main() -> None:
    for filename in FILES:
        try:
            dataframe = read_excel_file(filename)

            dataframe = clean_dataframe(dataframe)

            dataframe = convert_dates(
                filename,
                dataframe,
            )

            dataframe = convert_numeric_columns(
                filename,
                dataframe,
            )

            check_missing_values(
                filename,
                dataframe,
            )

            output_path = OUTPUT_DIR / filename

            dataframe.to_excel(
                output_path,
                index=False,
                engine="openpyxl",
            )

            print(
                f"Fichier nettoyé : {output_path} "
                f"({len(dataframe)} lignes)"
            )

        except Exception as error:
            print(f"Erreur avec {filename} : {error}")


if __name__ == "__main__":
    main()