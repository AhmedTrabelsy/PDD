# views/manager.py
from __future__ import annotations
from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st
from services import database as db
from services import kpi_engine as kpi
from services import pdf_export
from components import charts


def _periode_sidebar() -> tuple[date, date]:
    with st.sidebar:
        st.markdown("---")
        st.markdown("**📅 Période d'analyse**")
        choix = st.radio("Période", ["7 derniers jours","30 derniers jours",
                                     "Cette semaine","Ce mois","Personnalisée"],
                         label_visibility="collapsed")
        today = date.today()
        if choix == "7 derniers jours":  return today - timedelta(days=6), today
        if choix == "30 derniers jours": return today - timedelta(days=29), today
        if choix == "Cette semaine":
            return today - timedelta(days=today.weekday()), today
        if choix == "Ce mois":
            return today.replace(day=1), today
        c1, c2 = st.columns(2)
        return c1.date_input("Du", value=today-timedelta(days=29)), c2.date_input("Au", value=today)


# ── Onglet 1 : Vue Globale ────────────────────────────────────
def _onglet_global(df_t: pd.DataFrame, df_p: pd.DataFrame):
    st.markdown("### 📊 Indicateurs Clés de Performance")

    v_c  = kpi.velocite_semaine_courante(df_t)
    v_pr = kpi.velocite_semaine_precedente(df_t)
    lt   = kpi.lead_time_moyen(df_t)
    sc   = kpi.score_complexite_semaine(df_t)
    ponc = kpi.indice_ponctualite(df_p)
    eff  = kpi.taux_efficacite(df_t, df_p)
    tb   = kpi.taux_blocage(df_t)

    c1,c2,c3 = st.columns(3)
    c1.metric("🚀 Tâches terminées (semaine)", v_c, kpi.delta_pct(v_c, v_pr),
              help="Tâches clôturées cette semaine ISO vs semaine précédente")
    c2.metric("⏱️ Lead Time moyen", f"{lt}h",
              help="Durée moyenne création → clôture (30 derniers jours)")
    c3.metric("🧠 Score de complexité", sc,
              help="Somme des complexités (1-5) des tâches terminées cette semaine")
    c4,c5,c6 = st.columns(3)
    c4.metric("📅 Indice de ponctualité", f"{ponc}%",
              help="100 − écart-type des heures d'arrivée (en minutes). 100% = horaires stables.")
    c5.metric("⚡ Taux d'efficacité", f"{eff}%",
              help="(Heures sur tâches / Heures pointées) × 100")
    c6.metric("🚧 Taux de blocage", f"{tb}%", delta_color="inverse",
              help="% de tâches actives en statut BLOQUÉ")

    # Alertes blocages
    bloquees = kpi.taches_bloquees(df_t)
    if not bloquees.empty:
        st.error(f"⚠️ **{len(bloquees)} tâche(s) bloquée(s)** nécessitent une action.", icon="🚧")
        for _, t in bloquees.iterrows():
            raison = t.get("raison_blocage") or "Raison non précisée"
            projet = f" · 📁 {t['projet_nom']}" if t.get("projet_nom") else ""
            st.markdown(
                f"<div style='background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);"
                f"border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.5rem;font-size:13px;'>"
                f"<b style='color:#f87171;'>{t['titre']}</b> "
                f"<span style='color:#64748b;'>— {t['zone_usine']} · {t['categorie']}{projet}</span><br>"
                f"<span style='color:#ef4444;'>🔴 {raison}</span></div>",
                unsafe_allow_html=True)

    st.divider()
    ca, cb = st.columns(2)
    with ca:
        st.plotly_chart(charts.graphique_velocite(kpi.velocite_hebdomadaire(df_t)), use_container_width=True)
    with cb:
        st.plotly_chart(charts.graphique_categories(kpi.repartition_par_categorie(df_t)), use_container_width=True)
    st.plotly_chart(charts.graphique_gauge_efficacite(eff), use_container_width=True)
    st.plotly_chart(charts.graphique_heatmap_zones(kpi.heatmap_zone_semaine(df_t)), use_container_width=True)


