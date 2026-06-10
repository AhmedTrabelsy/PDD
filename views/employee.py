# views/employee.py
from __future__ import annotations
from datetime import date, timedelta
import pandas as pd
import streamlit as st
from services import database as db
from services import kpi_engine as kpi
from components import charts

ZONES = ["Ligne A", "Ligne B", "Salle Serveurs", "Bureau d'Études", "Entrepôt", "Externe"]
CATEGORIES = ["Développement", "Maintenance", "Déploiement Terrain",
               "Analyse de Données", "Documentation", "Réunion"]
STATUTS = {"A_FAIRE": "📋 À faire", "EN_COURS": "🔵 En cours",
           "BLOQUE": "🔴 Bloqué", "TERMINE": "✅ Terminé"}
COULEURS_STATUT = {"A_FAIRE": "#64748b", "EN_COURS": "#3b82f6", "BLOQUE": "#ef4444", "TERMINE": "#10b981"}


def _badge(texte: str, couleur: str) -> str:
    return (f"<span style='background:{couleur}22;color:{couleur};padding:2px 10px;"
            f"border-radius:100px;font-size:11px;border:1px solid {couleur}44;'>{texte}</span>")


def _carte_tache(row: pd.Series, index: int):
    c = COULEURS_STATUT.get(row["statut"], "#64748b")
    projet_badge = ""
    if row.get("projet_nom"):
        pc = row.get("projet_couleur", "#64748b")
        projet_badge = f"<span style='background:{pc}22;color:{pc};padding:2px 8px;border-radius:100px;font-size:11px;border:1px solid {pc}44;'>📁 {row['projet_nom']}</span> "
    st.markdown(f"""
    <div style='background:#121828;border:1px solid rgba(255,255,255,0.07);
                border-left:3px solid {c};border-radius:10px;padding:1rem;margin-bottom:0.5rem;'>
        <div style='color:#e2e8f0;font-weight:600;font-size:14px;margin-bottom:6px;'>{row['titre']}</div>
        <div style='display:flex;gap:6px;flex-wrap:wrap;margin-bottom:4px;'>
            {projet_badge}
            {_badge(STATUTS[row['statut']], c)}
            {_badge('📍 '+row['zone_usine'], '#64748b')}
            {_badge('🏷️ '+row['categorie'], '#64748b')}
            {_badge('⭐'*int(row['complexite']), '#f59e0b')}
        </div>
        {'<div style="color:#ef4444;font-size:12px;margin-top:4px;">🚧 '+str(row.get('raison_blocage',''))+'</div>' if row['statut']=='BLOQUE' and row.get('raison_blocage') else ''}
        {'<div style="color:#10b981;font-size:12px;margin-top:4px;">📦 '+str(row.get('livrable',''))+'</div>' if row.get('livrable') else ''}
    </div>""", unsafe_allow_html=True)

    tid = row["tache_id"]
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 0.5])
    if c1.button("📋", key=f"af_{tid}_{index}", use_container_width=True, help="À faire"):
        db.maj_statut_tache(tid, "A_FAIRE"); st.rerun()
    if c2.button("🔵", key=f"ec_{tid}_{index}", use_container_width=True, help="En cours"):
        db.maj_statut_tache(tid, "EN_COURS"); st.rerun()
    if c3.button("🔴", key=f"bl_{tid}_{index}", use_container_width=True, help="Bloqué"):
        st.session_state[f"show_block_{tid}"] = True; st.rerun()
    if c4.button("✅", key=f"te_{tid}_{index}", use_container_width=True, help="Terminé"):
        db.maj_statut_tache(tid, "TERMINE"); st.success(f"✅ « {row['titre']} » clôturée !"); st.rerun()
    if c5.button("🗑️", key=f"del_{tid}_{index}", use_container_width=True, help="Supprimer"):
        db.supprimer_tache(tid); st.rerun()

    if st.session_state.get(f"show_block_{tid}"):
        with st.form(key=f"fblock_{tid}"):
            raison = st.text_input("Raison du blocage *", placeholder="Ex : En attente d'accès IT…")
            if st.form_submit_button("Confirmer"):
                db.maj_statut_tache(tid, "BLOQUE", raison_blocage=raison)
                st.session_state[f"show_block_{tid}"] = False; st.rerun()


