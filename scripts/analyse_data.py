from pathlib import Path

import pandas as pd


# 1. Définition des chemins

# Chemin du dossier principal du projet
BASE_DIR = Path(__file__).resolve().parent.parent

# Chemin du dossier contenant les fichiers Excel
DATA_DIR = BASE_DIR / "data"


# 2. Fonction de lecture d'un fichier Excel


def lire_excel(nom_fichier: str) -> pd.DataFrame:
    """
    Lit un fichier Excel situé dans le dossier data
    et retourne son contenu sous forme de DataFrame pandas.
    """

    chemin_fichier = DATA_DIR / nom_fichier

    # Vérification de l'existence du fichier
    if not chemin_fichier.exists():
        raise FileNotFoundError(
            f"Le fichier est introuvable : {chemin_fichier}"
        )

    dataframe = pd.read_excel(
        chemin_fichier,
        engine="openpyxl",
    )

    # Suppression des espaces inutiles dans les noms de colonnes
    dataframe.columns = (
        dataframe.columns
        .astype(str)
        .str.strip()
    )

    return dataframe


# 3. Analyse des mesures DCS


def analyser_mesures(mesures: pd.DataFrame) -> None:
    """
    Calcule le minimum, la moyenne et le maximum
    pour chaque tag et chaque paramètre.
    """

    print("\n--- Statistiques des mesures DCS ---")

    colonnes_obligatoires = {
        "tag",
        "parametre",
        "valeur",
    }

    colonnes_manquantes = (
        colonnes_obligatoires
        - set(mesures.columns)
    )

    if colonnes_manquantes:
        print(
            "Colonnes manquantes dans mesures_dcs.xlsx : "
            + ", ".join(sorted(colonnes_manquantes))
        )
        return

    # Conversion de la colonne valeur en nombre
    mesures["valeur"] = pd.to_numeric(
        mesures["valeur"],
        errors="coerce",
    )

    # Suppression des lignes sans valeur numérique
    mesures_valides = mesures.dropna(
        subset=["tag", "parametre", "valeur"]
    )

    statistiques = (
        mesures_valides
        .groupby(["tag", "parametre"])["valeur"]
        .agg(["min", "mean", "max"])
        .round(2)
    )

    if statistiques.empty:
        print("Aucune mesure valide trouvée.")
    else:
        print(statistiques)



# 4. Analyse des alarmes


def analyser_alarmes(alarmes: pd.DataFrame) -> None:
    """
    Compte le nombre d'alarmes par niveau de criticité.
    """

    print("\n--- Nombre d'alarmes par criticité ---")

    if "criticite" not in alarmes.columns:
        print(
            "La colonne 'criticite' est absente "
            "du fichier alarmes.xlsx."
        )
        return

    alarmes["criticite"] = (
        alarmes["criticite"]
        .astype(str)
        .str.strip()
    )

    nombre_alarmes = (
        alarmes["criticite"]
        .replace("", pd.NA)
        .dropna()
        .value_counts()
    )

    if nombre_alarmes.empty:
        print("Aucune alarme trouvée.")
    else:
        print(nombre_alarmes)



# 5. Analyse des arrêts

def analyser_arrets(arrets: pd.DataFrame) -> None:
    """
    Calcule la durée totale des arrêts par catégorie.
    """

    print("\n--- Durée totale des arrêts par catégorie ---")

    colonnes_obligatoires = {
        "categorie",
        "duree_min",
    }

    colonnes_manquantes = (
        colonnes_obligatoires
        - set(arrets.columns)
    )

    if colonnes_manquantes:
        print(
            "Colonnes manquantes dans arrets_cap.xlsx : "
            + ", ".join(sorted(colonnes_manquantes))
        )
        return

    arrets["duree_min"] = pd.to_numeric(
        arrets["duree_min"],
        errors="coerce",
    )

    arrets_valides = arrets.dropna(
        subset=["categorie", "duree_min"]
    )

    durees_par_categorie = (
        arrets_valides
        .groupby("categorie")["duree_min"]
        .sum()
        .sort_values(ascending=False)
    )

    if durees_par_categorie.empty:
        print("Aucun arrêt valide trouvé.")
    else:
        print(durees_par_categorie)



# 6. Analyse des résultats du laboratoire

def analyser_laboratoire(
    laboratoire: pd.DataFrame,) -> None:
    """
    Affiche uniquement les résultats de laboratoire
    marqués comme non conformes.
    """

    print("\n--- Résultats laboratoire non conformes ---")

    if "conforme" not in laboratoire.columns:
        print(
            "La colonne 'conforme' est absente du fichier laboratoire.xlsx."
        )
        return

    conforme_normalise = (
        laboratoire["conforme"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    non_conformes = laboratoire[
        conforme_normalise == "non"
    ]

    if non_conformes.empty:
        print(
            "Aucun résultat laboratoire non conforme."
        )
    else:
        print(non_conformes.to_string(index=False))



# 7. Programme principal


def main() -> None:
    """
    Fonction principale du programme.
    """

    try:
        print("Début de l'analyse des fichiers Excel.")

        # Lecture des fichiers Excel
        mesures = lire_excel(
            "mesures_dcs.xlsx"
        )

        alarmes = lire_excel(
            "alarmes.xlsx"
        )

        arrets = lire_excel(
            "arrets_cap.xlsx"
        )

        laboratoire = lire_excel(
            "laboratoire.xlsx"
        )

        print(
            "\nTous les fichiers Excel ont été lus correctement."
        )

        # Analyse des différentes données
        analyser_mesures(mesures)
        analyser_alarmes(alarmes)
        analyser_arrets(arrets)
        analyser_laboratoire(laboratoire)

        print("\nAnalyse terminée.")

    except FileNotFoundError as error:
        print(f"\nErreur de fichier : {error}")

    except PermissionError:
        print(
            "\nErreur : un fichier Excel est peut-être "
            "ouvert dans Excel. Ferme-le puis relance le script."
        )

    except ImportError:
        print(
            "\nErreur : la bibliothèque openpyxl "
            "n'est pas installée."
        )

        print(
            "Commande à exécuter : "
            "pip install openpyxl"
        )

    except Exception as error:
        print(
            f"\nErreur pendant l'analyse : {error}"
        )



# 8. Lancement du programme


if __name__ == "__main__":
    main()