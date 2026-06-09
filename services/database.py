# services/database.py
# ─────────────────────────────────────────────────────────────
# Couche d'accès aux données — toutes les interactions Supabase
# sont centralisées ici. Aucune autre vue ne touche Supabase
# directement.
# ─────────────────────────────────────────────────────────────

from __future__ import annotations

import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date, datetime, timezone

# Fuseau horaire cible pour l'affichage des heures
LOCAL_TZ = "Africa/Tunis"


# ── Client Supabase (singleton via cache) ─────────────────────
@st.cache_resource(show_spinner=False)
def get_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


# ════════════════════════════════════════════════════════════
#  PRÉSENCE
# ════════════════════════════════════════════════════════════

def pointer_entree(zone: str | None = None, note: str | None = None) -> dict:
    """Enregistre un pointage d'entrée avec l'heure UTC actuelle."""
    db = get_client()
    payload = {
        "type_evenement": "ENTREE",
        "horodatage": datetime.now(timezone.utc).isoformat(),
        "date_jour": date.today().isoformat(),
        "zone_usine": zone,
        "note": note,
    }
    res = db.table("journal_presence").insert(payload).execute()
    return res.data[0] if res.data else {}


def pointer_sortie(zone: str | None = None, note: str | None = None) -> dict:
    """Enregistre un pointage de sortie avec l'heure UTC actuelle."""
    db = get_client()
    payload = {
        "type_evenement": "SORTIE",
        "horodatage": datetime.now(timezone.utc).isoformat(),
        "date_jour": date.today().isoformat(),
        "zone_usine": zone,
        "note": note,
    }
    res = db.table("journal_presence").insert(payload).execute()
    return res.data[0] if res.data else {}


def get_presence(date_debut: date, date_fin: date) -> pd.DataFrame:
    """Retourne tous les événements de présence convertis à l'heure locale mais typés UTC pour l'UI."""
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
    
    # Hack d'alignement : Heure de Tunis encapsulée dans un type UTC pour l'UI
    df["horodatage"] = pd.to_datetime(df["horodatage"], utc=True)
    df["horodatage"] = df["horodatage"].dt.tz_convert(LOCAL_TZ).dt.tz_localize(None).dt.tz_localize("UTC")
    
    df["date_jour"]  = pd.to_datetime(df["date_jour"]).dt.date
    return df


def get_dernier_evenement_aujourd_hui() -> dict | None:
    """Retourne le dernier événement de présence du jour courant."""
    db = get_client()
    res = (
        db.table("journal_presence")
        .select("*")
        .eq("date_jour", date.today().isoformat())
        .order("horodatage", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
        
    ev = res.data[0]
    if "horodatage" in ev and ev["horodatage"]:
        dt_local = pd.to_datetime(ev["horodatage"], utc=True).tz_convert(LOCAL_TZ)
        ev["horodatage"] = dt_local.strftime("%Y-%m-%d %H:%M:%S")
    return ev


# ════════════════════════════════════════════════════════════
#  TÂCHES
# ════════════════════════════════════════════════════════════

def creer_tache(
    titre: str,
    categorie: str,
    zone_usine: str,
    complexite: int,
    statut: str = "EN_COURS",
    description: str | None = None,
    livrable: str | None = None,
) -> dict:
    """Crée une nouvelle tâche."""
    db = get_client()
    payload = {
        "titre": titre,
        "categorie": categorie,
        "zone_usine": zone_usine,
        "complexite": complexite,
        "statut": statut,
        "description": description,
        "livrable": livrable,
        "cree_le": datetime.now(timezone.utc).isoformat(),
    }
    res = db.table("journal_taches").insert(payload).execute()
    return res.data[0] if res.data else {}


def maj_statut_tache(
    tache_id: str,
    nouveau_statut: str,
    raison_blocage: str | None = None,
    livrable: str | None = None,
) -> dict:
    """Met à jour le statut d'une tâche."""
    db = get_client()
    payload: dict = {"statut": nouveau_statut}
    if nouveau_statut == "TERMINE":
        payload["cloture_le"] = datetime.now(timezone.utc).isoformat()
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
    """Retourne toutes les tâches de la plage de dates alignées sur la timezone attendue par l'UI."""
    db = get_client()
    res = (
        db.table("journal_taches")
        .select("*")
        .gte("cree_le", f"{date_debut.isoformat()}T00:00:00+00:00")
        .lte("cree_le", f"{date_fin.isoformat()}T23:59:59+00:00")
        .order("cree_le", desc=True)
        .execute()
    )
    if not res.data:
        return pd.DataFrame()
    df = pd.DataFrame(res.data)
    
    # Alignement forcé en type UTC pour la compatibilité absolue avec les filtres de l'UI
    df["cree_le"] = pd.to_datetime(df["cree_le"], utc=True).dt.tz_convert(LOCAL_TZ).dt.tz_localize(None).dt.tz_localize("UTC")
    
    df["cloture_le"] = pd.to_datetime(df["cloture_le"], utc=True, errors="coerce")
    # On applique la transformation seulement sur les lignes non nulles
    mask = df["cloture_le"].notna()
    if mask.any():
        df.loc[mask, "cloture_le"] = df.loc[mask, "cloture_le"].dt.tz_convert(LOCAL_TZ).dt.tz_localize(None).dt.tz_localize("UTC")
    return df


def get_taches_du_jour() -> pd.DataFrame:
    """Retourne les tâches créées aujourd'hui."""
    return get_taches(date.today(), date.today())


def get_toutes_taches() -> pd.DataFrame:
    """Retourne toutes les tâches historiques alignées sur la timezone attendue par l'UI."""
    db = get_client()
    res = (
        db.table("journal_taches")
        .select("*")
        .order("cree_le", desc=True)
        .execute()
    )
    if not res.data:
        return pd.DataFrame()
    df = pd.DataFrame(res.data)
    
    df["cree_le"] = pd.to_datetime(df["cree_le"], utc=True).dt.tz_convert(LOCAL_TZ).dt.tz_localize(None).dt.tz_localize("UTC")
    
    df["cloture_le"] = pd.to_datetime(df["cloture_le"], utc=True, errors="coerce")
    mask = df["cloture_le"].notna()
    if mask.any():
        df.loc[mask, "cloture_le"] = df.loc[mask, "cloture_le"].dt.tz_convert(LOCAL_TZ).dt.tz_localize(None).dt.tz_localize("UTC")
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
    """Insère ou met à jour la note du jour (upsert sur date_jour)."""
    db = get_client()
    d = (date_cible or date.today()).isoformat()
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
    if not res.data:
        return pd.DataFrame()
    return pd.DataFrame(res.data)


# ════════════════════════════════════════════════════════════
#  OBJECTIFS (OKR)
# ════════════════════════════════════════════════════════════

def creer_objectif(
    titre: str,
    description: str,
    date_echeance: date,
    progression: int = 0,
    statut: str = "EN_COURS",
) -> dict:
    db = get_client()
    payload = {
        "titre": titre,
        "description": description,
        "date_echeance": date_echeance.isoformat(),
        "progression": progression,
        "statut": statut,
    }
    res = db.table("objectifs").insert(payload).execute()
    return res.data[0] if res.data else {}


def maj_objectif(
    obj_id: str,
    progression: int,
    statut: str,
) -> dict:
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
    df["date_echeance"] = pd.to_datetime(df["date_echeance"]).dt.date
    return df