# ── Onglet 1 : Pointage ──────────────────────────────────────
def _onglet_pointage():
    st.markdown("### 🕐 Pointage Rapide")
    dernier = db.get_dernier_evenement_aujourd_hui()
    if dernier:
        evt = "✅ Arrivée" if dernier["type_evenement"] == "ENTREE" else "👋 Départ"
        st.info(f"**Dernier événement aujourd'hui :** {evt} à **{dernier['horodatage']}**", icon="📍")
    else:
        st.info("Aucun pointage enregistré aujourd'hui.", icon="📍")

    zone_sel = st.selectbox("Zone actuelle (optionnel)", ["—"] + ZONES, key="zone_ptg")
    zone_val = zone_sel if zone_sel != "—" else None
    note_val = st.text_input("Note (optionnel)", key="note_ptg")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""<div style='background:rgba(16,185,129,0.08);border:2px solid rgba(16,185,129,0.3);
            border-radius:12px;padding:1.25rem;text-align:center;margin-bottom:0.5rem;'>
            <div style='font-size:2rem;'>🏭</div>
            <div style='color:#10b981;font-weight:600;'>Pointer l'Arrivée</div></div>""",
            unsafe_allow_html=True)
        if st.button("▶ ENTRÉE", key="btn_entree", use_container_width=True):
            res = db.pointer_entree(zone=zone_val, note=note_val or None)
            if res:
                h = pd.to_datetime(res["horodatage"], utc=True).tz_convert("Africa/Tunis").strftime("%H:%M:%S")
                st.success(f"✅ Arrivée enregistrée à **{h}**"); st.rerun()
            else:
                st.error("Erreur lors de l'enregistrement.")

    with col2:
        st.markdown("""<div style='background:rgba(239,68,68,0.08);border:2px solid rgba(239,68,68,0.3);
            border-radius:12px;padding:1.25rem;text-align:center;margin-bottom:0.5rem;'>
            <div style='font-size:2rem;'>🚪</div>
            <div style='color:#ef4444;font-weight:600;'>Pointer le Départ</div></div>""",
            unsafe_allow_html=True)
        if st.button("■ SORTIE", key="btn_sortie", use_container_width=True):
            res = db.pointer_sortie(zone=zone_val, note=note_val or None)
            if res:
                h = pd.to_datetime(res["horodatage"], utc=True).tz_convert("Africa/Tunis").strftime("%H:%M:%S")
                st.success(f"👋 Départ enregistré à **{h}**"); st.rerun()
            else:
                st.error("Erreur lors de l'enregistrement.")

    st.divider()
    st.markdown("#### 📋 Journal du jour")
    df_p = db.get_presence(date.today(), date.today())
    if df_p.empty:
        st.markdown("<p style='color:#64748b;font-size:13px;'>Aucun pointage aujourd'hui.</p>",
                    unsafe_allow_html=True)
    else:
        for _, row in df_p.iterrows():
            icone = "🟢" if row["type_evenement"] == "ENTREE" else "🔴"
            heure = pd.Timestamp(row["horodatage"]).strftime("%H:%M:%S")
            zone  = f" — {row['zone_usine']}" if row.get("zone_usine") else ""
            st.markdown(f"<div style='color:#94a3b8;font-size:13px;padding:3px 0;'>"
                        f"{icone} <b style='color:#e2e8f0;'>{row['type_evenement']}</b> à {heure}{zone}</div>",
                        unsafe_allow_html=True)
        pres = kpi.heures_presence_par_jour(df_p)
        if not pres.empty:
            h = pres["heures_presentes"].sum()
            hh, mm = int(h), int((h - int(h)) * 60)
            st.markdown(f"<div style='margin-top:0.75rem;padding:0.75rem;background:#1a2235;"
                        f"border-radius:8px;color:#10b981;font-weight:600;'>"
                        f"⏱️ Temps total présent aujourd'hui : {hh}h{mm:02d}</div>",
                        unsafe_allow_html=True)


