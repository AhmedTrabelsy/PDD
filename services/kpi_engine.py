# services/kpi_engine.py
# ─────────────────────────────────────────────────────────────
# Moteur de calcul KPI. Toutes les formules sont ici.
# Les DataFrames reçus ont des colonnes datetime NAIVE
# (heure locale Tunis, sans tzinfo) grâce à database.py.
# ─────────────────────────────────────────────────────────────

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytz

TZ_LOCAL = pytz.timezone("Africa/Tunis")


def _now_local() -> pd.Timestamp:
    import datetime as _dt
    return pd.Timestamp(_dt.datetime.now(TZ_LOCAL).replace(tzinfo=None))


def _debut_semaine_courante() -> date:
    today = _now_local().date()
    return today - timedelta(days=today.weekday())


# ════════════════════════════════════════════════════════════
#  KPI-01 : VÉLOCITÉ
# ════════════════════════════════════════════════════════════

def velocite_hebdomadaire(df_taches: pd.DataFrame) -> pd.DataFrame:
    if df_taches.empty:
        return pd.DataFrame(columns=["semaine", "nb_terminees", "score_complexite"])
    done = df_taches[df_taches["statut"] == "TERMINE"].copy()
    if done.empty:
        return pd.DataFrame(columns=["semaine", "nb_terminees", "score_complexite"])
    done["semaine"] = done["cree_le"].dt.to_period("W").dt.start_time.dt.date
    return (
        done.groupby("semaine")
        .agg(nb_terminees=("tache_id", "count"), score_complexite=("complexite", "sum"))
        .reset_index()
        .sort_values("semaine")
    )


def velocite_semaine_courante(df_taches: pd.DataFrame) -> int:
    if df_taches.empty:
        return 0
    debut = _debut_semaine_courante()
    fin = debut + timedelta(days=6)
    mask = (
        (df_taches["statut"] == "TERMINE")
        & (df_taches["cree_le"].dt.date >= debut)
        & (df_taches["cree_le"].dt.date <= fin)
    )
    return int(mask.sum())


def velocite_semaine_precedente(df_taches: pd.DataFrame) -> int:
    if df_taches.empty:
        return 0
    debut = _debut_semaine_courante() - timedelta(days=7)
    fin = debut + timedelta(days=6)
    mask = (
        (df_taches["statut"] == "TERMINE")
        & (df_taches["cree_le"].dt.date >= debut)
        & (df_taches["cree_le"].dt.date <= fin)
    )
    return int(mask.sum())


# ════════════════════════════════════════════════════════════
#  KPI-02 : LEAD TIME
# ════════════════════════════════════════════════════════════

def lead_time_moyen(df_taches: pd.DataFrame, jours: int = 28) -> float:
    if df_taches.empty:
        return 0.0
    cutoff = _now_local() - pd.Timedelta(days=jours)
    done = df_taches[
        (df_taches["statut"] == "TERMINE")
        & df_taches["cloture_le"].notna()
        & (df_taches["cree_le"] >= cutoff)
    ].copy()
    if done.empty:
        return 0.0
    done["duree_h"] = (done["cloture_le"] - done["cree_le"]
                       ).dt.total_seconds() / 3600
    return round(float(done["duree_h"].mean()), 1)


def lead_time_par_categorie(df_taches: pd.DataFrame) -> pd.DataFrame:
    if df_taches.empty:
        return pd.DataFrame()
    done = df_taches[
        (df_taches["statut"] == "TERMINE") & df_taches["cloture_le"].notna()
    ].copy()
    if done.empty:
        return pd.DataFrame()
    done["duree_h"] = (done["cloture_le"] - done["cree_le"]
                       ).dt.total_seconds() / 3600
    return (
        done.groupby("categorie")["duree_h"]
        .mean()
        .round(1)
        .reset_index()
        .rename(columns={"duree_h": "lead_time_h"})
        .sort_values("lead_time_h")
    )


# ════════════════════════════════════════════════════════════
#  KPI-03 : SCORE DE COMPLEXITÉ
# ════════════════════════════════════════════════════════════

def score_complexite_semaine(df_taches: pd.DataFrame) -> int:
    if df_taches.empty:
        return 0
    debut = _debut_semaine_courante()
    fin = debut + timedelta(days=6)
    mask = (
        (df_taches["statut"] == "TERMINE")
        & (df_taches["cree_le"].dt.date >= debut)
        & (df_taches["cree_le"].dt.date <= fin)
    )
    return int(df_taches.loc[mask, "complexite"].sum())


# ════════════════════════════════════════════════════════════
#  KPI-04 : INDICE DE PONCTUALITÉ
# ─────────────────────────────────────────────────────────────
# Formule : 100 − écart-type des heures d'arrivée (en minutes).
# Les heures stockées sont en heure locale Tunis (naive),
# donc l'heure lue directement est correcte.
# ════════════════════════════════════════════════════════════

def indice_ponctualite(df_presence: pd.DataFrame) -> float:
    if df_presence.empty:
        return 100.0
    entrees = df_presence[df_presence["type_evenement"] == "ENTREE"].copy()
    if len(entrees) < 2:
        return 100.0
    # heure en minutes depuis minuit — les datetime sont naifs heure Tunis
    entrees["heure_min"] = entrees["horodatage"].dt.hour * \
        60 + entrees["horodatage"].dt.minute
    std = float(entrees["heure_min"].std())
    return round(max(0.0, 100.0 - std), 1)


