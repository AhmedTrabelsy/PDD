# services/kpi_engine.py
# ─────────────────────────────────────────────────────────────
# Moteur de calcul des KPI.
# Toutes les formules sont définies ici et nulle part ailleurs.
# Chaque fonction prend un DataFrame (déjà chargé) et retourne
# une valeur scalaire ou un DataFrame résumé.
# ─────────────────────────────────────────────────────────────

from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import date, timedelta


# ════════════════════════════════════════════════════════════
#  KPI-01 : VÉLOCITÉ — nombre de tâches terminées / semaine
# ════════════════════════════════════════════════════════════

def velocite_hebdomadaire(df_taches: pd.DataFrame) -> pd.DataFrame:
    """
    Retourne un DataFrame avec une ligne par semaine ISO et
    les colonnes : semaine, nb_terminees, score_complexite.
    """
    if df_taches.empty:
        return pd.DataFrame(columns=["semaine", "nb_terminees", "score_complexite"])

    done = df_taches[df_taches["statut"] == "TERMINE"].copy()
    if done.empty:
        return pd.DataFrame(columns=["semaine", "nb_terminees", "score_complexite"])

    done["semaine"] = done["cree_le"].dt.to_period("W").dt.start_time.dt.date
    agg = (
        done.groupby("semaine")
        .agg(nb_terminees=("tache_id", "count"), score_complexite=("complexite", "sum"))
        .reset_index()
        .sort_values("semaine")
    )
    return agg


def velocite_semaine_courante(df_taches: pd.DataFrame) -> int:
    """Nombre de tâches terminées cette semaine ISO."""
    if df_taches.empty:
        return 0
    debut = date.today() - timedelta(days=date.today().weekday())
    fin   = debut + timedelta(days=6)
    mask  = (
        (df_taches["statut"] == "TERMINE") &
        (df_taches["cree_le"].dt.date >= debut) &
        (df_taches["cree_le"].dt.date <= fin)
    )
    return int(mask.sum())


def velocite_semaine_precedente(df_taches: pd.DataFrame) -> int:
    """Nombre de tâches terminées la semaine précédente."""
    if df_taches.empty:
        return 0
    debut = date.today() - timedelta(days=date.today().weekday() + 7)
    fin   = debut + timedelta(days=6)
    mask  = (
        (df_taches["statut"] == "TERMINE") &
        (df_taches["cree_le"].dt.date >= debut) &
        (df_taches["cree_le"].dt.date <= fin)
    )
    return int(mask.sum())


# ════════════════════════════════════════════════════════════
#  KPI-02 : LEAD TIME — durée moyenne de résolution (en heures)
# ════════════════════════════════════════════════════════════

def lead_time_moyen(df_taches: pd.DataFrame, jours: int = 28) -> float:
    """
    Durée moyenne (en heures) entre création et clôture,
    sur les `jours` derniers jours. Arrondi à 1 décimale.
    """
    if df_taches.empty:
        return 0.0
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=jours)
    done = df_taches[
        (df_taches["statut"] == "TERMINE") &
        (df_taches["cloture_le"].notna()) &
        (df_taches["cree_le"] >= cutoff)
    ].copy()
    if done.empty:
        return 0.0
    done["duree_h"] = (done["cloture_le"] - done["cree_le"]).dt.total_seconds() / 3600
    return round(float(done["duree_h"].mean()), 1)


def lead_time_par_categorie(df_taches: pd.DataFrame) -> pd.DataFrame:
    """Lead time moyen par catégorie de tâche."""
    if df_taches.empty:
        return pd.DataFrame()
    done = df_taches[
        (df_taches["statut"] == "TERMINE") & df_taches["cloture_le"].notna()
    ].copy()
    if done.empty:
        return pd.DataFrame()
    done["duree_h"] = (done["cloture_le"] - done["cree_le"]).dt.total_seconds() / 3600
    return (
        done.groupby("categorie")["duree_h"]
        .mean()
        .round(1)
        .reset_index()
        .rename(columns={"duree_h": "lead_time_h"})
        .sort_values("lead_time_h")
    )


# ════════════════════════════════════════════════════════════
#  KPI-03 : SCORE DE COMPLEXITÉ PONDÉRÉ (semaine courante)
# ════════════════════════════════════════════════════════════

def score_complexite_semaine(df_taches: pd.DataFrame) -> int:
    """Somme des complexités des tâches terminées cette semaine."""
    if df_taches.empty:
        return 0
    debut = date.today() - timedelta(days=date.today().weekday())
    fin   = debut + timedelta(days=6)
    mask  = (
        (df_taches["statut"] == "TERMINE") &
        (df_taches["cree_le"].dt.date >= debut) &
        (df_taches["cree_le"].dt.date <= fin)
    )
    return int(df_taches.loc[mask, "complexite"].sum())


# ════════════════════════════════════════════════════════════
#  KPI-04 : INDICE DE PONCTUALITÉ
# ════════════════════════════════════════════════════════════

def indice_ponctualite(df_presence: pd.DataFrame) -> float:
    """
    100 − (écart-type des heures d'arrivée en minutes).
    Retourne un % entre 0 et 100. Un score élevé = horaires stables.
    """
    if df_presence.empty:
        return 100.0
    entrees = df_presence[df_presence["type_evenement"] == "ENTREE"].copy()
    if len(entrees) < 2:
        return 100.0
    entrees["heure_min"] = (
        entrees["horodatage"].dt.hour * 60 + entrees["horodatage"].dt.minute
    )
    std = entrees["heure_min"].std()
    score = max(0.0, 100.0 - float(std))
    return round(score, 1)


