# views/manager.py
# ─────────────────────────────────────────────────────────────
# Vue Manager — tableau de bord exécutif en lecture seule.
# Onglets : Vue Globale · Présence · Tâches & Blocages · OKR · Rapport PDF
# ─────────────────────────────────────────────────────────────

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from services import database as db
from services import kpi_engine as kpi
from services import pdf_export
from components import charts


# ════════════════════════════════════════════════════════════
#  SÉLECTEUR DE PÉRIODE (sidebar manager)
# ════════════════════════════════════════════════════════════

def _periode_sidebar() -> tuple[date, date]:
    with st.sidebar:
        st.markdown("---")
        st.markdown("**📅 Période d'analyse**")
        choix = st.radio(
            "Période",
            ["7 derniers jours", "30 derniers jours", "Cette semaine", "Ce mois", "Personnalisée"],
            label_visibility="collapsed",
        )
        today = date.today()
        if choix == "7 derniers jours":
            return today - timedelta(days=6), today
        elif choix == "30 derniers jours":
            return today - timedelta(days=29), today
        elif choix == "Cette semaine":
            debut = today - timedelta(days=today.weekday())
            return debut, today
        elif choix == "Ce mois":
            return today.replace(day=1), today
        else:
            col1, col2 = st.columns(2)
            d1 = col1.date_input("Du", value=today - timedelta(days=29))
            d2 = col2.date_input("Au", value=today)
            return d1, d2


# ════════════════════════════════════════════════════════════
#  ONGLET 1 — VUE GLOBALE (KPI FLASH)
# ════════════════════════════════════════════════════════════

