import os
import re
import unicodedata
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


# ============================================================
# 1. CONFIGURATION DE POSTGRESQL
# ============================================================

DB_USER = "postgres"
DB_PASSWORD = os.getenv("CAP_DB_PASSWORD")
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "cap_supervision"

# Les mesures sont enregistrées toutes les 10 minutes.
SAMPLE_INTERVAL_MINUTES = 10

# Deux occurrences de la même règle sont regroupées si elles
# sont séparées de 10 minutes au maximum.
MAX_GAP_MINUTES = 10


# ============================================================
# 2. ASSOCIATION ENTRE LES NOMS DES RÈGLES ET LES TAGS
# ============================================================

VARIABLE_TAGS = {
    "temperature": "304TI102",
    "pression": "304PI004",
    "vide": "304PIC005",
    "niveau": "304LT203",
    "debit_acide_29": "304FT401",
    "debit_acide_54": "304FT402",
    "conductivite": "304AI401",
    "ph": "304AI402",
    "pompe_circulation": "304AP01",
    "pompe_production": "304AP02",
    "vanne_vapeur": "304XV804",
}


# ============================================================
# 3. CONNEXION À POSTGRESQL
# ============================================================

def create_postgresql_engine() -> Engine:
    """
    Crée la connexion à la base de données PostgreSQL.
    """

    if not DB_PASSWORD:
        raise ValueError(
            "La variable CAP_DB_PASSWORD n'est pas définie."
        )

    encoded_password = quote_plus(DB_PASSWORD)

    database_url = (
        f"postgresql+psycopg2://{DB_USER}:"
        f"{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    return create_engine(database_url)


# ============================================================
# 4. NORMALISATION DU TEXTE
# ============================================================

def normalize_text(value) -> str:
    """
    Uniformise le texte afin de faciliter les comparaisons.

    """

    if value is None or pd.isna(value):
        return ""

    normalized = str(value).strip().lower()
    normalized = unicodedata.normalize(
        "NFD",
        normalized,
    )

    normalized = "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Mn"
    )

    normalized = normalized.replace("’", "'")
    normalized = normalized.replace(",", ".")
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


# ============================================================
# 5. VÉRIFICATION DES TABLES
# ============================================================

def check_required_tables(engine: Engine) -> None:
    """
    Vérifie que les tables nécessaires existent.
    """

    required_tables = {
        "mesures_dcs",
        "etats_scada",
        "regles_simples",
        "regles_croisees",
    }

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    missing_tables = required_tables - existing_tables

    if missing_tables:
        raise ValueError(
            "Tables absentes dans PostgreSQL : "
            + ", ".join(sorted(missing_tables))
        )


# ============================================================
# 6. LECTURE DES MESURES DCS
# ============================================================

def load_dcs_measurements(engine: Engine) -> pd.DataFrame:
    """
    Lit les mesures numériques depuis mesures_dcs.
    """

    query = text(
        """
        SELECT
            timestamp,
            tag,
            valeur
        FROM mesures_dcs
        WHERE timestamp IS NOT NULL
          AND tag IS NOT NULL
          AND valeur IS NOT NULL
        ORDER BY timestamp, tag;
        """
    )

    dataframe = pd.read_sql_query(
        query,
        engine,
    )

    dataframe["timestamp"] = pd.to_datetime(
        dataframe["timestamp"],
        errors="coerce",
    )

    dataframe["valeur"] = pd.to_numeric(
        dataframe["valeur"],
        errors="coerce",
    )

    dataframe["tag"] = (
        dataframe["tag"]
        .astype(str)
        .str.strip()
    )

    dataframe = dataframe.dropna(
        subset=["timestamp", "tag", "valeur"]
    )

    print(
        f"{len(dataframe)} mesures DCS chargées."
    )

    return dataframe


# ============================================================
# 7. LECTURE DES ÉTATS SCADA
# ============================================================

def load_scada_states(engine: Engine) -> pd.DataFrame:
    """
    Lit les états des équipements depuis etats_scada.
    """

    query = text(
        """
        SELECT
            timestamp,
            tag,
            etat
        FROM etats_scada
        WHERE timestamp IS NOT NULL
          AND tag IS NOT NULL
          AND etat IS NOT NULL
        ORDER BY timestamp, tag;
        """
    )

    dataframe = pd.read_sql_query(
        query,
        engine,
    )

    dataframe["timestamp"] = pd.to_datetime(
        dataframe["timestamp"],
        errors="coerce",
    )

    dataframe["tag"] = (
        dataframe["tag"]
        .astype(str)
        .str.strip()
    )

    dataframe["etat"] = (
        dataframe["etat"]
        .astype(str)
        .str.strip()
    )

    dataframe = dataframe.dropna(
        subset=["timestamp", "tag", "etat"]
    )

    print(
        f"{len(dataframe)} états SCADA chargés."
    )

    return dataframe


