# Projet de Supervision CAP — OCP

Plateforme de supervision de l'unité CAP : une API FastAPI adossée
à PostgreSQL et une interface Streamlit.

- **Base de données** — Neon (PostgreSQL serverless)
- **API** — Render (service web)
- **Interface** — Streamlit Community Cloud

---

## Structure du dépôt

```
supervision-cap-ocp
├─ api
│  └─ main.py                 API FastAPI (8 endpoints de lecture)
├─ app
│  ├─ _auth.py               garde d'authentification partagée
│  ├─ home.py                point d'entrée Streamlit (connexion)
│  ├─ assets
│  │  ├─ background.jpg
│  │  └─ ocp_logo.png
│  └─ pages                  pages du tableau de bord
│     ├─ 1_Mesures.py        (le dossier doit rester en minuscules :
│     ├─ 2_Alarmes.py         Streamlit ne reconnaît que « pages »,
│     ├─ 3_Anomalies.py       et Linux distingue la casse)
│     └─ 4_Arrets.py
├─ common
│  └─ db.py                  configuration unique de la connexion
├─ data
│  ├─ *.xlsx                 sources brutes
│  └─ cleaned
│     └─ *.xlsx              sources nettoyées (importées en base)
├─ scripts
│  ├─ analyse_data.py        exploration des fichiers Excel
│  ├─ clean_data.py          data/*.xlsx  ->  data/cleaned/*.xlsx
│  ├─ import_postgresql.py   data/cleaned/*.xlsx  ->  PostgreSQL
│  └─ detect_anomalies.py    règles métier  ->  anomalies_detectees
├─ .env.example              modèle de configuration
├─ .python-version
├─ render.yaml               Blueprint Render (service API)
└─ requirements.txt
```

---

## Installation locale

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

Copier le modèle de configuration et le compléter :

```bash
copy .env.example .env          # Windows
# cp .env.example .env          # macOS / Linux
```

`.env` n'est jamais versionné. Variables attendues :

| Variable              | Rôle                                                | Requis |
| --------------------- | --------------------------------------------------- | ------ |
| `DATABASE_URL`        | connexion PostgreSQL directe (scripts)               | oui    |
| `DATABASE_URL_POOLED` | connexion via le pooler Neon (API)                   | non    |
| `CORS_ORIGINS`        | origines autorisées, séparées par des virgules       | non    |
| `API_URL`             | URL de l'API vue par Streamlit                       | non    |
| `APP_USER_EMAIL`      | identifiant de connexion à l'interface               | non    |
| `APP_USER_PASSWORD`   | mot de passe de connexion à l'interface              | non    |

---

## Lancer le projet en local

Deux processus, dans deux terminaux séparés.

**1. API FastAPI**

```bash
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

- API : http://127.0.0.1:8000
- Documentation interactive : http://127.0.0.1:8000/docs
- Vivacité : http://127.0.0.1:8000/health
- Base accessible : http://127.0.0.1:8000/health/db

La commande se lance depuis la racine du dépôt : c'est ce qui rend
le paquet `common` importable.

**2. Interface Streamlit**

```bash
streamlit run app/home.py
```

Interface : http://localhost:8501

L'interface interroge l'API : démarrer l'API en premier.

---

## Pipeline de données

À exécuter dans l'ordre, ponctuellement. Ces scripts ne sont pas
appelés au démarrage de l'application.

```bash
# 1. Nettoyage des fichiers Excel  ->  data/cleaned/
python scripts/clean_data.py

# 2. Import en base + création des index
python scripts/import_postgresql.py

# 3. Détection des anomalies  ->  table anomalies_detectees
python scripts/detect_anomalies.py
```


Tables produites : `mesures_dcs`, `etats_scada`, `alarmes`,
`arrets_cap`, `laboratoire`, `regles_simples`, `regles_croisees`,
puis `anomalies_detectees`.

---

## Endpoints de l'API

| Méthode | Chemin             | Description                          |
| ------- | ------------------ | ------------------------------------ |
| GET     | `/`                | message de disponibilité             |
| GET     | `/health`          | vivacité (ne touche pas à la base)   |
| GET     | `/health/db`       | disponibilité de la base (SELECT 1)  |
| GET     | `/mesures`         | mesures DCS, filtre `?tag=`          |
| GET     | `/mesures/{tag}`   | mesures d'un tag                     |
| GET     | `/alarmes`         | alarmes                              |
| GET     | `/arrets`          | arrêts de l'unité                    |
| GET     | `/anomalies`       | anomalies détectées                  |
| GET     | `/laboratoire`     | analyses laboratoire                 |
| GET     | `/etats-scada`     | états SCADA                          |