# ── Onglet 2 : Tâches ────────────────────────────────────────
def _onglet_taches():
    st.markdown("### ✅ Gestion des Tâches")

    # Charger la liste des projets pour le sélecteur
    df_projets = db.get_projets()
    projets_actifs = df_projets[df_projets["statut"] == "EN_COURS"] if not df_projets.empty else pd.DataFrame()
    options_projets = {"— Aucun projet —": None}
    if not projets_actifs.empty:
        for _, p in projets_actifs.iterrows():
            options_projets[f"📁 {p['nom']}"] = p["projet_id"]

    with st.expander("➕ Ajouter une nouvelle tâche", expanded=True):
        with st.form("form_tache", clear_on_submit=True):
            titre = st.text_input("Titre de la tâche *", placeholder="Ex : Calibration capteur Ligne A")
            col1, col2 = st.columns(2)
            categorie = col1.selectbox("Catégorie *", CATEGORIES)
            zone      = col2.selectbox("Zone *", ZONES)
            col3, col4 = st.columns(2)
            statut_init = col3.selectbox("Statut initial", list(STATUTS.keys()),
                                         format_func=lambda k: STATUTS[k], index=1)
            complexite = col4.slider("Complexité", 1, 5, 3)

            # Sélecteur de projet
            projet_label = st.selectbox("Projet associé (optionnel)", list(options_projets.keys()))
            projet_id_sel = options_projets[projet_label]

            description = st.text_area("Description (optionnel)", height=70)
            livrable    = st.text_input("Livrable attendu (optionnel)")

            if st.form_submit_button("💾 Enregistrer la tâche", use_container_width=True):
                if not titre.strip():
                    st.error("Le titre est obligatoire.")
                else:
                    db.creer_tache(
                        titre=titre.strip(), categorie=categorie,
                        zone_usine=zone, complexite=complexite,
                        statut=statut_init, description=description or None,
                        livrable=livrable or None, projet_id=projet_id_sel,
                    )
                    st.success(f"✅ Tâche « {titre.strip()} » créée !"); st.rerun()

    st.divider()
    st.markdown("#### 📋 Tableau des tâches du jour")
    df_t = db.get_taches_du_jour()

    if df_t.empty:
        st.markdown("""<div style='text-align:center;padding:2.5rem;color:#64748b;'>
            <div style='font-size:2.5rem;'>📭</div>
            <p>Aucune tâche aujourd'hui. Utilise le formulaire ci-dessus pour commencer.</p>
            </div>""", unsafe_allow_html=True)
        return

    nb_t, nb_ok = len(df_t), (df_t["statut"] == "TERMINE").sum()
    nb_b = (df_t["statut"] == "BLOQUE").sum()
    sc   = df_t[df_t["statut"] == "TERMINE"]["complexite"].sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total",     nb_t)
    c2.metric("Terminées", nb_ok, f"{int(nb_ok/nb_t*100)}%" if nb_t else "0%")
    c3.metric("Bloquées",  nb_b, delta_color="inverse")
    c4.metric("Score Cx",  sc)

    if nb_b > 0:
        st.warning(f"⚠️ {nb_b} tâche(s) bloquée(s) !", icon="🚧")

    filtre = st.multiselect("Filtrer par statut", list(STATUTS.keys()),
                             default=list(STATUTS.keys()), format_func=lambda k: STATUTS[k])
    df_f = df_t[df_t["statut"].isin(filtre)]
    if df_f.empty:
        st.info("Aucune tâche pour les statuts sélectionnés."); return

    for statut in ["BLOQUE", "EN_COURS", "A_FAIRE", "TERMINE"]:
        sous = df_f[df_f["statut"] == statut]
        if sous.empty or statut not in filtre:
            continue
        c = COULEURS_STATUT[statut]
        st.markdown(f"<div style='color:{c};font-weight:600;font-size:12px;"
                    f"text-transform:uppercase;letter-spacing:0.1em;margin:1rem 0 0.5rem;'>"
                    f"{STATUTS[statut]} — {len(sous)}</div>", unsafe_allow_html=True)
        for i, (_, row) in enumerate(sous.iterrows()):
            _carte_tache(row, i)