# ============================================================
# 8. LECTURE DES RÈGLES SIMPLES
# ============================================================

def load_simple_rules(engine: Engine) -> pd.DataFrame:
    """
    Lit directement les règles simples importées depuis Excel.
    """

    query = text(
        """
        SELECT
            tag,
            condition,
            interpretation,
            cause_probable,
            criticite
        FROM regles_simples
        WHERE tag IS NOT NULL
          AND condition IS NOT NULL;
        """
    )

    rules = pd.read_sql_query(
        query,
        engine,
    )

    rules = rules.dropna(
        subset=["tag", "condition"]
    )

    rules["tag"] = (
        rules["tag"]
        .astype(str)
        .str.strip()
    )

    print(
        f"{len(rules)} règles simples chargées."
    )

    return rules


# ============================================================
# 9. LECTURE DES RÈGLES CROISÉES
# ============================================================

def load_crossed_rules(engine: Engine) -> pd.DataFrame:
    """
    Lit directement les règles croisées importées depuis Excel.
    """

    query = text(
        """
        SELECT
            regle_croisee,
            interpretation,
            cause_probable,
            criticite
        FROM regles_croisees
        WHERE regle_croisee IS NOT NULL;
        """
    )

    rules = pd.read_sql_query(
        query,
        engine,
    )

    rules = rules.dropna(
        subset=["regle_croisee"]
    )

    print(
        f"{len(rules)} règles croisées chargées."
    )

    return rules


# ============================================================
# 10. TRANSFORMATION DES MESURES EN TABLE LARGE
# ============================================================

def create_dcs_table(
    measurements: pd.DataFrame,
) -> pd.DataFrame:
    """
    Transforme les tags numériques en colonnes.

    Avant :
        timestamp | tag       | valeur
        08:00     | 304TI102  | 75
        08:00     | 304PI004  | 2

    Après :
        timestamp | 304TI102 | 304PI004
        08:00     | 75       | 2
    """

    table = measurements.pivot_table(
        index="timestamp",
        columns="tag",
        values="valeur",
        aggfunc="mean",
    )

    table = table.reset_index()
    table.columns.name = None

    return table.sort_values(
        "timestamp"
    ).reset_index(drop=True)


# ============================================================
# 11. TRANSFORMATION DES ÉTATS SCADA
# ============================================================

def create_scada_table(
    states: pd.DataFrame,
) -> pd.DataFrame:
    """
    Transforme les états SCADA en colonnes.
    """

    table = states.pivot_table(
        index="timestamp",
        columns="tag",
        values="etat",
        aggfunc="last",
    )

    table = table.reset_index()
    table.columns.name = None

    return table.sort_values(
        "timestamp"
    ).reset_index(drop=True)


# ============================================================
# 12. CRÉATION D'UNE TABLE GLOBALE
# ============================================================

def create_global_table(
    dcs_table: pd.DataFrame,
    scada_table: pd.DataFrame,
) -> pd.DataFrame:
    """
    Réunit les mesures DCS et les états SCADA selon timestamp.
    """

    global_table = pd.merge(
        dcs_table,
        scada_table,
        on="timestamp",
        how="outer",
        suffixes=("", "_scada"),
    )

    global_table = global_table.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    # Propage le dernier état SCADA connu jusqu'à l'état suivant.
    scada_tags = [
        VARIABLE_TAGS["pompe_circulation"],
        VARIABLE_TAGS["pompe_production"],
        VARIABLE_TAGS["vanne_vapeur"],
    ]

    available_scada_tags = [
        tag
        for tag in scada_tags
        if tag in global_table.columns
    ]

    if available_scada_tags:
        global_table[available_scada_tags] = (
            global_table[available_scada_tags]
            .ffill()
        )

    return global_table


# ============================================================
# 13. COMPARAISON NUMÉRIQUE
# ============================================================

