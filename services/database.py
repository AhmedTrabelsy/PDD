# services/database.py
# ─────────────────────────────────────────────────────────────
# Couche d'accès aux données.
#
# RÈGLE TIMEZONE (définitive) :
#   • On stocke en UTC dans Supabase (TIMESTAMPTZ).
#   • On NE touche JAMAIS au timezone dans cette couche.
#   • Les colonnes TIMESTAMPTZ arrivent comme strings ISO avec
#     offset (+00:00). On les parse en UTC-aware, puis on
#     convertit en Africa/Tunis UNIQUEMENT pour l'affichage
#     (tz_localize(None) en fin = naive local pour Streamlit).
#   • Les colonnes DATE (objectifs, notes) ne sont PAS des
#     timestamps → parse direct sans aucune conversion TZ.
# ─────────────────────────────────────────────────────────────

from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd
import pytz
import streamlit as st
from supabase import Client, create_client

TZ_LOCAL = pytz.timezone("Africa/Tunis")


def _utc_to_local(series: pd.Series) -> pd.Series:
    """Parse une série de strings UTC en datetime naive heure locale (Tunis)."""
    s = pd.to_datetime(series, utc=True, errors="coerce")
    return s.dt.tz_convert(TZ_LOCAL).dt.tz_localize(None)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_local() -> date:
    """Date locale à Tunis (pas forcement == date UTC si proche de minuit)."""
    return datetime.now(TZ_LOCAL).date()


# ── Client Supabase (singleton) ───────────────────────────────
@st.cache_resource(show_spinner=False)
def get_client() -> Client:
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"],
    )


# ════════════════════════════════════════════════════════════
#  PRÉSENCE
# ════════════════════════════════════════════════════════════

def pointer_entree(zone: str | None = None, note: str | None = None) -> dict:
    db = get_client()
    now = datetime.now(timezone.utc)
    payload = {
        "type_evenement": "ENTREE",
        "horodatage": now.isoformat(),
        # date_jour = date locale de Tunis au moment du clic
        "date_jour": datetime.now(TZ_LOCAL).date().isoformat(),
        "zone_usine": zone,
        "note": note,
    }
    res = db.table("journal_presence").insert(payload).execute()
    return res.data[0] if res.data else {}


def pointer_sortie(zone: str | None = None, note: str | None = None) -> dict:
    db = get_client()
    payload = {
        "type_evenement": "SORTIE",
        "horodatage": datetime.now(timezone.utc).isoformat(),
        "date_jour": datetime.now(TZ_LOCAL).date().isoformat(),
        "zone_usine": zone,
        "note": note,
    }
    res = db.table("journal_presence").insert(payload).execute()
    return res.data[0] if res.data else {}


def get_presence(date_debut: date, date_fin: date) -> pd.DataFrame:
    db = get_client()
    res = (
        db.table("journal_presence")
        .select("*")
        .gte("date_jour", date_debut.isoformat())
        .lte("date_jour", date_fin.isoformat())
        .order("horodatage")
        .execute()
    )
    if not res.data:
        return pd.DataFrame()
    df = pd.DataFrame(res.data)
    df["horodatage"] = _utc_to_local(df["horodatage"])   # naive, heure Tunis
    df["date_jour"]  = pd.to_datetime(df["date_jour"]).dt.date
    return df


