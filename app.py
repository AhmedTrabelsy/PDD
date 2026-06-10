# app.py
import streamlit as st

st.set_page_config(
    page_title="PPD — Tableau de Bord de Performance",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background-color: #0b0f1a; }
[data-testid="stSidebar"]          { background-color: #121828; border-right: 1px solid rgba(255,255,255,0.07); }
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }
[data-testid="stMetric"] {
    background: #121828;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 1rem 1.25rem;
}
[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 12px !important; }
[data-testid="stMetricValue"] { color: #e2e8f0 !important; }
[data-testid="stMetricDelta"] { font-size: 12px !important; }
.stButton > button {
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.1);
    background: #1a2235;
    color: #e2e8f0;
    transition: all 0.2s;
}
.stButton > button:hover { border-color: #3b82f6; background: rgba(59,130,246,0.15); }
.stTextInput > div > div > input,
.stTextArea  > div > div > textarea,
.stSelectbox > div > div {
    background: #121828 !important;
    border-color: rgba(255,255,255,0.1) !important;
    color: #e2e8f0 !important;
}
[data-testid="stDataFrame"] { border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; }
.stTabs [data-baseweb="tab-list"] { background: #121828; border-radius: 8px; padding: 4px; gap: 4px; }
.stTabs [data-baseweb="tab"]      { border-radius: 6px; color: #64748b; }
.stTabs [aria-selected="true"]    { background: #1a2235 !important; color: #e2e8f0 !important; }
hr { border-color: rgba(255,255,255,0.07); }
.stAlert { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

if "role"         not in st.session_state: st.session_state.role = None
if "pin_erreur"   not in st.session_state: st.session_state.pin_erreur = False


def page_connexion():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center;margin-bottom:2rem;'>
            <div style='font-size:3rem;'>📊</div>
            <h1 style='color:#e2e8f0;font-size:1.8rem;margin:0.5rem 0;'>Tableau de Bord de Performance</h1>
            <p style='color:#64748b;font-size:14px;'>Entrez votre code PIN pour accéder à votre espace</p>
        </div>""", unsafe_allow_html=True)

        with st.form("form_connexion", clear_on_submit=True):
            pin = st.text_input("Code PIN", type="password", max_chars=4,
                                placeholder="• • • •", label_visibility="collapsed")
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            btn_e = c1.form_submit_button("👷 Espace Employé", use_container_width=True)
            btn_m = c2.form_submit_button("📊 Vue Manager",    use_container_width=True)

        if btn_e or btn_m:
            p_e = st.secrets["auth"]["pin_employe"]
            p_m = st.secrets["auth"]["pin_manager"]
            if btn_e and pin == p_e:
                st.session_state.role = "employe";  st.session_state.pin_erreur = False; st.rerun()
            elif btn_m and pin == p_m:
                st.session_state.role = "manager";  st.session_state.pin_erreur = False; st.rerun()
            else:
                st.session_state.pin_erreur = True; st.rerun()

        if st.session_state.pin_erreur:
            st.error("❌ Code PIN incorrect.")

        st.markdown("<div style='text-align:center;margin-top:3rem;color:#334155;font-size:12px;'>"
                    "PPD v2.0 · Données hébergées sur Supabase · Africa/Tunis</div>",
                    unsafe_allow_html=True)


def afficher_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style='padding:1rem 0 1.5rem;'>
            <div style='font-size:1.5rem;font-weight:700;color:#e2e8f0;'>📊 PPD</div>
            <div style='font-size:11px;color:#64748b;letter-spacing:0.1em;text-transform:uppercase;'>
                Performance Dashboard
            </div>
        </div>""", unsafe_allow_html=True)

        role = st.session_state.role
        if role == "employe":
            st.markdown("**🟢 Connecté — Espace Employé**")
            st.markdown("""<div style='color:#64748b;font-size:12px;line-height:2;margin-top:8px;'>
            · 🕐 Pointage Entrée / Sortie<br>
            · ✅ Saisie de tâches<br>
            · 📁 Gestion des projets<br>
            · 📝 Note journalière<br>
            · 📈 Analytics personnelles
            </div>""", unsafe_allow_html=True)
        elif role == "manager":
            st.markdown("**🔵 Connecté — Vue Manager**")
            st.markdown("""<div style='color:#64748b;font-size:12px;line-height:2;margin-top:8px;'>
            · 📊 KPI Flash<br>
            · 🕐 Présence & ponctualité<br>
            · ✅ Tâches & blocages<br>
            · 📁 Suivi des projets<br>
            · 🎯 OKR · 📄 Rapport PDF
            </div>""", unsafe_allow_html=True)

        st.divider()
        if st.button("🔓 Se déconnecter", use_container_width=True):
            st.session_state.role = None
            st.session_state.pin_erreur = False
            st.rerun()


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