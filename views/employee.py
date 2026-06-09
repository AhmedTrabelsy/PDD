# views/employee.py
# ─────────────────────────────────────────────────────────────
# Vue Employé — saisie mobile-first.
# 4 onglets : Pointage · Tâches · Note du jour · Mes Analytics
# ─────────────────────────────────────────────────────────────

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from services import database as db
from services import kpi_engine as kpi
from components import charts


# ── Constantes ────────────────────────────────────────────────
ZONES = ["Usine SICAM M EL BEB"]
CATEGORIES = ["Développement", "Maintenance", "Déploiement Terrain",
              "Analyse de Données", "Documentation", "Réunion"]
STATUTS = {"A_FAIRE": "📋 À faire", "EN_COURS": "🔵 En cours",
           "BLOQUE": "🔴 Bloqué", "TERMINE": "✅ Terminé"}
STATUTS_COULEURS = {
    "A_FAIRE": "#64748b", "EN_COURS": "#3b82f6",
    "BLOQUE": "#ef4444",  "TERMINE": "#10b981",
}


def _badge_statut(statut: str) -> str:
    couleur = STATUTS_COULEURS.get(statut, "#64748b")
    label   = STATUTS.get(statut, statut)
    return f"<span style='background:{couleur}22; color:{couleur}; padding:2px 10px; border-radius:100px; font-size:11px; border:1px solid {couleur}44;'>{label}</span>"


def _badge_complexite(n: int) -> str:
    etoiles = "⭐" * n + "☆" * (5 - n)
    return f"<span style='font-size:11px; color:#94a3b8;'>{etoiles}</span>"