def get_dernier_evenement_aujourd_hui() -> dict | None:
    db = get_client()
    today = datetime.now(TZ_LOCAL).date().isoformat()
    res = (
        db.table("journal_presence")
        .select("*")
        .eq("date_jour", today)
        .order("horodatage", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    ev = res.data[0]
    if ev.get("horodatage"):
        local_dt = pd.to_datetime(ev["horodatage"], utc=True).tz_convert(TZ_LOCAL)
        ev["horodatage"] = local_dt.strftime("%H:%M:%S")
    return ev


# ════════════════════════════════════════════════════════════
#  PROJETS
# ════════════════════════════════════════════════════════════

def get_projets() -> pd.DataFrame:
    db = get_client()
    res = db.table("projets").select("*").order("nom").execute()
    if not res.data:
        return pd.DataFrame()
    return pd.DataFrame(res.data)


def creer_projet(nom: str, description: str, couleur: str, date_fin: date | None) -> dict:
    db = get_client()
    payload = {
        "nom": nom,
        "description": description or None,
        "couleur": couleur,
        "date_debut": _today_local().isoformat(),
        "date_fin": date_fin.isoformat() if date_fin else None,
        "statut": "EN_COURS",
    }
    res = db.table("projets").insert(payload).execute()
    return res.data[0] if res.data else {}


def maj_projet(projet_id: str, statut: str) -> dict:
    db = get_client()
    res = db.table("projets").update({"statut": statut}).eq("projet_id", projet_id).execute()
    return res.data[0] if res.data else {}


def supprimer_projet(projet_id: str) -> None:
    db = get_client()
    db.table("projets").delete().eq("projet_id", projet_id).execute()


# ════════════════════════════════════════════════════════════
#  TÂCHES
# ════════════════════════════════════════════════════════════

def _parse_taches(data: list) -> pd.DataFrame:
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df["cree_le"]    = _utc_to_local(df["cree_le"])
    df["cloture_le"] = _utc_to_local(df["cloture_le"])
    return df


def creer_tache(
    titre: str,
    categorie: str,
    zone_usine: str,
    complexite: int,
    statut: str = "EN_COURS",
    description: str | None = None,
    livrable: str | None = None,
    projet_id: str | None = None,
) -> dict:
    db = get_client()
    payload = {
        "titre": titre,
        "categorie": categorie,
        "zone_usine": zone_usine,
        "complexite": complexite,
        "statut": statut,
        "description": description,
        "livrable": livrable,
        "projet_id": projet_id or None,
        "cree_le": _now_utc_iso(),
    }
    res = db.table("journal_taches").insert(payload).execute()
    return res.data[0] if res.data else {}


def maj_statut_tache(
    tache_id: str,
    nouveau_statut: str,
    raison_blocage: str | None = None,
    livrable: str | None = None,
) -> dict:
    db = get_client()
    payload: dict = {"statut": nouveau_statut}
    if nouveau_statut == "TERMINE":
        payload["cloture_le"] = _now_utc_iso()
    if raison_blocage is not None:
        payload["raison_blocage"] = raison_blocage
    if livrable is not None:
        payload["livrable"] = livrable
    res = db.table("journal_taches").update(payload).eq("tache_id", tache_id).execute()
    return res.data[0] if res.data else {}


def supprimer_tache(tache_id: str) -> None:
    db = get_client()
    db.table("journal_taches").delete().eq("tache_id", tache_id).execute()


def get_taches(date_debut: date, date_fin: date) -> pd.DataFrame:
    db = get_client()
    # Filtre sur la date locale Tunis → on étend d'un jour de chaque côté en UTC pour être safe
    res = (
        db.table("journal_taches")
        .select("*, projets(nom, couleur)")
        .gte("cree_le", f"{date_debut.isoformat()}T00:00:00+01:00")
        .lte("cree_le", f"{date_fin.isoformat()}T23:59:59+01:00")
        .order("cree_le", desc=True)
        .execute()
    )
    df = _parse_taches(res.data)
    if df.empty:
        return df
    # Aplatir la relation projet
    if "projets" in df.columns:
        df["projet_nom"]    = df["projets"].apply(lambda x: x["nom"]    if isinstance(x, dict) else None)
        df["projet_couleur"]= df["projets"].apply(lambda x: x["couleur"] if isinstance(x, dict) else "#64748b")
        df.drop(columns=["projets"], inplace=True)
    return df


def get_taches_du_jour() -> pd.DataFrame:
    today = datetime.now(TZ_LOCAL).date()
    return get_taches(today, today)


def get_toutes_taches() -> pd.DataFrame:
    db = get_client()
    res = (
        db.table("journal_taches")
        .select("*, projets(nom, couleur)")
        .order("cree_le", desc=True)
        .execute()
    )
    df = _parse_taches(res.data)
    if df.empty:
        return df
    if "projets" in df.columns:
        df["projet_nom"]    = df["projets"].apply(lambda x: x["nom"]    if isinstance(x, dict) else None)
        df["projet_couleur"]= df["projets"].apply(lambda x: x["couleur"] if isinstance(x, dict) else "#64748b")
        df.drop(columns=["projets"], inplace=True)
    return df


# ════════════════════════════════════════════════════════════
#  NOTES JOURNALIÈRES
# ════════════════════════════════════════════════════════════

def sauvegarder_note_journaliere(
    resume: str,
    points_bloquants: str,
    plan_lendemain: str,
    score_engagement: int,
    date_cible: date | None = None,
) -> dict:
    db = get_client()
    d = (date_cible or _today_local()).isoformat()
    payload = {
        "date_jour": d,
        "resume": resume,
        "points_bloquants": points_bloquants,
        "plan_lendemain": plan_lendemain,
        "score_engagement": score_engagement,
    }
    res = db.table("notes_journalieres").upsert(payload, on_conflict="date_jour").execute()
    return res.data[0] if res.data else {}


def get_notes(date_debut: date, date_fin: date) -> pd.DataFrame:
    db = get_client()
    res = (
        db.table("notes_journalieres")
        .select("*")
        .gte("date_jour", date_debut.isoformat())
        .lte("date_jour", date_fin.isoformat())
        .order("date_jour", desc=True)
        .execute()
    )
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()


# ════════════════════════════════════════════════════════════
#  OBJECTIFS
# ════════════════════════════════════════════════════════════

def creer_objectif(
    titre: str,
    description: str,
    date_echeance: date,
    progression: int = 0,
    statut: str = "EN_COURS",
) -> dict:
    db = get_client()
    # date_echeance est un objet date Python → .isoformat() = "YYYY-MM-DD"
    # Supabase le stocke en colonne DATE, pas TIMESTAMPTZ → aucun décalage possible
    payload = {
        "titre": titre,
        "description": description or None,
        "date_echeance": date_echeance.isoformat(),
        "progression": progression,
        "statut": statut,
    }
    res = db.table("objectifs").insert(payload).execute()
    return res.data[0] if res.data else {}


def maj_objectif(obj_id: str, progression: int, statut: str) -> dict:
    db = get_client()
    res = (
        db.table("objectifs")
        .update({"progression": progression, "statut": statut})
        .eq("obj_id", obj_id)
        .execute()
    )
    return res.data[0] if res.data else {}


def supprimer_objectif(obj_id: str) -> None:
    db = get_client()
    db.table("objectifs").delete().eq("obj_id", obj_id).execute()


def get_objectifs() -> pd.DataFrame:
    db = get_client()
    res = db.table("objectifs").select("*").order("date_echeance").execute()
    if not res.data:
        return pd.DataFrame()
    df = pd.DataFrame(res.data)
    # Colonne DATE → parse direct, pas de conversion TZ
    df["date_echeance"] = pd.to_datetime(df["date_echeance"]).dt.date
    return df