# app.py
# ─────────────────────────────────────────────────────────────
# Point d'entrée principal du PPD.
# Gère l'authentification par PIN et route vers les 3 vues.
# ─────────────────────────────────────────────────────────────

import streamlit as st

st.set_page_config(
    page_title="PPD — Tableau de Bord de Performance",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS global ────────────────────────────────────────────────
st.markdown("""
<style>
/* Fond principal */
[data-testid="stAppViewContainer"] { background-color: #0b0f1a; }
[data-testid="stSidebar"]          { background-color: #121828; border-right: 1px solid rgba(255,255,255,0.07); }

/* Masquer le menu hamburger et footer Streamlit */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

/* Métriques */
[data-testid="stMetric"] {
    background: #121828;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 1rem 1.25rem;
}
[data-testid="stMetricLabel"]  { color: #64748b !important; font-size: 12px !important; }
[data-testid="stMetricValue"]  { color: #e2e8f0 !important; }
[data-testid="stMetricDelta"]  { font-size: 12px !important; }

/* Boutons principaux */
.stButton > button {
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.1);
    background: #1a2235;
    color: #e2e8f0;
    transition: all 0.2s;
}
.stButton > button:hover {
    border-color: #3b82f6;
    background: rgba(59,130,246,0.15);
}

/* Inputs */
.stTextInput > div > div > input,
.stTextArea  > div > div > textarea,
.stSelectbox > div > div {
    background: #121828 !important;
    border-color: rgba(255,255,255,0.1) !important;
    color: #e2e8f0 !important;
}

/* Dataframe */
[data-testid="stDataFrame"] { border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: #121828; border-radius: 8px; padding: 4px; gap: 4px; }
.stTabs [data-baseweb="tab"]      { border-radius: 6px; color: #64748b; }
.stTabs [aria-selected="true"]    { background: #1a2235 !important; color: #e2e8f0 !important; }

/* Séparateur */
hr { border-color: rgba(255,255,255,0.07); }

/* Success / Error / Info */
.stAlert { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  ÉTAT DE SESSION — initialisation
# ════════════════════════════════════════════════════════════

if "role" not in st.session_state:
    st.session_state.role = None          # None | "employe" | "manager"
if "pin_tentative" not in st.session_state:
    st.session_state.pin_tentative = ""
if "pin_erreur" not in st.session_state:
    st.session_state.pin_erreur = False


# ════════════════════════════════════════════════════════════
#  PAGE DE CONNEXION
# ════════════════════════════════════════════════════════════

def page_connexion():
    # Centrer le formulaire
    col_g, col_c, col_d = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown("<br><br>", unsafe_allow_html=True)

        st.markdown("""
        <div style='text-align:center; margin-bottom:2rem;'>
            <div style='font-size:3rem;'>📊</div>
            <h1 style='color:#e2e8f0; font-size:1.8rem; margin:0.5rem 0;'>
                Tableau de Bord de Performance
            </h1>
            <p style='color:#64748b; font-size:14px;'>
                Entrez votre code PIN pour accéder à votre espace
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("form_connexion", clear_on_submit=True):
            pin = st.text_input(
                "Code PIN",
                type="password",
                max_chars=4,
                placeholder="• • • •",
                label_visibility="collapsed",
            )
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            btn_employe = col1.form_submit_button(
                "👷 Espace Employé",
                use_container_width=True,
            )
            btn_manager = col2.form_submit_button(
                "📊 Vue Manager",
                use_container_width=True,
            )

        if btn_employe or btn_manager:
            pin_employe = st.secrets["auth"]["pin_employe"]
            pin_manager = st.secrets["auth"]["pin_manager"]

            if btn_employe and pin == pin_employe:
                st.session_state.role = "employe"
                st.session_state.pin_erreur = False
                st.rerun()
            elif btn_manager and pin == pin_manager:
                st.session_state.role = "manager"
                st.session_state.pin_erreur = False
                st.rerun()
            else:
                st.session_state.pin_erreur = True
                st.rerun()

        if st.session_state.pin_erreur:
            st.error("❌ Code PIN incorrect. Veuillez réessayer.")

        st.markdown("""
        <div style='text-align:center; margin-top:3rem; color:#334155; font-size:12px;'>
            PPD v2.0 · Sécurisé · Données hébergées sur Supabase
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  BARRE LATÉRALE
# ════════════════════════════════════════════════════════════

def afficher_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style='padding:1rem 0 1.5rem;'>
            <div style='font-size:1.5rem; font-weight:700; color:#e2e8f0;'>📊 PPD</div>
            <div style='font-size:11px; color:#64748b; letter-spacing:0.1em; text-transform:uppercase;'>
                Performance Dashboard
            </div>
        </div>
        """, unsafe_allow_html=True)

        role = st.session_state.role
        if role == "employe":
            st.markdown("**🟢 Connecté en tant qu'Employé**")
        elif role == "manager":
            st.markdown("**🔵 Connecté en tant que Manager**")

        st.divider()

        if role == "employe":
            st.markdown("""
            <div style='color:#64748b; font-size:12px; line-height:2;'>
            📌 <b style='color:#94a3b8;'>Espace Employé</b><br>
            · Pointage Entrée / Sortie<br>
            · Saisie rapide de tâches<br>
            · Tableau du jour<br>
            · Note journalière<br>
            · Mes analytics personnelles
            </div>
            """, unsafe_allow_html=True)
        elif role == "manager":
            st.markdown("""
            <div style='color:#64748b; font-size:12px; line-height:2;'>
            📌 <b style='color:#94a3b8;'>Vue Manager</b><br>
            · KPI Flash<br>
            · Vélocité hebdomadaire<br>
            · Heatmap des zones<br>
            · Objectifs stratégiques<br>
            · Rapport PDF
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        if st.button("🔓 Se déconnecter", use_container_width=True):
            st.session_state.role = None
            st.session_state.pin_erreur = False
            st.rerun()

        st.markdown("""
        <div style='position:absolute; bottom:2rem; left:1rem; right:1rem;
                    color:#334155; font-size:11px; text-align:center;'>
            PPD v2.0 · © 2025
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  ROUTEUR PRINCIPAL
# ════════════════════════════════════════════════════════════

def main():
    if st.session_state.role is None:
        page_connexion()
        return

    afficher_sidebar()

    if st.session_state.role == "employe":
        from views.employee import afficher_vue_employe
        afficher_vue_employe()

    elif st.session_state.role == "manager":
        from views.manager import afficher_vue_manager
        afficher_vue_manager()


if __name__ == "__main__":
    main()