def _carte_tache(row: pd.Series, index: int):
    """Affiche une carte de tâche avec boutons de changement de statut."""
    couleur = STATUTS_COULEURS.get(row["statut"], "#64748b")
    st.markdown(f"""
    <div style='background:#121828; border:1px solid rgba(255,255,255,0.07);
                border-left:3px solid {couleur};
                border-radius:10px; padding:1rem; margin-bottom:0.75rem;'>
        <div style='display:flex; justify-content:space-between; align-items:flex-start;'>
            <div style='flex:1;'>
                <div style='color:#e2e8f0; font-weight:600; font-size:14px; margin-bottom:4px;'>
                    {row['titre']}
                </div>
                <div style='display:flex; gap:8px; flex-wrap:wrap; margin-bottom:6px;'>
                    {_badge_statut(row['statut'])}
                    <span style='background:#1a2235; color:#94a3b8; padding:2px 8px;
                                 border-radius:100px; font-size:11px; border:1px solid rgba(255,255,255,0.07);'>
                        📍 {row['zone_usine']}
                    </span>
                    <span style='background:#1a2235; color:#94a3b8; padding:2px 8px;
                                 border-radius:100px; font-size:11px; border:1px solid rgba(255,255,255,0.07);'>
                        🏷️ {row['categorie']}
                    </span>
                </div>
                {_badge_complexite(int(row['complexite']))}
                {'<br><span style="color:#ef4444; font-size:12px; margin-top:4px; display:block;">🚧 ' + str(row.get('raison_blocage','')) + '</span>' if row['statut'] == 'BLOQUE' and row.get('raison_blocage') else ''}
                {'<br><span style="color:#10b981; font-size:12px; margin-top:4px; display:block;">📦 ' + str(row.get('livrable','')) + '</span>' if row.get('livrable') else ''}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Boutons de changement de statut
    cols = st.columns([1, 1, 1, 1, 0.6])
    tache_id = row["tache_id"]

    if cols[0].button("📋 À faire",   key=f"af_{tache_id}_{index}", use_container_width=True):
        db.maj_statut_tache(tache_id, "A_FAIRE")
        st.rerun()
    if cols[1].button("🔵 En cours",  key=f"ec_{tache_id}_{index}", use_container_width=True):
        db.maj_statut_tache(tache_id, "EN_COURS")
        st.rerun()
    if cols[2].button("🔴 Bloqué",    key=f"bl_{tache_id}_{index}", use_container_width=True):
        st.session_state[f"show_block_{tache_id}"] = True
        st.rerun()
    if cols[3].button("✅ Terminé",   key=f"te_{tache_id}_{index}", use_container_width=True):
        db.maj_statut_tache(tache_id, "TERMINE")
        st.success(f"✅ Tâche « {row['titre']} » clôturée !")
        st.rerun()
    if cols[4].button("🗑️", key=f"del_{tache_id}_{index}", use_container_width=True, help="Supprimer"):
        db.supprimer_tache(tache_id)
        st.rerun()

    # Formulaire inline pour la raison de blocage
    if st.session_state.get(f"show_block_{tache_id}"):
        with st.form(key=f"form_block_{tache_id}"):
            raison = st.text_input("Raison du blocage", placeholder="Ex : En attente d'accès IT...")
            if st.form_submit_button("Confirmer le blocage"):
                db.maj_statut_tache(tache_id, "BLOQUE", raison_blocage=raison)
                st.session_state[f"show_block_{tache_id}"] = False
                st.rerun()


# ════════════════════════════════════════════════════════════
#  ONGLET 1 — POINTAGE
# ════════════════════════════════════════════════════════════

def _onglet_pointage():
    st.markdown("### 🕐 Pointage Rapide")

    # Dernier événement du jour
    dernier = db.get_dernier_evenement_aujourd_hui()
    if dernier:
        evt  = "✅ Entrée" if dernier["type_evenement"] == "ENTREE" else "👋 Sortie"
        heure = pd.to_datetime(dernier["horodatage"]).strftime("%H:%M")
        st.info(f"**Dernier événement aujourd'hui :** {evt} à **{heure}**", icon="📍")
    else:
        st.info("Aucun pointage enregistré aujourd'hui.", icon="📍")

    st.markdown("<br>", unsafe_allow_html=True)

    # Zone optionnelle
    zone_sel = st.selectbox("Zone actuelle (optionnel)", ["—"] + ZONES, key="zone_pointage")
    zone_val = zone_sel if zone_sel != "—" else None
    note_val = st.text_input("Note (optionnel)", placeholder="Ex : Retard transport…", key="note_pointage")

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style='background:rgba(16,185,129,0.08); border:2px solid rgba(16,185,129,0.3);
                    border-radius:12px; padding:1.5rem; text-align:center; margin-bottom:0.5rem;'>
            <div style='font-size:2rem;'>🏭</div>
            <div style='color:#10b981; font-weight:600; margin-top:0.5rem;'>Pointer l'Arrivée</div>
            <div style='color:#64748b; font-size:12px;'>Enregistre l'heure actuelle</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("▶ ENTRÉE", key="btn_entree", use_container_width=True,
                     help="Enregistre ton heure d'arrivée maintenant"):
            res = db.pointer_entree(zone=zone_val, note=note_val or None)
            if res:
                h = pd.to_datetime(res["horodatage"]).strftime("%H:%M:%S")
                st.success(f"✅ Arrivée enregistrée à **{h}**")
                st.rerun()
            else:
                st.error("Erreur lors de l'enregistrement.")

    with col2:
        st.markdown("""
        <div style='background:rgba(239,68,68,0.08); border:2px solid rgba(239,68,68,0.3);
                    border-radius:12px; padding:1.5rem; text-align:center; margin-bottom:0.5rem;'>
            <div style='font-size:2rem;'>🚪</div>
            <div style='color:#ef4444; font-weight:600; margin-top:0.5rem;'>Pointer le Départ</div>
            <div style='color:#64748b; font-size:12px;'>Enregistre l'heure actuelle</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("■ SORTIE", key="btn_sortie", use_container_width=True,
                     help="Enregistre ton heure de départ maintenant"):
            res = db.pointer_sortie(zone=zone_val, note=note_val or None)
            if res:
                h = pd.to_datetime(res["horodatage"]).strftime("%H:%M:%S")
                st.success(f"👋 Départ enregistré à **{h}**")
                st.rerun()
            else:
                st.error("Erreur lors de l'enregistrement.")

    # Journal de présence du jour
    st.divider()
    st.markdown("#### 📋 Journal du jour")
    df_p = db.get_presence(date.today(), date.today())
    if df_p.empty:
        st.markdown("<p style='color:#64748b; font-size:13px;'>Aucun pointage aujourd'hui.</p>",
                    unsafe_allow_html=True)
    else:
        for _, row in df_p.iterrows():
            icone = "🟢" if row["type_evenement"] == "ENTREE" else "🔴"
            heure = pd.to_datetime(row["horodatage"]).strftime("%H:%M:%S")
            zone  = f" — {row['zone_usine']}" if row.get("zone_usine") else ""
            st.markdown(
                f"<div style='color:#94a3b8; font-size:13px; padding:4px 0;'>"
                f"{icone} <b style='color:#e2e8f0;'>{row['type_evenement']}</b> "
                f"à {heure}{zone}</div>",
                unsafe_allow_html=True,
            )

        # Durée totale calculée
        presence_df = kpi.heures_presence_par_jour(df_p)
        if not presence_df.empty:
            h = presence_df["heures_presentes"].sum()
            heures  = int(h)
            minutes = int((h - heures) * 60)
            st.markdown(
                f"<div style='margin-top:0.75rem; padding:0.75rem; background:#1a2235; "
                f"border-radius:8px; color:#10b981; font-weight:600;'>"
                f"⏱️ Temps total présent aujourd'hui : {heures}h{minutes:02d}</div>",
                unsafe_allow_html=True,
            )