def heures_presence_par_jour(df_presence: pd.DataFrame) -> pd.DataFrame:
    """Apparie ENTREE/SORTIE pour calculer les heures présentes par jour."""
    if df_presence.empty:
        return pd.DataFrame(columns=["date_jour", "heures_presentes"])
    rows = []
    for jour, groupe in df_presence.groupby("date_jour"):
        entrees = sorted(groupe[groupe["type_evenement"]
                         == "ENTREE"]["horodatage"].tolist())
        sorties = sorted(groupe[groupe["type_evenement"]
                         == "SORTIE"]["horodatage"].tolist())
        total_sec = 0.0
        sorties_restantes = list(sorties)
        for e in entrees:
            apres = [s for s in sorties_restantes if s > e]
            if apres:
                total_sec += (apres[0] - e).total_seconds()
                sorties_restantes.remove(apres[0])
        rows.append(
            {"date_jour": jour, "heures_presentes": round(total_sec / 3600, 2)})
    return pd.DataFrame(rows).sort_values("date_jour")


# ════════════════════════════════════════════════════════════
#  KPI-05 : TAUX D'EFFICACITÉ
# ════════════════════════════════════════════════════════════

def taux_efficacite(df_taches: pd.DataFrame, df_presence: pd.DataFrame) -> float:
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
    done["duree_h"] = (done["cloture_le"] - done["cree_le"]
                       ).dt.total_seconds() / 3600
    return round(min((done["duree_h"].sum() / heures_totales) * 100, 100.0), 1)


# ════════════════════════════════════════════════════════════
#  KPI-06 : TAUX DE BLOCAGE
# ════════════════════════════════════════════════════════════

def taux_blocage(df_taches: pd.DataFrame) -> float:
    if df_taches.empty:
        return 0.0
    actives = df_taches[df_taches["statut"].isin(
        ["A_FAIRE", "EN_COURS", "BLOQUE"])]
    if actives.empty:
        return 0.0
    return round(((actives["statut"] == "BLOQUE").sum() / len(actives)) * 100, 1)


def taches_bloquees(df_taches: pd.DataFrame) -> pd.DataFrame:
    if df_taches.empty:
        return pd.DataFrame()
    cols = ["tache_id", "titre", "zone_usine",
            "categorie", "raison_blocage", "cree_le"]
    # inclure projet_nom si disponible
    if "projet_nom" in df_taches.columns:
        cols.append("projet_nom")
    return df_taches[df_taches["statut"] == "BLOQUE"][cols]


# ════════════════════════════════════════════════════════════
#  ANALYSES PAR PROJET
# ════════════════════════════════════════════════════════════

def temps_par_projet(df_taches: pd.DataFrame) -> pd.DataFrame:
    """Heures cumulées et nb de tâches terminées par projet."""
    if df_taches.empty or "projet_nom" not in df_taches.columns:
        return pd.DataFrame()
    done = df_taches[
        (df_taches["statut"] == "TERMINE")
        & df_taches["cloture_le"].notna()
        & df_taches["projet_nom"].notna()
    ].copy()
    if done.empty:
        return pd.DataFrame()
    done["duree_h"] = (done["cloture_le"] - done["cree_le"]
                       ).dt.total_seconds() / 3600
    return (
        done.groupby("projet_nom")
        .agg(heures=("duree_h", "sum"), nb_taches=("tache_id", "count"),
             score_cx=("complexite", "sum"))
        .round({"heures": 1})
        .reset_index()
        .sort_values("heures", ascending=False)
    )


def velocite_par_projet(df_taches: pd.DataFrame) -> pd.DataFrame:
    """Nombre de tâches par projet et par semaine."""
    if df_taches.empty or "projet_nom" not in df_taches.columns:
        return pd.DataFrame()
    done = df_taches[
        (df_taches["statut"] == "TERMINE") & df_taches["projet_nom"].notna()
    ].copy()
    if done.empty:
        return pd.DataFrame()
    done["semaine"] = done["cree_le"].dt.to_period("W").dt.start_time.dt.date
    return (
        done.groupby(["semaine", "projet_nom"])
        .size()
        .reset_index(name="nb_taches")
        .sort_values("semaine")
    )


# ════════════════════════════════════════════════════════════
#  ANALYSES COMPLÉMENTAIRES
# ════════════════════════════════════════════════════════════

def repartition_par_zone(df_taches: pd.DataFrame) -> pd.DataFrame:
    if df_taches.empty:
        return pd.DataFrame()
    return (
        df_taches.groupby(["zone_usine", "statut"])
        .size()
        .reset_index(name="nb_taches")
    )


def repartition_par_categorie(df_taches: pd.DataFrame) -> pd.DataFrame:
    if df_taches.empty:
        return pd.DataFrame()
    done = df_taches[df_taches["statut"] == "TERMINE"]
    if done.empty:
        return pd.DataFrame()
    return (
        done.groupby("categorie")
        .agg(nb=("tache_id", "count"), score=("complexite", "sum"))
        .reset_index()
        .sort_values("nb", ascending=False)
    )


def heatmap_zone_semaine(df_taches: pd.DataFrame) -> pd.DataFrame:
    if df_taches.empty:
        return pd.DataFrame()
    JOURS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    df = df_taches.copy()
    df["jour_semaine"] = df["cree_le"].dt.dayofweek.map(dict(enumerate(JOURS)))
    return (
        df.groupby(["zone_usine", "jour_semaine"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=JOURS, fill_value=0)
    )


def delta_pct(valeur_actuelle: float | int, valeur_precedente: float | int) -> str:
    if valeur_precedente == 0:
        return "N/A"
    diff = ((valeur_actuelle - valeur_precedente) / valeur_precedente) * 100
    return f"{'+'if diff >= 0 else ''}{round(diff, 1)}%"
