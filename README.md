# 📊 PPD — Tableau de Bord de Performance

Application Streamlit de suivi de performance.
Hébergement base de données sur Supabase (PostgreSQL), déploiement sur Streamlit Community Cloud.

---

## 🗂️ Structure du projet

```
ppd-app/
├── app.py                      # Point d'entrée — authentification PIN + routeur
├── views/
│   ├── __init__.py
│   ├── employee.py             # Vue Employé (pointage, tâches, notes, analytics)
│   └── manager.py              # Vue Manager (KPI, graphiques, OKR, PDF)
├── services/
│   ├── __init__.py
│   ├── database.py             # Toutes les interactions Supabase
│   ├── kpi_engine.py           # Calcul des 6 KPIs (formules exactes)
│   └── pdf_export.py           # Génération du rapport PDF hebdomadaire
├── components/
│   ├── __init__.py
│   └── charts.py               # Graphiques Plotly réutilisables
├── .streamlit/
│   ├── config.toml             # Thème sombre + config serveur
│   └── secrets.toml            # 🔒 NE PAS COMMITTER (voir .gitignore)
├── supabase_schema.sql         # Script SQL complet à exécuter dans Supabase
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🚀 Déploiement — Étape par Étape

### ÉTAPE 1 — Créer la base de données Supabase

1. Aller sur [supabase.com](https://supabase.com) → créer un compte gratuit
2. Créer un nouveau projet (choisir une région proche, ex: `eu-west-1`)
3. Attendre l'initialisation (~2 minutes)
4. Aller dans **SQL Editor** → **New Query**
5. Copier-coller l'intégralité de `supabase_schema.sql` → cliquer **Run**
6. Vérifier que les 4 tables sont créées dans **Table Editor** :
   - `journal_presence`
   - `journal_taches`
   - `notes_journalieres`
   - `objectifs`

### ÉTAPE 2 — Récupérer les credentials Supabase

1. Dans ton projet Supabase → **Settings** → **API**
2. Copier :
   - **Project URL** → ressemble à `https://abcdefgh.supabase.co`
   - **anon / public key** → longue chaîne JWT

### ÉTAPE 3 — Préparer le dépôt GitHub

```bash
# Cloner ou initialiser le repo
git init ppd-app
cd ppd-app

# Copier tous les fichiers du projet ici
# VÉRIFIER que .gitignore est présent avant de faire git add

git add .
git commit -m "feat: initial PPD deployment"

# Créer un repo sur GitHub (privé recommandé)
git remote add origin https://github.com/TON_USERNAME/ppd-app.git
git push -u origin main
```

> ⚠️ **Ne jamais committer `.streamlit/secrets.toml`** — le `.gitignore` l'exclut automatiquement.

### ÉTAPE 4 — Déployer sur Streamlit Community Cloud

1. Aller sur [share.streamlit.io](https://share.streamlit.io) → se connecter avec GitHub
2. Cliquer **New app**
3. Sélectionner ton repo `ppd-app`, branche `main`, fichier `app.py`
4. Cliquer **Advanced settings** → **Secrets**
5. Coller le contenu suivant (en remplaçant les valeurs) :

```toml
[supabase]
url = "https://VOTRE_ID_PROJET.supabase.co"
key = "VOTRE_ANON_KEY_SUPABASE"

[auth]
pin_employe = "1234"
pin_manager = "0000"
```

6. Cliquer **Deploy** → attendre ~2 minutes
7. Ton app est disponible sur `https://ppd-app.streamlit.app` (ou URL similaire)

---

## 🔑 Système d'authentification

| Rôle     | PIN par défaut | Accès |
|----------|----------------|-------|
| Employé  | `1234`         | Lecture + Écriture |
| Manager  | `0000`         | Lecture seule |

> Modifier les PIN dans les **Secrets** Streamlit (jamais dans le code).

---

## 📊 KPIs calculés

| Code   | Indicateur               | Formule |
|--------|--------------------------|---------|
| KPI-01 | Vélocité hebdomadaire    | `COUNT(tâches TERMINE, semaine courante)` |
| KPI-02 | Lead Time moyen          | `MEAN(cloture_le - cree_le)` en heures |
| KPI-03 | Score de complexité      | `SUM(complexite)` des tâches terminées cette semaine |
| KPI-04 | Indice de ponctualité    | `100 − STD_DEV(heures_arrivée en min)` |
| KPI-05 | Taux d'efficacité        | `(heures_taches / heures_présence) × 100` |
| KPI-06 | Taux de blocage          | `(nb_BLOQUE / nb_actives) × 100` |

---

## 🛠️ Développement local

```bash
# Cloner le repo
git clone https://github.com/TON_USERNAME/ppd-app.git
cd ppd-app

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
# .venv\Scripts\activate           # Windows

# Installer les dépendances
pip install -r requirements.txt

# Créer le fichier secrets local
mkdir -p .streamlit
cat > .streamlit/secrets.toml << 'EOF'
[supabase]
url = "https://VOTRE_ID_PROJET.supabase.co"
key = "VOTRE_ANON_KEY_SUPABASE"

[auth]
pin_employe = "1234"
pin_manager = "0000"
EOF

# Lancer l'application
streamlit run app.py
```

L'app sera disponible sur `http://localhost:8501`

---

## 🔒 Sécurité

- Les credentials Supabase ne sont jamais dans le code, uniquement dans les Secrets Streamlit
- Le fichier `secrets.toml` est dans `.gitignore`
- La Vue Manager est en lecture seule (aucun bouton d'écriture)
- Les PIN sont configurables sans redéploiement (modification dans Streamlit Secrets)

---

## 📦 Technologies

| Composant   | Technologie              |
|-------------|--------------------------|
| Frontend    | Python 3.11 + Streamlit  |
| Base de données | Supabase (PostgreSQL) |
| Graphiques  | Plotly Express           |
| Export PDF  | fpdf2                    |
| Déploiement | Streamlit Community Cloud |
| CI/CD       | GitHub (push = redéployé) |

---

*PPD v2.0*