# ════════════════════════════════════════════════════════════
#  ONGLET 2 — TÂCHES
# ════════════════════════════════════════════════════════════

def _onglet_taches():
    st.markdown("### ✅ Gestion des Tâches")

    # ── Formulaire de nouvelle tâche ─────────────────────
    with st.expander("➕ Ajouter une nouvelle tâche", expanded=True):
        with st.form("form_nouvelle_tache", clear_on_submit=True):
            titre = st.text_input(
                "Titre de la tâche *",
                placeholder="Ex : Calibration capteur Ligne A",
                max_chars=100,
            )

            col1, col2 = st.columns(2)
            categorie = col1.selectbox("Catégorie *", CATEGORIES)
            zone      = col2.selectbox("Zone *", ZONES)

            col3, col4 = st.columns(2)
            statut_init = col3.selectbox(
                "Statut initial",
                list(STATUTS.keys()),
                format_func=lambda k: STATUTS[k],
                index=1,  # EN_COURS par défaut
            )
            complexite = col4.slider("Complexité (1 = simple, 5 = expert)", 1, 5, 3)

            description = st.text_area(
                "Description (optionnel)",
                placeholder="Décris le contexte ou l'objectif de cette tâche…",
                height=80,
            )
            livrable = st.text_input(
                "Livrable attendu (optionnel)",
                placeholder="Ex : Script déployé, rapport PDF généré…",
            )

            submitted = st.form_submit_button("💾 Enregistrer la tâche", use_container_width=True)
            if submitted:
                if not titre.strip():
                    st.error("Le titre est obligatoire.")
                else:
                    db.creer_tache(
                        titre=titre.strip(),
                        categorie=categorie,
                        zone_usine=zone,
                        complexite=complexite,
                        statut=statut_init,
                        description=description or None,
                        livrable=livrable or None,
                    )
                    st.success(f"✅ Tâche « {titre.strip()} » créée !")
                    st.rerun()

    # ── Tableau de bord du jour ───────────────────────────
    st.divider()
    st.markdown("#### 📋 Tableau des tâches du jour")

    df_t = db.get_taches_du_jour()

    if df_t.empty:
        st.markdown("""
        <div style='text-align:center; padding:3rem; color:#64748b;'>
            <div style='font-size:2.5rem;'>📭</div>
            <p>Aucune tâche enregistrée aujourd'hui.<br>
            Utilise le formulaire ci-dessus pour commencer.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Résumé flash du jour
    nb_total    = len(df_t)
    nb_termines = (df_t["statut"] == "TERMINE").sum()
    nb_bloques  = (df_t["statut"] == "BLOQUE").sum()
    score_cx    = df_t[df_t["statut"] == "TERMINE"]["complexite"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total du jour",   nb_total)
    c2.metric("Terminées",       nb_termines, delta=f"{int(nb_termines/nb_total*100)}%" if nb_total else "0%")
    c3.metric("Bloquées",        nb_bloques,  delta_color="inverse")
    c4.metric("Score complexité",score_cx)

    st.markdown("<br>", unsafe_allow_html=True)

    # Alerte blocages
    if nb_bloques > 0:
        st.warning(f"⚠️ {nb_bloques} tâche(s) bloquée(s) nécessitent ton attention !", icon="🚧")

    # Filtre par statut
    filtre = st.multiselect(
        "Filtrer par statut",
        options=list(STATUTS.keys()),
        default=list(STATUTS.keys()),
        format_func=lambda k: STATUTS[k],
    )
    df_filtre = df_t[df_t["statut"].isin(filtre)]

    if df_filtre.empty:
        st.info("Aucune tâche pour les statuts sélectionnés.")
        return

    # Grouper par statut pour l'affichage
    ordre_statuts = ["BLOQUE", "EN_COURS", "A_FAIRE", "TERMINE"]
    for statut in ordre_statuts:
        sous_df = df_filtre[df_filtre["statut"] == statut]
        if sous_df.empty or statut not in filtre:
            continue
        couleur = STATUTS_COULEURS[statut]
        st.markdown(
            f"<div style='color:{couleur}; font-weight:600; font-size:13px; "
            f"text-transform:uppercase; letter-spacing:0.1em; margin:1rem 0 0.5rem;'>"
            f"{STATUTS[statut]} — {len(sous_df)}</div>",
            unsafe_allow_html=True,
        )
        for i, (_, row) in enumerate(sous_df.iterrows()):
            _carte_tache(row, i)


# ════════════════════════════════════════════════════════════
#  ONGLET 3 — NOTE JOURNALIÈRE
# ════════════════════════════════════════════════════════════

def _onglet_note():
    st.markdown("### 📝 Note de Fin de Journée")
    st.markdown(
        "<p style='color:#64748b; font-size:13px;'>Un rapide bilan de ta journée — "
        "visible par le manager dans sa vue hebdomadaire.</p>",
        unsafe_allow_html=True,
    )

    # Charger la note existante du jour
    df_notes = db.get_notes(date.today(), date.today())
    note_existante = df_notes.iloc[0] if not df_notes.empty else None

    with st.form("form_note_jour", clear_on_submit=False):
        resume = st.text_area(
            "📌 Ce que j'ai accompli aujourd'hui",
            value=note_existante["resume"] if note_existante is not None and note_existante.get("resume") else "",
            placeholder="Ex : J'ai déployé le script de monitoring, résolu 2 incidents serveurs…",
            height=100,
        )
        blocages = st.text_area(
            "🚧 Points bloquants ou difficultés rencontrées",
            value=note_existante["points_bloquants"] if note_existante is not None and note_existante.get("points_bloquants") else "",
            placeholder="Ex : Accès refusé au serveur B, besoin d'une validation…",
            height=80,
        )
        lendemain = st.text_area(
            "📅 Plan pour demain",
            value=note_existante["plan_lendemain"] if note_existante is not None and note_existante.get("plan_lendemain") else "",
            placeholder="Ex : Finaliser l'analyse de données, réunion équipe à 10h…",
            height=80,
        )

        score_vals = {1: "😞 1 — Très difficile", 2: "😐 2 — Difficile",
                      3: "🙂 3 — Correct", 4: "😊 4 — Bonne journée", 5: "🚀 5 — Excellente journée"}
        score_actuel = int(note_existante["score_engagement"]) if note_existante is not None and note_existante.get("score_engagement") else 3
        engagement = st.select_slider(
            "Comment s'est passée ta journée ?",
            options=[1, 2, 3, 4, 5],
            value=score_actuel,
            format_func=lambda x: score_vals[x],
        )

        if st.form_submit_button("💾 Sauvegarder la note", use_container_width=True):
            db.sauvegarder_note_journaliere(
                resume=resume,
                points_bloquants=blocages,
                plan_lendemain=lendemain,
                score_engagement=engagement,
            )
            if note_existante is not None:
                st.success("✅ Note mise à jour !")
            else:
                st.success("✅ Note sauvegardée !")
            st.rerun()

    if note_existante is not None:
        st.info("📝 Une note existe déjà pour aujourd'hui. Le formulaire la mettra à jour.", icon="ℹ️")


# ════════════════════════════════════════════════════════════
#  ONGLET 4 — MES ANALYTICS PERSONNELLES
# ════════════════════════════════════════════════════════════

def _onglet_analytics():
    st.markdown("### 📈 Mes Analytics Personnelles")

    # Sélecteur de période
    col1, col2 = st.columns(2)
    date_fin   = col1.date_input("Jusqu'au", value=date.today())
    date_debut = col2.date_input("Depuis le", value=date.today() - timedelta(days=30))

    if date_debut > date_fin:
        st.error("La date de début doit être antérieure à la date de fin.")
        return

    # Chargement des données
    with st.spinner("Chargement des données…"):
        df_taches  = db.get_taches(date_debut, date_fin)
        df_presence = db.get_presence(date_debut, date_fin)

    if df_taches.empty and df_presence.empty:
        st.info("Aucune donnée disponible pour cette période.")
        return

    # ── KPI personnels ────────────────────────────────────
    v_curr = kpi.velocite_semaine_courante(df_taches)
    v_prev = kpi.velocite_semaine_precedente(df_taches)
    lt     = kpi.lead_time_moyen(df_taches)
    sc     = kpi.score_complexite_semaine(df_taches)
    ponct  = kpi.indice_ponctualite(df_presence)
    effi   = kpi.taux_efficacite(df_taches, df_presence)
    taux_b = kpi.taux_blocage(df_taches)
    delta_v = kpi.delta_pct(v_curr, v_prev)

    c1, c2, c3 = st.columns(3)
    c1.metric("Tâches terminées (semaine)",  v_curr, delta=delta_v)
    c2.metric("Lead Time moyen",             f"{lt}h")
    c3.metric("Score complexité (semaine)",  sc)
    c1.metric("Indice de ponctualité",       f"{ponct}%")
    c2.metric("Taux d'efficacité",           f"{effi}%")
    c3.metric("Taux de blocage",             f"{taux_b}%", delta_color="inverse")

    st.divider()

    # ── Graphiques ────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        df_vel = kpi.velocite_hebdomadaire(df_taches)
        st.plotly_chart(charts.graphique_velocite(df_vel), use_container_width=True)

    with col_b:
        df_cat = kpi.repartition_par_categorie(df_taches)
        st.plotly_chart(charts.graphique_categories(df_cat), use_container_width=True)

    df_pres = kpi.heures_presence_par_jour(df_presence)
    st.plotly_chart(charts.graphique_presence(df_pres), use_container_width=True)

    df_lt_cat = kpi.lead_time_par_categorie(df_taches)
    st.plotly_chart(charts.graphique_lead_time(df_lt_cat), use_container_width=True)

    # ── Historique des tâches ─────────────────────────────
    st.divider()
    st.markdown("#### 📋 Historique complet")
    if not df_taches.empty:
        df_affichage = df_taches[[
            "cree_le", "titre", "categorie", "zone_usine", "statut", "complexite", "livrable"
        ]].copy()
        df_affichage["cree_le"] = df_affichage["cree_le"].dt.strftime("%d/%m/%Y %H:%M")
        df_affichage.columns = ["Créée le", "Titre", "Catégorie", "Zone", "Statut", "Cx", "Livrable"]
        st.dataframe(df_affichage, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune tâche sur cette période.")

    # ── Objectifs ─────────────────────────────────────────
    st.divider()
    st.markdown("#### 🎯 Mes Objectifs Stratégiques")
    _section_objectifs_employe()


def _section_objectifs_employe():
    """Affichage + gestion des objectifs côté employé."""
    df_obj = db.get_objectifs()

    if not df_obj.empty:
        for _, obj in df_obj.iterrows():
            statut_couleurs = {
                "EN_COURS": "#3b82f6", "EN_RISQUE": "#f59e0b",
                "ATTEINT": "#10b981",  "ABANDONNE": "#64748b",
            }
            c = statut_couleurs.get(obj["statut"], "#64748b")
            pct = int(obj["progression"])
            jours_restants = (obj["date_echeance"] - date.today()).days

            st.markdown(f"""
            <div style='background:#121828; border:1px solid rgba(255,255,255,0.07);
                        border-left:3px solid {c}; border-radius:10px;
                        padding:1rem 1.25rem; margin-bottom:1rem;'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <span style='color:#e2e8f0; font-weight:600;'>{obj['titre']}</span>
                    <span style='background:{c}22; color:{c}; padding:2px 10px;
                                 border-radius:100px; font-size:11px;'>{obj['statut']}</span>
                </div>
                <div style='color:#64748b; font-size:12px; margin:6px 0;'>
                    Échéance : {obj['date_echeance']} · {jours_restants} jour(s) restant(s)
                </div>
                <div style='background:#1a2235; border-radius:4px; height:8px; margin:8px 0;'>
                    <div style='background:{c}; width:{pct}%; height:8px; border-radius:4px;'></div>
                </div>
                <div style='color:{c}; font-size:12px; font-weight:600;'>{pct}%</div>
            </div>
            """, unsafe_allow_html=True)

            # Mise à jour inline
            with st.expander(f"✏️ Modifier « {obj['titre']} »"):
                with st.form(f"form_obj_{obj['obj_id']}"):
                    nouveau_pct = st.slider("Progression (%)", 0, 100, pct)
                    nouveau_statut = st.selectbox(
                        "Statut",
                        ["EN_COURS", "EN_RISQUE", "ATTEINT", "ABANDONNE"],
                        index=["EN_COURS", "EN_RISQUE", "ATTEINT", "ABANDONNE"].index(obj["statut"]),
                    )
                    if st.form_submit_button("Mettre à jour"):
                        db.maj_objectif(obj["obj_id"], nouveau_pct, nouveau_statut)
                        st.success("Objectif mis à jour !")
                        st.rerun()

    # Ajout d'un nouvel objectif
    st.markdown("---")
    with st.expander("➕ Créer un nouvel objectif"):
        with st.form("form_nouvel_objectif", clear_on_submit=True):
            titre_obj   = st.text_input("Titre de l'objectif *")
            desc_obj    = st.text_area("Description", height=60)
            echeance    = st.date_input("Date d'échéance", value=date.today() + timedelta(days=30))
            if st.form_submit_button("Créer l'objectif"):
                if not titre_obj.strip():
                    st.error("Le titre est obligatoire.")
                else:
                    db.creer_objectif(
                        titre=titre_obj.strip(),
                        description=desc_obj,
                        date_echeance=echeance,
                    )
                    st.success(f"🎯 Objectif « {titre_obj.strip()} » créé !")
                    st.rerun()


# ════════════════════════════════════════════════════════════
#  POINT D'ENTRÉE DE LA VUE
# ════════════════════════════════════════════════════════════

def afficher_vue_employe():
    st.markdown("""
    <div style='margin-bottom:1.5rem;'>
        <h1 style='color:#e2e8f0; font-size:1.6rem; font-weight:700; margin:0;'>
            👷 Espace Employé
        </h1>
        <p style='color:#64748b; font-size:13px; margin:4px 0 0;'>
            Toutes tes actions quotidiennes en un seul endroit
        </p>
    </div>
    """, unsafe_allow_html=True)

    onglet1, onglet2, onglet3, onglet4 = st.tabs([
        "🕐 Pointage",
        "✅ Mes Tâches",
        "📝 Note du Jour",
        "📈 Mes Analytics",
    ])

    with onglet1:
        _onglet_pointage()
    with onglet2:
        _onglet_taches()
    with onglet3:
        _onglet_note()
    with onglet4:
        _onglet_analytics()