def compare_numeric_value(
    value,
    operator: str,
    threshold: float,
) -> bool:
    """
    Compare une valeur numérique avec un seuil.
    """

    if value is None or pd.isna(value):
        return False

    comparisons = {
        "<": lambda current, limit: current < limit,
        "<=": lambda current, limit: current <= limit,
        ">": lambda current, limit: current > limit,
        ">=": lambda current, limit: current >= limit,
        "=": lambda current, limit: current == limit,
        "==": lambda current, limit: current == limit,
        "!=": lambda current, limit: current != limit,
    }

    comparison = comparisons.get(operator)

    if comparison is None:
        raise ValueError(
            f"Opérateur numérique inconnu : {operator}"
        )

    return comparison(
        float(value),
        float(threshold),
    )


# ============================================================
# 14. COMPARAISON TEXTUELLE
# ============================================================

def compare_text_value(
    current_value,
    expected_value: str,
) -> bool:
    """
    Compare un état SCADA avec un état attendu.
    """

    current = normalize_text(current_value)
    expected = normalize_text(expected_value)

    if not current or not expected:
        return False

    # L'expression « fermée en production » signifie que la
    # vanne doit être fermée pendant que l'installation produit.
    if expected == "fermee en production":
        return current in {
            "fermee",
            "ferme",
            "closed",
            "0",
        }

    equivalent_states = {
        "arret": {
            "arret",
            "arretee",
            "arrete",
            "stop",
            "stopped",
            "0",
            "off",
        },
        "marche": {
            "marche",
            "en marche",
            "running",
            "1",
            "on",
        },
        "ouverte": {
            "ouverte",
            "ouvert",
            "open",
            "1",
        },
        "fermee": {
            "fermee",
            "ferme",
            "closed",
            "0",
        },
    }

    for reference_state, possible_values in (
        equivalent_states.items()
    ):
        if expected in possible_values:
            return current in possible_values

    return current == expected


# ============================================================
# 15. INTERPRÉTATION D'UNE CONDITION SIMPLE
# ============================================================

def evaluate_simple_condition(
    value,
    condition: str,
) -> bool:
    """
    Interprète les conditions des règles simples.

    Exemples acceptés :
        valeur < 70
        valeur > 80
        etat = Arret
        etat = Fermee en production
    """

    normalized_condition = normalize_text(condition)

    numeric_match = re.fullmatch(
        r"valeur\s*(<=|>=|!=|==|=|<|>)\s*(-?\d+(?:\.\d+)?)",
        normalized_condition,
    )

    if numeric_match:
        operator = numeric_match.group(1)
        threshold = float(numeric_match.group(2))

        return compare_numeric_value(
            value,
            operator,
            threshold,
        )

    state_match = re.fullmatch(
        r"etat\s*(==|=|!=)\s*(.+)",
        normalized_condition,
    )

    if state_match:
        operator = state_match.group(1)
        expected_state = state_match.group(2)

        result = compare_text_value(
            value,
            expected_state,
        )

        if operator == "!=":
            return not result

        return result

    raise ValueError(
        f"Condition simple non reconnue : {condition}"
    )


# ============================================================
# 16. AJOUT D'UNE OCCURRENCE
# ============================================================

def add_occurrence(
    occurrences: list[dict],
    timestamp,
    rule_id: str,
    rule_type: str,
    rule_text: str,
    interpretation,
    probable_cause,
    criticality,
) -> None:
    """
    Ajoute une occurrence anormale.
    """

    occurrences.append(
        {
            "timestamp": timestamp,
            "rule_id": rule_id,
            "type_regle": rule_type,
            "regle": rule_text,
            "interpretation": (
                ""
                if pd.isna(interpretation)
                else str(interpretation)
            ),
            "cause_probable": (
                ""
                if pd.isna(probable_cause)
                else str(probable_cause)
            ),
            "criticite": (
                ""
                if pd.isna(criticality)
                else str(criticality)
            ),
        }
    )


# ============================================================
# 17. APPLICATION DES RÈGLES SIMPLES
# ============================================================