# ── Onglet 3 : Note du jour ───────────────────────────────────
def _onglet_note():
    st.markdown("### 📝 Note de Fin de Journée")
    df_n = db.get_notes(date.today(), date.today())
    ex = df_n.iloc[0] if not df_n.empty else None

    with st.form("form_note", clear_on_submit=False):
        resume   = st.text_area("📌 Ce que j'ai accompli aujourd'hui",
                                 value=ex["resume"] if ex is not None and ex.get("resume") else "",
                                 height=100)
        blocages = st.text_area("🚧 Points bloquants",
                                 value=ex["points_bloquants"] if ex is not None and ex.get("points_bloquants") else "",
                                 height=70)
        lendemain= st.text_area("📅 Plan pour demain",
                                 value=ex["plan_lendemain"] if ex is not None and ex.get("plan_lendemain") else "",
                                 height=70)
        score_map = {1:"😞 1 — Très difficile", 2:"😐 2 — Difficile",
                     3:"🙂 3 — Correct", 4:"😊 4 — Bonne journée", 5:"🚀 5 — Excellente"}
        score_act = int(ex["score_engagement"]) if ex is not None and ex.get("score_engagement") else 3
        engagement = st.select_slider("Comment s'est passée ta journée ?",
                                       options=[1,2,3,4,5], value=score_act,
                                       format_func=lambda x: score_map[x])
        if st.form_submit_button("💾 Sauvegarder", use_container_width=True):
            db.sauvegarder_note_journaliere(resume, blocages, lendemain, engagement)
            st.success("✅ Note sauvegardée !"); st.rerun()

    if ex is not None:
        st.info("Une note existe déjà pour aujourd'hui — le formulaire la mettra à jour.", icon="ℹ️")


# ── Onglet 4 : Projets ───────────────────────────────────────
def _onglet_projets():
    st.markdown("### 📁 Mes Projets")

    df_p = db.get_projets()
    COULEURS = ["#3b82f6","#10b981","#8b5cf6","#f59e0b","#06b6d4","#ef4444","#ec4899"]
    STATUTS_P = {"EN_COURS":"🔵 En cours","EN_PAUSE":"⏸️ En pause",
                 "TERMINE":"✅ Terminé","ABANDONNE":"⚫ Abandonné"}

    if not df_p.empty:
        for _, p in df_p.iterrows():
            c = p.get("couleur", "#3b82f6")
            st.markdown(f"""
            <div style='background:#121828;border:1px solid rgba(255,255,255,0.07);
                        border-left:3px solid {c};border-radius:10px;
                        padding:1rem 1.25rem;margin-bottom:0.75rem;'>
                <div style='display:flex;justify-content:space-between;'>
                    <span style='color:#e2e8f0;font-weight:600;'>{p['nom']}</span>
                    {_badge(STATUTS_P.get(p['statut'], p['statut']), c)}
                </div>
                {'<div style="color:#64748b;font-size:12px;margin-top:4px;">'+str(p.get('description',''))+'</div>' if p.get('description') else ''}
                {'<div style="color:#64748b;font-size:11px;margin-top:4px;">📅 Fin prévue : '+str(p.get('date_fin',''))+'</div>' if p.get('date_fin') else ''}
            </div>""", unsafe_allow_html=True)

            with st.expander(f"⚙️ Modifier « {p['nom']} »"):
                with st.form(f"fproj_{p['projet_id']}"):
                    new_statut = st.selectbox("Statut", list(STATUTS_P.keys()),
                                               index=list(STATUTS_P.keys()).index(p["statut"]),
                                               format_func=lambda k: STATUTS_P[k])
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("Mettre à jour"):
                        db.maj_projet(p["projet_id"], new_statut)
                        st.success("Projet mis à jour !"); st.rerun()
                    if c2.form_submit_button("🗑️ Supprimer", help="Supprime le projet (les tâches liées restent)"):
                        db.supprimer_projet(p["projet_id"])
                        st.rerun()
    else:
        st.info("Aucun projet créé. Utilise le formulaire ci-dessous pour commencer.")

    st.divider()
    with st.expander("➕ Créer un nouveau projet", expanded=df_p.empty):
        with st.form("form_nouveau_projet", clear_on_submit=True):
            nom   = st.text_input("Nom du projet *")
            desc  = st.text_area("Description", height=60)
            col1, col2 = st.columns(2)
            couleur  = col1.selectbox("Couleur", COULEURS,
                                       format_func=lambda c: f"● {c}")
            date_fin = col2.date_input("Date de fin prévue (optionnel)",
                                        value=None, min_value=date.today())
            if st.form_submit_button("Créer le projet", use_container_width=True):
                if not nom.strip():
                    st.error("Le nom est obligatoire.")
                else:
                    db.creer_projet(nom.strip(), desc, couleur, date_fin)
                    st.success(f"📁 Projet « {nom.strip()} » créé !"); st.rerun()