# ── Onglet 2 : Présence ──────────────────────────────────────
def _onglet_presence(df_p: pd.DataFrame):
    st.markdown("### 🕐 Présence & Ponctualité")
    if df_p.empty:
        st.info("Aucune donnée de présence pour cette période."); return

    st.plotly_chart(charts.graphique_presence(kpi.heures_presence_par_jour(df_p)), use_container_width=True)

    df_j = kpi.heures_presence_par_jour(df_p)
    if not df_j.empty:
        tot = df_j["heures_presentes"].sum()
        moy = df_j["heures_presentes"].mean()
        c1,c2,c3 = st.columns(3)
        c1.metric("Jours de présence", len(df_j))
        c2.metric("Total heures",      f"{tot:.1f}h")
        c3.metric("Moyenne / jour",    f"{moy:.1f}h")

    st.divider()
    st.markdown("#### 📋 Journal détaillé des pointages")
    df_aff = df_p[["date_jour","type_evenement","horodatage","zone_usine","note"]].copy()
    df_aff["horodatage"]     = pd.to_datetime(df_aff["horodatage"]).dt.strftime("%H:%M:%S")
    df_aff["date_jour"]      = df_aff["date_jour"].astype(str)
    df_aff["type_evenement"] = df_aff["type_evenement"].map({"ENTREE":"🟢 Arrivée","SORTIE":"🔴 Départ"})
    df_aff.columns = ["Date","Événement","Heure","Zone","Note"]
    st.dataframe(df_aff, use_container_width=True, hide_index=True)


# ── Onglet 3 : Tâches & Blocages ─────────────────────────────
def _onglet_taches(df_t: pd.DataFrame):
    st.markdown("### ✅ Tâches & Analyse des Blocages")
    if df_t.empty:
        st.info("Aucune tâche pour cette période."); return

    st.plotly_chart(charts.graphique_lead_time(kpi.lead_time_par_categorie(df_t)), use_container_width=True)

    # Zone chart
    df_z = kpi.repartition_par_zone(df_t)
    if not df_z.empty:
        fig_z = px.bar(df_z, x="zone_usine", y="nb_taches", color="statut",
                       title="Tâches par zone", barmode="stack",
                       color_discrete_map={"TERMINE":"#10b981","EN_COURS":"#3b82f6",
                                           "BLOQUE":"#ef4444","A_FAIRE":"#64748b"},
                       labels={"zone_usine":"Zone","nb_taches":"Nb tâches","statut":"Statut"})
        fig_z.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font_color="#94a3b8", margin=dict(l=20,r=20,t=40,b=20))
        st.plotly_chart(fig_z, use_container_width=True)

    st.divider()
    st.markdown("#### 📋 Liste des tâches")
    col1, col2 = st.columns(2)
    f_stat = col1.multiselect("Statut",    ["A_FAIRE","EN_COURS","BLOQUE","TERMINE"],
                               default=["A_FAIRE","EN_COURS","BLOQUE","TERMINE"])
    f_cat  = col2.multiselect("Catégorie", df_t["categorie"].unique().tolist(),
                               default=df_t["categorie"].unique().tolist())
    df_f = df_t[df_t["statut"].isin(f_stat) & df_t["categorie"].isin(f_cat)]

    cols_aff = ["cree_le","cloture_le","titre","projet_nom","categorie","zone_usine","statut","complexite","livrable","raison_blocage"]
    cols_aff = [c for c in cols_aff if c in df_f.columns]
    df_aff = df_f[cols_aff].copy()
    df_aff["cree_le"]    = pd.to_datetime(df_aff["cree_le"]).dt.strftime("%d/%m/%Y %H:%M")
    df_aff["cloture_le"] = pd.to_datetime(df_aff["cloture_le"]).dt.strftime("%d/%m/%Y %H:%M").fillna("—")
    rename = {"cree_le":"Créée le","cloture_le":"Clôturée le","titre":"Titre","projet_nom":"Projet",
               "categorie":"Catégorie","zone_usine":"Zone","statut":"Statut",
               "complexite":"Cx","livrable":"Livrable","raison_blocage":"Blocage"}
    df_aff.columns = [rename.get(c, c) for c in df_aff.columns]
    st.dataframe(df_aff, use_container_width=True, hide_index=True)