def apply_simple_rules(
    global_table: pd.DataFrame,
    simple_rules: pd.DataFrame,
) -> list[dict]:
    """
    Applique les règles simples provenant de PostgreSQL.
    """

    occurrences: list[dict] = []

    for rule_index, rule in simple_rules.iterrows():
        tag = str(rule["tag"]).strip()
        condition = str(rule["condition"]).strip()

        rule_id = f"RS{rule_index + 1:02d}"

        if tag not in global_table.columns:
            print(
                f"Attention : tag {tag} absent pour {rule_id}."
            )
            continue

        for _, measurement in global_table.iterrows():
            value = measurement.get(tag)

            try:
                condition_result = evaluate_simple_condition(
                    value,
                    condition,
                )

            except ValueError as error:
                print(
                    f"Règle {rule_id} ignorée : {error}"
                )
                break

            if condition_result:
                add_occurrence(
                    occurrences=occurrences,
                    timestamp=measurement["timestamp"],
                    rule_id=rule_id,
                    rule_type="Simple",
                    rule_text=f"{tag} : {condition}",
                    interpretation=rule["interpretation"],
                    probable_cause=rule["cause_probable"],
                    criticality=rule["criticite"],
                )

    print(
        f"{len(occurrences)} occurrences simples détectées."
    )

    return occurrences


# ============================================================
# 18. RÉCUPÉRATION D'UNE VALEUR PAR NOM DE VARIABLE
# ============================================================

def get_variable_value(
    row: pd.Series,
    variable_name: str,
):
    """
    Récupère la valeur du tag correspondant à une variable.
    """

    tag = VARIABLE_TAGS.get(variable_name)

    if tag is None:
        return None

    return row.get(tag)


# ============================================================
# 19. INTERPRÉTATION D'UNE CONDITION CROISÉE
# ============================================================

def evaluate_crossed_part(
    row: pd.Series,
    condition: str,
) -> bool:
    """
    Interprète une partie d'une règle croisée.

    Exemples :
        température < 70
        pression > 3
        pH normal
        pompe de circulation arrêtée
        vanne de vapeur ouverte
    """

    condition = normalize_text(condition)

    numeric_patterns = [
        (
            r"temperature\s*(<=|>=|=|<|>)\s*(\d+(?:\.\d+)?)",
            "temperature",
        ),
        (
            r"pression\s*(<=|>=|=|<|>)\s*(\d+(?:\.\d+)?)",
            "pression",
        ),
        (
            r"vide\s*(<=|>=|=|<|>)\s*(\d+(?:\.\d+)?)",
            "vide",
        ),
        (
            r"niveau\s*(<=|>=|=|<|>)\s*(\d+(?:\.\d+)?)",
            "niveau",
        ),
        (
            r"conductivite\s*(<=|>=|=|<|>)\s*(\d+(?:\.\d+)?)",
            "conductivite",
        ),
        (
            r"ph\s*(<=|>=|=|<|>)\s*(\d+(?:\.\d+)?)",
            "ph",
        ),
    ]

    for pattern, variable_name in numeric_patterns:
        match = re.fullmatch(
            pattern,
            condition,
        )

        if match:
            operator = match.group(1)
            threshold = float(match.group(2))

            value = get_variable_value(
                row,
                variable_name,
            )

            return compare_numeric_value(
                value,
                operator,
                threshold,
            )

    if condition == "debit d'acide a 54 % faible":
        value = get_variable_value(
            row,
            "debit_acide_54",
        )
        return compare_numeric_value(
            value,
            "<",
            10,
        )

    if condition == "debit d'acide a 29 % faible":
        value = get_variable_value(
            row,
            "debit_acide_29",
        )
        return compare_numeric_value(
            value,
            "<",
            15,
        )

    if condition == "debit d'acide a 29 % eleve":
        value = get_variable_value(
            row,
            "debit_acide_29",
        )
        return compare_numeric_value(
            value,
            ">",
            28,
        )

    if condition == "debit d'acide a 29 % normal":
        value = get_variable_value(
            row,
            "debit_acide_29",
        )

        if value is None or pd.isna(value):
            return False

        return 15 <= float(value) <= 28

    if condition == "ph normal":
        value = get_variable_value(
            row,
            "ph",
        )

        if value is None or pd.isna(value):
            return False

        return float(value) >= 7

    if condition == "conductivite normale":
        value = get_variable_value(
            row,
            "conductivite",
        )

        if value is None or pd.isna(value):
            return False

        return float(value) <= 20

    if condition == "pompe de circulation arretee":
        value = get_variable_value(
            row,
            "pompe_circulation",
        )

        return compare_text_value(
            value,
            "Arret",
        )

    if condition == "pompe de production arretee":
        value = get_variable_value(
            row,
            "pompe_production",
        )

        return compare_text_value(
            value,
            "Arret",
        )

    if condition == "vanne de vapeur ouverte":
        value = get_variable_value(
            row,
            "vanne_vapeur",
        )

        return compare_text_value(
            value,
            "Ouverte",
        )

    if condition == "vanne de vapeur fermee":
        value = get_variable_value(
            row,
            "vanne_vapeur",
        )

        return compare_text_value(
            value,
            "Fermee",
        )

    raise ValueError(
        f"Partie de règle croisée non reconnue : {condition}"
    )