# ── Onglet 5 : Analytics ─────────────────────────────────────
def _onglet_analytics():
    st.markdown("### 📈 Mes Analytics Personnelles")
    col1, col2 = st.columns(2)
    date_fin   = col1.date_input("Jusqu'au", value=date.today())
    date_debut = col2.date_input("Depuis le", value=date.today() - timedelta(days=30))
    if date_debut > date_fin:
        st.error("Date début > date fin."); return

    with st.spinner("Chargement…"):
        df_t = db.get_taches(date_debut, date_fin)
        df_p = db.get_presence(date_debut, date_fin)

    if df_t.empty and df_p.empty:
        st.info("Aucune donnée pour cette période."); return

    v_c  = kpi.velocite_semaine_courante(df_t)
    v_p  = kpi.velocite_semaine_precedente(df_t)
    lt   = kpi.lead_time_moyen(df_t)
    sc   = kpi.score_complexite_semaine(df_t)
    ponc = kpi.indice_ponctualite(df_p)
    eff  = kpi.taux_efficacite(df_t, df_p)
    tb   = kpi.taux_blocage(df_t)

    c1,c2,c3 = st.columns(3)
    c1.metric("Tâches terminées (semaine)", v_c, kpi.delta_pct(v_c, v_p))
    c2.metric("Lead Time moyen", f"{lt}h")
    c3.metric("Score complexité", sc)
    c1.metric("Indice ponctualité", f"{ponc}%")
    c2.metric("Taux d'efficacité", f"{eff}%")
    c3.metric("Taux de blocage", f"{tb}%", delta_color="inverse")

    st.divider()
    ca, cb = st.columns(2)
    with ca:
        st.plotly_chart(charts.graphique_velocite(kpi.velocite_hebdomadaire(df_t)), use_container_width=True)
    with cb:
        st.plotly_chart(charts.graphique_categories(kpi.repartition_par_categorie(df_t)), use_container_width=True)

    # Projets
    df_proj_kpi = kpi.temps_par_projet(df_t)
    if not df_proj_kpi.empty:
        st.divider()
        st.markdown("#### 📁 Temps par Projet")
        cp, cq = st.columns(2)
        with cp:
            st.plotly_chart(charts.graphique_temps_projets(df_proj_kpi), use_container_width=True)
        with cq:
            df_vp = kpi.velocite_par_projet(df_t)
            st.plotly_chart(charts.graphique_velocite_projets(df_vp), use_container_width=True)
        st.dataframe(df_proj_kpi.rename(columns={
            "projet_nom": "Projet", "heures": "Heures", "nb_taches": "Tâches", "score_cx": "Score Cx"
        }), use_container_width=True, hide_index=True)

    st.plotly_chart(charts.graphique_presence(kpi.heures_presence_par_jour(df_p)), use_container_width=True)
    st.plotly_chart(charts.graphique_lead_time(kpi.lead_time_par_categorie(df_t)), use_container_width=True)

    st.divider()
    st.markdown("#### 📋 Historique")
    if not df_t.empty:
        cols_aff = ["cree_le","titre","projet_nom","categorie","zone_usine","statut","complexite","livrable"]
        cols_aff = [c for c in cols_aff if c in df_t.columns]
        df_aff = df_t[cols_aff].copy()
        df_aff["cree_le"] = pd.to_datetime(df_aff["cree_le"]).dt.strftime("%d/%m/%Y %H:%M")
        df_aff.columns = [{"cree_le":"Créée le","titre":"Titre","projet_nom":"Projet",
                            "categorie":"Catégorie","zone_usine":"Zone","statut":"Statut",
                            "complexite":"Cx","livrable":"Livrable"}.get(c,c) for c in df_aff.columns]
        st.dataframe(df_aff, use_container_width=True, hide_index=True)

    # Objectifs
    st.divider()
    st.markdown("#### 🎯 Mes Objectifs")
    _gestion_objectifs()


