# components/charts.py
# ─────────────────────────────────────────────────────────────
# Constructeurs de graphiques Plotly réutilisables.
# Tous les graphiques ont le même thème sombre.
# ─────────────────────────────────────────────────────────────

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Thème partagé ─────────────────────────────────────────────
THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#94a3b8",
    font_family="sans-serif",
    margin=dict(l=20, r=20, t=40, b=20),
    colorway=["#3b82f6", "#06b6d4", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444"],
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.1)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.1)"),
)

COULEUR_STATUT = {
    "TERMINE":  "#10b981",
    "EN_COURS": "#3b82f6",
    "BLOQUE":   "#ef4444",
    "A_FAIRE":  "#64748b",
}


def _appliquer_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(**THEME)
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
    return fig


# ════════════════════════════════════════════════════════════
#  GRAPHIQUE DE VÉLOCITÉ HEBDOMADAIRE
# ════════════════════════════════════════════════════════════

def graphique_velocite(df: pd.DataFrame) -> go.Figure:
    """
    Bar chart + line : tâches terminées par semaine + score de complexité.
    df doit avoir les colonnes : semaine, nb_terminees, score_complexite.
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Pas encore de données", showarrow=False,
                           font=dict(color="#64748b", size=14), xref="paper", yref="paper", x=0.5, y=0.5)
        return _appliquer_theme(fig)

    fig = go.Figure()
    fig.add_bar(
        x=df["semaine"].astype(str),
        y=df["nb_terminees"],
        name="Tâches terminées",
        marker_color="#3b82f6",
        marker_opacity=0.85,
    )
    fig.add_scatter(
        x=df["semaine"].astype(str),
        y=df["score_complexite"],
        name="Score complexité",
        mode="lines+markers",
        line=dict(color="#f59e0b", width=2),
        marker=dict(size=6),
        yaxis="y2",
    )
    fig.update_layout(
        title="Vélocité hebdomadaire",
        yaxis2=dict(
            overlaying="y", side="right",
            showgrid=False, title="Score complexité",
            color="#f59e0b",
        ),
        legend=dict(orientation="h", y=1.1),
        barmode="group",
    )
    return _appliquer_theme(fig)


# ════════════════════════════════════════════════════════════
#  HEATMAP — ZONE × JOUR DE SEMAINE
# ════════════════════════════════════════════════════════════

def graphique_heatmap_zones(pivot: pd.DataFrame) -> go.Figure:
    """
    Heatmap des interventions par zone et par jour de semaine.
    `pivot` est un DataFrame avec les zones en index et les jours en colonnes.
    """
    if pivot.empty:
        fig = go.Figure()
        fig.add_annotation(text="Pas encore de données", showarrow=False,
                           font=dict(color="#64748b", size=14), xref="paper", yref="paper", x=0.5, y=0.5)
        return _appliquer_theme(fig)

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale="Blues",
        showscale=True,
        hoverongaps=False,
        hovertemplate="%{y} — %{x} : %{z} tâche(s)<extra></extra>",
    ))
    fig.update_layout(title="Répartition par zone et par jour")
    return _appliquer_theme(fig)


# ════════════════════════════════════════════════════════════
#  PIE CHART — RÉPARTITION PAR CATÉGORIE
# ════════════════════════════════════════════════════════════

def graphique_categories(df: pd.DataFrame) -> go.Figure:
    """
    df doit avoir les colonnes : categorie, nb.
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Pas encore de données", showarrow=False,
                           font=dict(color="#64748b", size=14), xref="paper", yref="paper", x=0.5, y=0.5)
        return _appliquer_theme(fig)

    fig = px.pie(
        df, names="categorie", values="nb",
        title="Types d'interventions",
        color_discrete_sequence=["#3b82f6", "#06b6d4", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444"],
        hole=0.4,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return _appliquer_theme(fig)


# ════════════════════════════════════════════════════════════
#  BAR CHART — LEAD TIME PAR CATÉGORIE
# ════════════════════════════════════════════════════════════

def graphique_lead_time(df: pd.DataFrame) -> go.Figure:
    """
    df doit avoir les colonnes : categorie, lead_time_h.
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Pas encore de données", showarrow=False,
                           font=dict(color="#64748b", size=14), xref="paper", yref="paper", x=0.5, y=0.5)
        return _appliquer_theme(fig)

    fig = px.bar(
        df, x="lead_time_h", y="categorie",
        orientation="h",
        title="Lead Time moyen par catégorie (heures)",
        labels={"lead_time_h": "Heures", "categorie": ""},
        color="lead_time_h",
        color_continuous_scale="Blues",
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False)
    return _appliquer_theme(fig)


# ════════════════════════════════════════════════════════════
#  LINE CHART — HEURES DE PRÉSENCE PAR JOUR
# ════════════════════════════════════════════════════════════

def graphique_presence(df: pd.DataFrame) -> go.Figure:
    """
    df doit avoir les colonnes : date_jour, heures_presentes.
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Pas encore de données", showarrow=False,
                           font=dict(color="#64748b", size=14), xref="paper", yref="paper", x=0.5, y=0.5)
        return _appliquer_theme(fig)

    fig = go.Figure()
    fig.add_scatter(
        x=df["date_jour"].astype(str),
        y=df["heures_presentes"],
        mode="lines+markers",
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.15)",
        line=dict(color="#3b82f6", width=2),
        marker=dict(size=7, color="#3b82f6"),
        name="Heures présent",
        hovertemplate="%{x} : %{y:.1f}h<extra></extra>",
    )
    # Ligne de référence 8h
    fig.add_hline(y=8, line_dash="dot", line_color="#64748b",
                  annotation_text="8h théoriques", annotation_position="bottom right")
    fig.update_layout(title="Temps de présence quotidien", yaxis_title="Heures")
    return _appliquer_theme(fig)


# ════════════════════════════════════════════════════════════
#  GAUGE — TAUX D'EFFICACITÉ
# ════════════════════════════════════════════════════════════

def graphique_gauge_efficacite(valeur: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valeur,
        number={"suffix": "%", "font": {"size": 28, "color": "#e2e8f0"}},
        title={"text": "Taux d'efficacité opérationnelle", "font": {"color": "#94a3b8", "size": 13}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#64748b"},
            "bar": {"color": "#3b82f6"},
            "bgcolor": "rgba(255,255,255,0.05)",
            "bordercolor": "rgba(255,255,255,0.1)",
            "steps": [
                {"range": [0, 40],  "color": "rgba(239,68,68,0.15)"},
                {"range": [40, 70], "color": "rgba(245,158,11,0.15)"},
                {"range": [70, 100],"color": "rgba(16,185,129,0.15)"},
            ],
            "threshold": {"line": {"color": "#10b981", "width": 3}, "value": 75},
        },
    ))
    fig.update_layout(height=220, **{k: v for k, v in THEME.items()
                                     if k not in ("xaxis", "yaxis")})
    return fig