# ============================================================
# 20. APPLICATION DES RÈGLES CROISÉES
# ============================================================

def apply_crossed_rules(
    global_table: pd.DataFrame,
    crossed_rules: pd.DataFrame,
) -> list[dict]:
    """
    Applique les règles croisées provenant de PostgreSQL.
    """

    occurrences: list[dict] = []

    for rule_index, rule in crossed_rules.iterrows():
        rule_text = str(
            rule["regle_croisee"]
        ).strip()

        rule_id = f"RC{rule_index + 1:02d}"

        normalized_rule = normalize_text(
            rule_text
        )

        rule_parts = re.split(
            r"\s+et\s+",
            normalized_rule,
            maxsplit=1,
        )

        if len(rule_parts) != 2:
            print(
                f"Règle {rule_id} ignorée : "
                f"le connecteur ET est absent."
            )
            continue

        first_condition = rule_parts[0]
        second_condition = rule_parts[1]

        rule_is_valid = True

        for _, measurement in global_table.iterrows():
            try:
                first_result = evaluate_crossed_part(
                    measurement,
                    first_condition,
                )

                second_result = evaluate_crossed_part(
                    measurement,
                    second_condition,
                )

            except ValueError as error:
                print(
                    f"Règle {rule_id} ignorée : {error}"
                )
                rule_is_valid = False
                break

            if first_result and second_result:
                add_occurrence(
                    occurrences=occurrences,
                    timestamp=measurement["timestamp"],
                    rule_id=rule_id,
                    rule_type="Croisée",
                    rule_text=rule_text,
                    interpretation=rule["interpretation"],
                    probable_cause=rule["cause_probable"],
                    criticality=rule["criticite"],
                )

        if not rule_is_valid:
            continue

    print(
        f"{len(occurrences)} occurrences croisées détectées."
    )

    return occurrences


# ============================================================
# 21. REGROUPEMENT DES OCCURRENCES EN ÉVÉNEMENTS
# ============================================================

def group_occurrences_into_events(
    occurrences: list[dict],
) -> pd.DataFrame:
    """
    Regroupe les occurrences successives d'une même règle.
    """

    if not occurrences:
        return pd.DataFrame()

    dataframe = pd.DataFrame(
        occurrences
    )

    dataframe["timestamp"] = pd.to_datetime(
        dataframe["timestamp"],
        errors="coerce",
    )

    dataframe = dataframe.dropna(
        subset=["timestamp"]
    )

    dataframe = dataframe.drop_duplicates(
        subset=["timestamp", "rule_id"]
    )

    dataframe = dataframe.sort_values(
        ["rule_id", "timestamp"]
    ).reset_index(drop=True)

    events: list[dict] = []

    maximum_gap = pd.Timedelta(
        minutes=MAX_GAP_MINUTES,
    )

    sample_interval = pd.Timedelta(
        minutes=SAMPLE_INTERVAL_MINUTES,
    )

    for rule_id, group in dataframe.groupby(
        "rule_id"
    ):
        group = group.sort_values(
            "timestamp"
        ).reset_index(drop=True)

        first_row = group.iloc[0]

        event_start = first_row["timestamp"]
        event_end = first_row["timestamp"]
        occurrence_count = 1

        for index in range(1, len(group)):
            current_row = group.iloc[index]
            current_timestamp = current_row["timestamp"]

            gap = current_timestamp - event_end

            if gap <= maximum_gap:
                event_end = current_timestamp
                occurrence_count += 1

            else:
                duration_minutes = int(
                    (
                        event_end
                        - event_start
                        + sample_interval
                    ).total_seconds()
                    / 60
                )

                events.append(
                    {
                        "debut_anomalie": event_start,
                        "fin_anomalie": event_end,
                        "duree_min": duration_minutes,
                        "nombre_occurrences": occurrence_count,
                        "rule_id": rule_id,
                        "type_regle": first_row["type_regle"],
                        "regle": first_row["regle"],
                        "interpretation": (
                            first_row["interpretation"]
                        ),
                        "cause_probable": (
                            first_row["cause_probable"]
                        ),
                        "criticite": first_row["criticite"],
                    }
                )

                event_start = current_timestamp
                event_end = current_timestamp
                occurrence_count = 1

        duration_minutes = int(
            (
                event_end
                - event_start
                + sample_interval
            ).total_seconds()
            / 60
        )

        events.append(
            {
                "debut_anomalie": event_start,
                "fin_anomalie": event_end,
                "duree_min": duration_minutes,
                "nombre_occurrences": occurrence_count,
                "rule_id": rule_id,
                "type_regle": first_row["type_regle"],
                "regle": first_row["regle"],
                "interpretation": first_row["interpretation"],
                "cause_probable": first_row["cause_probable"],
                "criticite": first_row["criticite"],
            }
        )

    events_dataframe = pd.DataFrame(
        events
    )

    events_dataframe = events_dataframe.sort_values(
        "debut_anomalie"
    ).reset_index(drop=True)

    return events_dataframe