def heures_presence_par_jour(df_presence: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les heures de présence par jour en appariant ENTREE/SORTIE.
    Retourne un DataFrame avec les colonnes : date_jour, heures_presentes.
    """
    if df_presence.empty:
        return pd.DataFrame(columns=["date_jour", "heures_presentes"])

    rows = []
    for jour, groupe in df_presence.groupby("date_jour"):
        entrees = sorted(
            groupe[groupe["type_evenement"] == "ENTREE"]["horodatage"].tolist()
        )
        sorties = sorted(
            groupe[groupe["type_evenement"] == "SORTIE"]["horodatage"].tolist()
        )
        total_sec = 0.0
        for e in entrees:
            # Cherche la première sortie après cette entrée
            sorties_apres = [s for s in sorties if s > e]
            if sorties_apres:
                total_sec += (sorties_apres[0] - e).total_seconds()
                sorties.remove(sorties_apres[0])
        rows.append({"date_jour": jour, "heures_presentes": round(total_sec / 3600, 2)})

    return pd.DataFrame(rows).sort_values("date_jour")


# ════════════════════════════════════════════════════════════
#  KPI-05 : TAUX D'EFFICACITÉ OPÉRATIONNELLE
# ════════════════════════════════════════════════════════════

def taux_efficacite(df_taches: pd.DataFrame, df_presence: pd.DataFrame) -> float:
    """
    (heures_taches_terminees / heures_totales_pointées) × 100
    Retourne un % arrondi à 1 décimale.
    """
    presence = heures_presence_par_jour(df_presence)
    if presence.empty or df_taches.empty:
        return 0.0

    heures_totales = presence["heures_presentes"].sum()
    if heures_totales == 0:
        return 0.0

    done = df_taches[
        (df_taches["statut"] == "TERMINE") & df_taches["cloture_le"].notna()
    ].copy()
    if done.empty:
        return 0.0

    done["duree_h"] = (done["cloture_le"] - done["cree_le"]).dt.total_seconds() / 3600
    heures_taches = done["duree_h"].sum()
    ratio = (heures_taches / heures_totales) * 100
    return round(min(ratio, 100.0), 1)


# ════════════════════════════════════════════════════════════
#  KPI-06 : TAUX DE BLOCAGE
# ════════════════════════════════════════════════════════════

def taux_blocage(df_taches: pd.DataFrame) -> float:
    """% de tâches actuellement en statut BLOQUE."""
    if df_taches.empty:
        return 0.0
    actives = df_taches[df_taches["statut"].isin(["A_FAIRE", "EN_COURS", "BLOQUE"])]
    if actives.empty:
        return 0.0
    nb_bloques = (actives["statut"] == "BLOQUE").sum()
    return round((nb_bloques / len(actives)) * 100, 1)


def taches_bloquees(df_taches: pd.DataFrame) -> pd.DataFrame:
    """Retourne uniquement les tâches bloquées avec leur raison."""
    if df_taches.empty:
        return pd.DataFrame()
    return df_taches[df_taches["statut"] == "BLOQUE"][
        ["tache_id", "titre", "zone_usine", "categorie", "raison_blocage", "cree_le"]
    ]


# ════════════════════════════════════════════════════════════
#  ANALYSES COMPLÉMENTAIRES
# ════════════════════════════════════════════════════════════

def repartition_par_zone(df_taches: pd.DataFrame) -> pd.DataFrame:
    """Nombre de tâches par zone et par statut."""
    if df_taches.empty:
        return pd.DataFrame()
    return (
        df_taches.groupby(["zone_usine", "statut"])
        .size()
        .reset_index(name="nb_taches")
    )


def repartition_par_categorie(df_taches: pd.DataFrame) -> pd.DataFrame:
    """Nombre de tâches terminées par catégorie."""
    if df_taches.empty:
        return pd.DataFrame()
    done = df_taches[df_taches["statut"] == "TERMINE"]
    return (
        done.groupby("categorie")
        .agg(nb=("tache_id", "count"), score=("complexite", "sum"))
        .reset_index()
        .sort_values("nb", ascending=False)
    )


def heatmap_zone_semaine(df_taches: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrame pivot : zones × jours de semaine, valeur = nb de tâches.
    Utilisé pour la heatmap de la vue manager.
    """
    if df_taches.empty:
        return pd.DataFrame()

    JOURS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    df = df_taches.copy()
    df["jour_semaine"] = df["cree_le"].dt.dayofweek.map(dict(enumerate(JOURS)))

    pivot = (
        df.groupby(["zone_usine", "jour_semaine"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=JOURS, fill_value=0)
    )
    return pivot


def delta_pct(valeur_actuelle: float | int, valeur_precedente: float | int) -> str:
    """Retourne une chaîne '+X%' ou '−X%' pour affichage dans st.metric."""
    if valeur_precedente == 0:
        return "N/A"
    diff = ((valeur_actuelle - valeur_precedente) / valeur_precedente) * 100
    signe = "+" if diff >= 0 else ""
    return f"{signe}{round(diff, 1)}%"