# ── Onglet 4 : Projets ───────────────────────────────────────
def _onglet_projets(df_t: pd.DataFrame):
    st.markdown("### 📁 Suivi des Projets")

    df_proj_kpi = kpi.temps_par_projet(df_t)
    if df_proj_kpi.empty:
        st.info("Aucune tâche terminée liée à un projet pour cette période."); 
    else:
        cp, cq = st.columns(2)
        with cp:
            st.plotly_chart(charts.graphique_temps_projets(df_proj_kpi), use_container_width=True)
        with cq:
            df_vp = kpi.velocite_par_projet(df_t)
            st.plotly_chart(charts.graphique_velocite_projets(df_vp), use_container_width=True)

        st.markdown("#### 📊 Tableau récapitulatif par projet")
        st.dataframe(df_proj_kpi.rename(columns={
            "projet_nom":"Projet","heures":"Heures","nb_taches":"Tâches terminées","score_cx":"Score Cx"
        }), use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### 📋 Tous les projets")
    df_projets = db.get_projets()
    if df_projets.empty:
        st.info("Aucun projet créé."); return

    STATUTS_P = {"EN_COURS":"🔵 En cours","EN_PAUSE":"⏸️ En pause",
                 "TERMINE":"✅ Terminé","ABANDONNE":"⚫ Abandonné"}
    COULEURS_P = {"EN_COURS":"#3b82f6","EN_PAUSE":"#f59e0b",
                  "TERMINE":"#10b981","ABANDONNE":"#64748b"}
    for _, p in df_projets.iterrows():
        c = p.get("couleur", "#3b82f6")
        # Tâches liées dans la période
        nb_taches_p = 0
        if not df_t.empty and "projet_id" in df_t.columns:
            nb_taches_p = (df_t["projet_id"] == p["projet_id"]).sum()
        st.markdown(f"""
        <div style='background:#121828;border:1px solid rgba(255,255,255,0.07);
                    border-left:3px solid {c};border-radius:10px;
                    padding:1rem 1.25rem;margin-bottom:0.75rem;'>
            <div style='display:flex;justify-content:space-between;align-items:center;'>
                <span style='color:#e2e8f0;font-weight:600;'>📁 {p['nom']}</span>
                <span style='background:{COULEURS_P.get(p["statut"],"#64748b")}22;
                             color:{COULEURS_P.get(p["statut"],"#64748b")};
                             padding:2px 10px;border-radius:100px;font-size:11px;'>
                    {STATUTS_P.get(p["statut"], p["statut"])}
                </span>
            </div>
            {'<div style="color:#64748b;font-size:12px;margin-top:4px;">'+str(p.get('description',''))+'</div>' if p.get('description') else ''}
            <div style='color:#64748b;font-size:11px;margin-top:6px;'>
                {nb_taches_p} tâche(s) sur la période analysée
                {'· 📅 Fin : '+str(p["date_fin"]) if p.get("date_fin") else ''}
            </div>
        </div>""", unsafe_allow_html=True)


# ── Onglet 5 : OKR ───────────────────────────────────────────
def _onglet_okr():
    st.markdown("### 🎯 Objectifs Stratégiques (OKR)")
    df_obj = db.get_objectifs()
    if df_obj.empty:
        st.info("Aucun objectif défini.", icon="🎯"); return

    STATUTS_OKR = {"EN_COURS":("🔵","#3b82f6"),"EN_RISQUE":("🟡","#f59e0b"),
                   "ATTEINT":("🟢","#10b981"),"ABANDONNE":("⚫","#64748b")}
    for _, obj in df_obj.iterrows():
        ic, c = STATUTS_OKR.get(obj["statut"], ("⚪","#64748b"))
        pct = int(obj["progression"])
        jours = (obj["date_echeance"] - date.today()).days
        jt = (f"<span style='color:#ef4444;'>Dépassé de {abs(jours)}j</span>" if jours < 0 else
              f"<span style='color:#f59e0b;'>{jours}j restant(s)</span>" if jours <= 7 else
              f"<span style='color:#64748b;'>{jours}j restant(s)</span>")
        st.markdown(f"""
        <div style='background:#121828;border:1px solid rgba(255,255,255,0.07);
                    border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem;'>
            <div style='display:flex;justify-content:space-between;margin-bottom:6px;'>
                <span style='color:#e2e8f0;font-weight:600;font-size:15px;'>{ic} {obj['titre']}</span>
                <span style='background:{c}22;color:{c};padding:3px 12px;border-radius:100px;
                             font-size:11px;border:1px solid {c}44;'>{obj['statut'].replace('_',' ')}</span>
            </div>
            {'<p style="color:#64748b;font-size:12px;margin:0 0 8px;">'+str(obj.get('description',''))+'</p>' if obj.get('description') else ''}
            <div style='font-size:12px;color:#64748b;margin-bottom:8px;'>
                📅 Échéance : {obj['date_echeance']} · {jt}
            </div>
            <div style='display:flex;align-items:center;gap:12px;'>
                <div style='flex:1;background:#1a2235;border-radius:6px;height:10px;'>
                    <div style='background:{c};width:{pct}%;height:10px;border-radius:6px;'></div>
                </div>
                <span style='color:{c};font-weight:700;font-size:14px;'>{pct}%</span>
            </div>
        </div>""", unsafe_allow_html=True)

    st.divider()
    na = (df_obj["statut"] == "ATTEINT").sum()
    nc = (df_obj["statut"] == "EN_COURS").sum()
    nr = (df_obj["statut"] == "EN_RISQUE").sum()
    pm = df_obj["progression"].mean()
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Atteints",            f"{na}/{len(df_obj)}")
    c2.metric("En cours",            nc)
    c3.metric("En risque",           nr, delta_color="inverse")
    c4.metric("Progression moyenne", f"{pm:.0f}%")


# ── Onglet 6 : Rapport PDF ────────────────────────────────────
def _onglet_pdf(df_t: pd.DataFrame, df_p: pd.DataFrame, d1: date, d2: date):
    st.markdown("### 📄 Rapport PDF")
    st.info("Génère un rapport PDF professionnel pour la période sélectionnée.", icon="📋")
    nt = len(df_t); nok = (df_t["statut"] == "TERMINE").sum() if not df_t.empty else 0
    nj = df_p["date_jour"].nunique() if not df_p.empty else 0
    c1,c2,c3 = st.columns(3)
    c1.metric("Tâches dans le rapport", nt)
    c2.metric("Tâches terminées",       nok)
    c3.metric("Jours de présence",      nj)
    if st.button("📥 Générer le rapport PDF", use_container_width=True, type="primary"):
        with st.spinner("Génération en cours…"):
            try:
                notes = db.get_notes(d1, d2)
                objs  = db.get_objectifs()
                pdf_bytes = pdf_export.generer_rapport(df_t, df_p, notes, objs, d1, d2)
                nom = f"PPD_Rapport_{d1.strftime('%Y%m%d')}_{d2.strftime('%Y%m%d')}.pdf"
                st.download_button("⬇️ Télécharger", data=pdf_bytes, file_name=nom,
                                   mime="application/pdf", use_container_width=True)
                st.success("✅ Rapport généré !")
            except Exception as e:
                st.error(f"Erreur : {e}")


# ── Point d'entrée ───────────────────────────────────────────
def afficher_vue_manager():
    st.markdown("""<div style='margin-bottom:1.5rem;'>
        <h1 style='color:#e2e8f0;font-size:1.6rem;font-weight:700;margin:0;'>📊 Vue Manager</h1>
        <p style='color:#64748b;font-size:13px;margin:4px 0 0;'>Tableau de bord de performance — lecture seule</p>
    </div>""", unsafe_allow_html=True)

    d1, d2 = _periode_sidebar()
    st.markdown(f"<div style='background:#1a2235;border:1px solid rgba(59,130,246,0.2);"
                f"border-radius:8px;padding:0.6rem 1rem;margin-bottom:1.5rem;font-size:13px;color:#94a3b8;'>"
                f"📅 Période : <b style='color:#3b82f6;'>{d1.strftime('%d/%m/%Y')} → {d2.strftime('%d/%m/%Y')}</b>"
                f"</div>", unsafe_allow_html=True)

    with st.spinner("Chargement des données…"):
        df_t = db.get_taches(d1, d2)
        df_p = db.get_presence(d1, d2)

    o1,o2,o3,o4,o5,o6 = st.tabs([
        "📊 Vue Globale","🕐 Présence","✅ Tâches","📁 Projets","🎯 OKR","📄 Rapport PDF"
    ])
    with o1: _onglet_global(df_t, df_p)
    with o2: _onglet_presence(df_p)
    with o3: _onglet_taches(df_t)
    with o4: _onglet_projets(df_t)
    with o5: _onglet_okr()
    with o6: _onglet_pdf(df_t, df_p, d1, d2)