def _onglet_global(df_taches: pd.DataFrame, df_presence: pd.DataFrame):
    st.markdown("### 📊 Indicateurs Clés de Performance")

    # ── KPI Flash ─────────────────────────────────────────
    v_curr  = kpi.velocite_semaine_courante(df_taches)
    v_prev  = kpi.velocite_semaine_precedente(df_taches)
    lt      = kpi.lead_time_moyen(df_taches)
    sc      = kpi.score_complexite_semaine(df_taches)
    ponct   = kpi.indice_ponctualite(df_presence)
    effi    = kpi.taux_efficacite(df_taches, df_presence)
    taux_b  = kpi.taux_blocage(df_taches)
    delta_v = kpi.delta_pct(v_curr, v_prev)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            label="🚀 Tâches terminées (semaine)",
            value=v_curr,
            delta=delta_v,
            help="Nombre de tâches clôturées cette semaine ISO vs la semaine précédente",
        )
    with c2:
        st.metric(
            label="⏱️ Lead Time moyen",
            value=f"{lt}h",
            help="Durée moyenne entre la création et la clôture d'une tâche (30 derniers jours)",
        )
    with c3:
        st.metric(
            label="🧠 Score de complexité (semaine)",
            value=sc,
            help="Somme des niveaux de complexité (1–5) des tâches terminées cette semaine",
        )

    c4, c5, c6 = st.columns(3)
    with c4:
        st.metric(
            label="📅 Indice de ponctualité",
            value=f"{ponct}%",
            help="100 − (écart-type des heures d'arrivée en minutes). 100% = parfaitement régulier.",
        )
    with c5:
        st.metric(
            label="⚡ Taux d'efficacité",
            value=f"{effi}%",
            help="(Heures sur tâches terminées / Heures pointées) × 100",
        )
    with c6:
        delta_blocage = f"{taux_b}%" if taux_b > 0 else None
        st.metric(
            label="🚧 Taux de blocage",
            value=f"{taux_b}%",
            delta=delta_blocage,
            delta_color="inverse",
            help="% de tâches actives actuellement en statut BLOQUÉ",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Alertes actives ───────────────────────────────────
    taches_bloquees = kpi.taches_bloquees(df_taches)
    if not taches_bloquees.empty:
        st.error(
            f"⚠️ **{len(taches_bloquees)} tâche(s) actuellement bloquée(s)** "
            f"nécessitent une action.",
            icon="🚧",
        )
        for _, t in taches_bloquees.iterrows():
            raison = t.get("raison_blocage") or "Raison non précisée"
            st.markdown(
                f"<div style='background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.2); "
                f"border-radius:8px; padding:0.75rem 1rem; margin-bottom:0.5rem; font-size:13px;'>"
                f"<b style='color:#f87171;'>{t['titre']}</b> "
                f"<span style='color:#64748b;'>— {t['zone_usine']} · {t['categorie']}</span><br>"
                f"<span style='color:#ef4444;'>🔴 {raison}</span></div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Graphiques ────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        df_vel = kpi.velocite_hebdomadaire(df_taches)
        st.plotly_chart(charts.graphique_velocite(df_vel), use_container_width=True)

    with col_b:
        df_cat = kpi.repartition_par_categorie(df_taches)
        st.plotly_chart(charts.graphique_categories(df_cat), use_container_width=True)

    # Jauge efficacité
    st.plotly_chart(charts.graphique_gauge_efficacite(effi), use_container_width=True)

    # Heatmap zones
    st.markdown("#### 🏭 Carte d'intervention par zone et jour")
    pivot = kpi.heatmap_zone_semaine(df_taches)
    st.plotly_chart(charts.graphique_heatmap_zones(pivot), use_container_width=True)


# ════════════════════════════════════════════════════════════
#  ONGLET 2 — PRÉSENCE & HORAIRES
# ════════════════════════════════════════════════════════════

def _onglet_presence(df_presence: pd.DataFrame):
    st.markdown("### 🕐 Présence & Ponctualité")

    if df_presence.empty:
        st.info("Aucune donnée de présence disponible pour cette période.")
        return

    # Graphique ligne
    df_par_jour = kpi.heures_presence_par_jour(df_presence)
    st.plotly_chart(charts.graphique_presence(df_par_jour), use_container_width=True)

    # Statistiques de présence
    if not df_par_jour.empty:
        total_h   = df_par_jour["heures_presentes"].sum()
        moy_h     = df_par_jour["heures_presentes"].mean()
        nb_jours  = len(df_par_jour)

        c1, c2, c3 = st.columns(3)
        c1.metric("Jours de présence",   nb_jours)
        c2.metric("Total heures",        f"{total_h:.1f}h")
        c3.metric("Moyenne / jour",      f"{moy_h:.1f}h")

    st.divider()
    st.markdown("#### 📋 Journal détaillé des pointages")

    # Tableau des événements
    df_affichage = df_presence[["date_jour", "type_evenement", "horodatage", "zone_usine", "note"]].copy()
    df_affichage["horodatage"] = pd.to_datetime(df_affichage["horodatage"]).dt.strftime("%H:%M:%S")
    df_affichage["date_jour"]  = df_affichage["date_jour"].astype(str)
    df_affichage.columns = ["Date", "Événement", "Heure", "Zone", "Note"]
    df_affichage["Événement"] = df_affichage["Événement"].map(
        {"ENTREE": "🟢 Arrivée", "SORTIE": "🔴 Départ"}
    )
    st.dataframe(df_affichage, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════
#  ONGLET 3 — TÂCHES & BLOCAGES
# ════════════════════════════════════════════════════════════

def _onglet_taches(df_taches: pd.DataFrame):
    st.markdown("### ✅ Tâches & Analyse des Blocages")

    if df_taches.empty:
        st.info("Aucune tâche enregistrée pour cette période.")
        return

    # Lead time par catégorie
    df_lt = kpi.lead_time_par_categorie(df_taches)
    st.plotly_chart(charts.graphique_lead_time(df_lt), use_container_width=True)

    # Répartition par zone et statut
    st.markdown("#### 🏭 Tâches par zone")
    df_zones = kpi.repartition_par_zone(df_taches)
    if not df_zones.empty:
        import plotly.express as px
        fig_z = px.bar(
            df_zones, x="zone_usine", y="nb_taches", color="statut",
            title="Répartition des tâches par zone",
            color_discrete_map={
                "TERMINE": "#10b981", "EN_COURS": "#3b82f6",
                "BLOQUE": "#ef4444",  "A_FAIRE": "#64748b",
            },
            labels={"zone_usine": "Zone", "nb_taches": "Nb tâches", "statut": "Statut"},
            barmode="stack",
        )
        fig_z.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#94a3b8", margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig_z, use_container_width=True)

    st.divider()
    st.markdown("#### 📋 Liste complète des tâches")

    # Filtres
    col1, col2 = st.columns(2)
    filtre_statut = col1.multiselect(
        "Statut",
        ["A_FAIRE", "EN_COURS", "BLOQUE", "TERMINE"],
        default=["A_FAIRE", "EN_COURS", "BLOQUE", "TERMINE"],
    )
    filtre_categorie = col2.multiselect(
        "Catégorie",
        df_taches["categorie"].unique().tolist(),
        default=df_taches["categorie"].unique().tolist(),
    )

    df_f = df_taches[
        df_taches["statut"].isin(filtre_statut) &
        df_taches["categorie"].isin(filtre_categorie)
    ]

    df_aff = df_f[["cree_le", "cloture_le", "titre", "categorie", "zone_usine",
                    "statut", "complexite", "livrable", "raison_blocage"]].copy()
    df_aff["cree_le"]    = df_aff["cree_le"].dt.strftime("%d/%m/%Y %H:%M")
    df_aff["cloture_le"] = df_aff["cloture_le"].dt.strftime("%d/%m/%Y %H:%M").fillna("—")
    df_aff.columns = ["Créée le", "Clôturée le", "Titre", "Catégorie", "Zone",
                       "Statut", "Cx", "Livrable", "Blocage"]
    st.dataframe(df_aff, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════
#  ONGLET 4 — OBJECTIFS STRATÉGIQUES (OKR)
# ════════════════════════════════════════════════════════════

def _onglet_okr():
    st.markdown("### 🎯 Objectifs Stratégiques (OKR)")

    df_obj = db.get_objectifs()

    if df_obj.empty:
        st.info("Aucun objectif défini pour le moment.", icon="🎯")
        return

    STATUTS_OKR = {
        "EN_COURS":  ("🔵", "#3b82f6"),
        "EN_RISQUE": ("🟡", "#f59e0b"),
        "ATTEINT":   ("🟢", "#10b981"),
        "ABANDONNE": ("⚫", "#64748b"),
    }

    for _, obj in df_obj.iterrows():
        icone, couleur = STATUTS_OKR.get(obj["statut"], ("⚪", "#64748b"))
        pct = int(obj["progression"])
        jours = (obj["date_echeance"] - date.today()).days

        if jours < 0:
            jours_txt = f"<span style='color:#ef4444;'>Dépassé de {abs(jours)} jour(s)</span>"
        elif jours <= 7:
            jours_txt = f"<span style='color:#f59e0b;'>{jours} jour(s) restant(s)</span>"
        else:
            jours_txt = f"<span style='color:#64748b;'>{jours} jour(s) restant(s)</span>"

        st.markdown(f"""
        <div style='background:#121828; border:1px solid rgba(255,255,255,0.07);
                    border-radius:12px; padding:1.25rem 1.5rem; margin-bottom:1rem;'>
            <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                <span style='color:#e2e8f0; font-weight:600; font-size:15px;'>{icone} {obj['titre']}</span>
                <span style='background:{couleur}22; color:{couleur}; padding:3px 12px;
                             border-radius:100px; font-size:11px; border:1px solid {couleur}44;'>
                    {obj['statut'].replace('_', ' ')}
                </span>
            </div>
            {'<p style="color:#64748b; font-size:12px; margin:0 0 8px;">' + str(obj.get('description','')) + '</p>' if obj.get('description') else ''}
            <div style='display:flex; justify-content:space-between; font-size:12px; color:#64748b; margin-bottom:10px;'>
                <span>📅 Échéance : {obj['date_echeance']}</span>
                <span>{jours_txt}</span>
            </div>
            <div style='display:flex; align-items:center; gap:12px;'>
                <div style='flex:1; background:#1a2235; border-radius:6px; height:10px;'>
                    <div style='background:{couleur}; width:{pct}%; height:10px; border-radius:6px;
                                 transition:width 0.5s;'></div>
                </div>
                <span style='color:{couleur}; font-weight:700; font-size:14px; min-width:40px;'>
                    {pct}%
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Résumé OKR
    st.divider()
    nb_atteints  = (df_obj["statut"] == "ATTEINT").sum()
    nb_en_cours  = (df_obj["statut"] == "EN_COURS").sum()
    nb_en_risque = (df_obj["statut"] == "EN_RISQUE").sum()
    prog_moy     = df_obj["progression"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Objectifs atteints",    f"{nb_atteints}/{len(df_obj)}")
    c2.metric("En cours",              nb_en_cours)
    c3.metric("En risque",             nb_en_risque, delta_color="inverse")
    c4.metric("Progression moyenne",   f"{prog_moy:.0f}%")


# ════════════════════════════════════════════════════════════
#  ONGLET 5 — RAPPORT PDF
# ════════════════════════════════════════════════════════════

def _onglet_pdf(df_taches: pd.DataFrame, df_presence: pd.DataFrame,
                date_debut: date, date_fin: date):
    st.markdown("### 📄 Rapport PDF Hebdomadaire")

    st.markdown("""
    <div style='background:#121828; border:1px solid rgba(59,130,246,0.2);
                border-radius:12px; padding:1.25rem 1.5rem; margin-bottom:1.5rem;'>
        <p style='color:#94a3b8; font-size:14px; margin:0;'>
            Génère un rapport PDF professionnel incluant tous les KPI, le journal des tâches,
            les objectifs et les notes journalières pour la période sélectionnée.
            Idéal pour les entretiens individuels ou les revues de performance.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Aperçu du contenu
    nb_taches   = len(df_taches)
    nb_termines = (df_taches["statut"] == "TERMINE").sum() if not df_taches.empty else 0
    nb_jours_p  = df_presence["date_jour"].nunique() if not df_presence.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Tâches dans le rapport",  nb_taches)
    c2.metric("Tâches terminées",        nb_termines)
    c3.metric("Jours de présence",       nb_jours_p)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("📥 Générer le rapport PDF", use_container_width=True, type="primary"):
        with st.spinner("Génération du rapport PDF en cours…"):
            df_notes  = db.get_notes(date_debut, date_fin)
            df_obj    = db.get_objectifs()

            try:
                pdf_bytes = pdf_export.generer_rapport(
                    df_taches=df_taches,
                    df_presence=df_presence,
                    df_notes=df_notes,
                    df_objectifs=df_obj,
                    date_debut=date_debut,
                    date_fin=date_fin,
                )
                nom_fichier = (
                    f"PPD_Rapport_{date_debut.strftime('%Y%m%d')}"
                    f"_{date_fin.strftime('%Y%m%d')}.pdf"
                )
                st.download_button(
                    label="⬇️ Télécharger le rapport PDF",
                    data=pdf_bytes,
                    file_name=nom_fichier,
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.success("✅ Rapport généré avec succès !")
            except Exception as e:
                st.error(f"Erreur lors de la génération du PDF : {e}")


# ════════════════════════════════════════════════════════════
#  POINT D'ENTRÉE DE LA VUE
# ════════════════════════════════════════════════════════════

def afficher_vue_manager():
    st.markdown("""
    <div style='margin-bottom:1.5rem;'>
        <h1 style='color:#e2e8f0; font-size:1.6rem; font-weight:700; margin:0;'>
            📊 Vue Manager
        </h1>
        <p style='color:#64748b; font-size:13px; margin:4px 0 0;'>
            Tableau de bord de performance — lecture seule
        </p>
    </div>
    """, unsafe_allow_html=True)

    date_debut, date_fin = _periode_sidebar()

    # Indicateur de période sélectionnée
    st.markdown(
        f"<div style='background:#1a2235; border:1px solid rgba(59,130,246,0.2); "
        f"border-radius:8px; padding:0.6rem 1rem; margin-bottom:1.5rem; font-size:13px; color:#94a3b8;'>"
        f"📅 Période analysée : <b style='color:#3b82f6;'>"
        f"{date_debut.strftime('%d/%m/%Y')} → {date_fin.strftime('%d/%m/%Y')}</b>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Chargement centralisé des données
    with st.spinner("Chargement des données…"):
        df_taches   = db.get_taches(date_debut, date_fin)
        df_presence = db.get_presence(date_debut, date_fin)

    # Onglets
    ong1, ong2, ong3, ong4, ong5 = st.tabs([
        "📊 Vue Globale",
        "🕐 Présence",
        "✅ Tâches & Blocages",
        "🎯 Objectifs (OKR)",
        "📄 Rapport PDF",
    ])

    with ong1:
        _onglet_global(df_taches, df_presence)
    with ong2:
        _onglet_presence(df_presence)
    with ong3:
        _onglet_taches(df_taches)
    with ong4:
        _onglet_okr()
    with ong5:
        _onglet_pdf(df_taches, df_presence, date_debut, date_fin)