# ============================================================
# 22. ENREGISTREMENT DANS POSTGRESQL
# ============================================================

def save_anomaly_events(
    engine: Engine,
    events: pd.DataFrame,
) -> None:
    """
    Enregistre les événements dans anomalies_detectees.
    """

    columns = [
        "debut_anomalie",
        "fin_anomalie",
        "duree_min",
        "nombre_occurrences",
        "rule_id",
        "type_regle",
        "regle",
        "interpretation",
        "cause_probable",
        "criticite",
    ]

    if events.empty:
        empty_dataframe = pd.DataFrame(
            columns=columns
        )

        empty_dataframe.to_sql(
            "anomalies_detectees",
            engine,
            if_exists="replace",
            index=False,
        )

        print(
            "Aucun événement d'anomalie détecté."
        )

        return

    events[columns].to_sql(
        "anomalies_detectees",
        engine,
        if_exists="replace",
        index=False,
    )

    print(
        f"{len(events)} événements enregistrés "
        "dans anomalies_detectees."
    )


# ============================================================
# 23. AFFICHAGE DU RÉSUMÉ
# ============================================================

def display_summary(
    occurrences: list[dict],
    events: pd.DataFrame,
) -> None:
    """
    Affiche le résumé de la détection dans le terminal.
    """

    print("\n====================================")
    print("RÉSUMÉ DE LA DÉTECTION")
    print("====================================")

    print(
        f"Occurrences anormales : {len(occurrences)}"
    )

    print(
        f"Événements regroupés : {len(events)}"
    )

    if events.empty:
        return

    summary = (
        events.groupby(
            ["type_regle", "criticite"],
            dropna=False,
        )
        .size()
        .reset_index(name="nombre_evenements")
    )

    print("\nÉvénements par type et criticité :")
    print(
        summary.to_string(index=False)
    )


# ============================================================
# 24. PROGRAMME PRINCIPAL
# ============================================================

def main() -> None:
    engine = None

    try:
        print("Début de la détection des anomalies.")

        # Étape 1 : connexion PostgreSQL
        engine = create_postgresql_engine()

        print("Connexion PostgreSQL réussie.")

        # Étape 2 : vérification des tables
        check_required_tables(engine)

        # Étape 3 : lecture des données
        dcs_measurements = load_dcs_measurements(
            engine
        )

        scada_states = load_scada_states(
            engine
        )

        simple_rules = load_simple_rules(
            engine
        )

        crossed_rules = load_crossed_rules(
            engine
        )

        # Étape 4 : transformation des données
        dcs_table = create_dcs_table(
            dcs_measurements
        )

        scada_table = create_scada_table(
            scada_states
        )

        global_table = create_global_table(
            dcs_table,
            scada_table,
        )

        print(
            f"{len(global_table)} instants préparés "
            "pour l'analyse."
        )

        # Étape 5 : règles simples
        simple_occurrences = apply_simple_rules(
            global_table,
            simple_rules,
        )

        # Étape 6 : règles croisées
        crossed_occurrences = apply_crossed_rules(
            global_table,
            crossed_rules,
        )

        # Étape 7 : fusion des résultats
        all_occurrences = (
            simple_occurrences
            + crossed_occurrences
        )

        # Étape 8 : regroupement
        events = group_occurrences_into_events(
            all_occurrences
        )

        # Étape 9 : enregistrement
        save_anomaly_events(
            engine,
            events,
        )

        # Étape 10 : résumé
        display_summary(
            all_occurrences,
            events,
        )

    except Exception as error:
        print(
            f"\nErreur pendant la détection : {error}"
        )

    finally:
        if engine is not None:
            engine.dispose()

        print("\nConnexion PostgreSQL fermée.")


if __name__ == "__main__":
    main()