def _gestion_objectifs():
    df_obj = db.get_objectifs()
    STATUTS_OBJ = {"EN_COURS":"🔵","EN_RISQUE":"🟡","ATTEINT":"🟢","ABANDONNE":"⚫"}
    COULEURS_OBJ = {"EN_COURS":"#3b82f6","EN_RISQUE":"#f59e0b","ATTEINT":"#10b981","ABANDONNE":"#64748b"}

    if not df_obj.empty:
        for _, obj in df_obj.iterrows():
            ic = STATUTS_OBJ.get(obj["statut"], "⚪")
            c  = COULEURS_OBJ.get(obj["statut"], "#64748b")
            pct = int(obj["progression"])
            jours = (obj["date_echeance"] - date.today()).days
            jours_txt = f"<span style='color:#ef4444;'>{abs(jours)}j dépassé</span>" if jours < 0 else \
                        f"<span style='color:#f59e0b;'>{jours}j</span>" if jours <= 7 else \
                        f"<span style='color:#64748b;'>{jours}j</span>"
            st.markdown(f"""
            <div style='background:#121828;border:1px solid rgba(255,255,255,0.07);
                        border-radius:10px;padding:1rem 1.25rem;margin-bottom:0.75rem;'>
                <div style='display:flex;justify-content:space-between;margin-bottom:6px;'>
                    <span style='color:#e2e8f0;font-weight:600;'>{ic} {obj['titre']}</span>
                    {_badge(obj['statut'], c)}
                </div>
                <div style='color:#64748b;font-size:12px;margin-bottom:8px;'>
                    📅 {obj['date_echeance']} · {jours_txt} restant(s)
                </div>
                <div style='background:#1a2235;border-radius:4px;height:8px;'>
                    <div style='background:{c};width:{pct}%;height:8px;border-radius:4px;'></div>
                </div>
                <div style='color:{c};font-size:12px;font-weight:600;margin-top:4px;'>{pct}%</div>
            </div>""", unsafe_allow_html=True)
            with st.expander(f"✏️ Modifier « {obj['titre']} »"):
                with st.form(f"fobj_{obj['obj_id']}"):
                    npct = st.slider("Progression (%)", 0, 100, pct)
                    nst  = st.selectbox("Statut", list(STATUTS_OBJ.keys()),
                                         index=list(STATUTS_OBJ.keys()).index(obj["statut"]),
                                         format_func=lambda k: f"{STATUTS_OBJ[k]} {k}")
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("Mettre à jour"):
                        db.maj_objectif(obj["obj_id"], npct, nst); st.success("Mis à jour !"); st.rerun()
                    if c2.form_submit_button("🗑️ Supprimer"):
                        db.supprimer_objectif(obj["obj_id"]); st.rerun()

    with st.expander("➕ Créer un objectif"):
        with st.form("form_obj_new", clear_on_submit=True):
            t = st.text_input("Titre *")
            d = st.text_area("Description", height=60)
            e = st.date_input("Échéance *", value=date.today() + timedelta(days=30))
            if st.form_submit_button("Créer"):
                if not t.strip():
                    st.error("Titre obligatoire.")
                else:
                    db.creer_objectif(t.strip(), d, e); st.success(f"🎯 Objectif créé !"); st.rerun()


# ── Point d'entrée ───────────────────────────────────────────
def afficher_vue_employe():
    st.markdown("""<div style='margin-bottom:1.5rem;'>
        <h1 style='color:#e2e8f0;font-size:1.6rem;font-weight:700;margin:0;'>👷 Espace Employé</h1>
        <p style='color:#64748b;font-size:13px;margin:4px 0 0;'>Toutes tes actions quotidiennes</p>
    </div>""", unsafe_allow_html=True)

    o1, o2, o3, o4, o5 = st.tabs([
        "🕐 Pointage", "✅ Mes Tâches", "📁 Projets", "📝 Note du Jour", "📈 Mes Analytics"
    ])
    with o1: _onglet_pointage()
    with o2: _onglet_taches()
    with o3: _onglet_projets()
    with o4: _onglet_note()
    with o5: _onglet_analytics()