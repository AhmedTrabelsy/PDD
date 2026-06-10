# components/charts.py
from __future__ import annotations
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#94a3b8", font_family="sans-serif",
    margin=dict(l=20, r=20, t=40, b=20),
    colorway=["#3b82f6", "#06b6d4", "#8b5cf6",
              "#10b981", "#f59e0b", "#ef4444"],
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)",
               linecolor="rgba(255,255,255,0.1)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)",
               linecolor="rgba(255,255,255,0.1)"),
)
COULEUR_STATUT = {"TERMINE": "#10b981", "EN_COURS": "#3b82f6",
                  "BLOQUE": "#ef4444", "A_FAIRE": "#64748b"}


def _empty(titre: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text="Pas encore de données", showarrow=False,
                       font=dict(color="#64748b", size=14), xref="paper", yref="paper", x=0.5, y=0.5)
    fig.update_layout(title=titre, **THEME)
    return fig


def _theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(**THEME)
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
    return fig


def graphique_velocite(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty("Vélocité hebdomadaire")
    fig = go.Figure()
    fig.add_bar(x=df["semaine"].astype(str), y=df["nb_terminees"],
                name="Tâches terminées", marker_color="#3b82f6", marker_opacity=0.85)
    fig.add_scatter(x=df["semaine"].astype(str), y=df["score_complexite"],
                    name="Score complexité", mode="lines+markers",
                    line=dict(color="#f59e0b", width=2), marker=dict(size=6), yaxis="y2")
    fig.update_layout(
        title="Vélocité hebdomadaire",
        yaxis2=dict(overlaying="y", side="right", showgrid=False,
                    title="Score complexité", color="#f59e0b"),
        legend=dict(orientation="h", y=1.1), barmode="group",
    )
    return _theme(fig)


def graphique_heatmap_zones(pivot: pd.DataFrame) -> go.Figure:
    if pivot.empty:
        return _empty("Répartition par zone et par jour")
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale="Blues", showscale=True,
        hovertemplate="%{y} — %{x} : %{z} tâche(s)<extra></extra>",
    ))
    fig.update_layout(title="Carte d'intervention par zone et jour")
    return _theme(fig)


def graphique_categories(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty("Types d'interventions")
    fig = px.pie(df, names="categorie", values="nb", title="Types d'interventions",
                 color_discrete_sequence=[
                     "#3b82f6", "#06b6d4", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444"],
                 hole=0.4)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return _theme(fig)


def graphique_lead_time(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty("Lead Time moyen par catégorie")
    fig = px.bar(df, x="lead_time_h", y="categorie", orientation="h",
                 title="Lead Time moyen par catégorie (heures)",
                 labels={"lead_time_h": "Heures", "categorie": ""},
                 color="lead_time_h", color_continuous_scale="Blues")
    fig.update_layout(showlegend=False, coloraxis_showscale=False)
    return _theme(fig)


def graphique_presence(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty("Temps de présence quotidien")
    fig = go.Figure()
    fig.add_scatter(x=df["date_jour"].astype(str), y=df["heures_presentes"],
                    mode="lines+markers", fill="tozeroy",
                    fillcolor="rgba(59,130,246,0.15)",
                    line=dict(color="#3b82f6", width=2), marker=dict(size=7),
                    hovertemplate="%{x} : %{y:.1f}h<extra></extra>")
    fig.add_hline(y=8, line_dash="dot", line_color="#64748b",
                  annotation_text="8h théoriques", annotation_position="bottom right")
    fig.update_layout(title="Temps de présence quotidien",
                      yaxis_title="Heures")
    return _theme(fig)


def graphique_gauge_efficacite(valeur: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=valeur,
        number={"suffix": "%", "font": {"size": 28, "color": "#e2e8f0"}},
        title={"text": "Taux d'efficacité opérationnelle",
               "font": {"color": "#94a3b8", "size": 13}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#64748b"},
            "bar": {"color": "#3b82f6"},
            "bgcolor": "rgba(255,255,255,0.05)",
            "bordercolor": "rgba(255,255,255,0.1)",
            "steps": [
                {"range": [0, 40],   "color": "rgba(239,68,68,0.15)"},
                {"range": [40, 70],  "color": "rgba(245,158,11,0.15)"},
                {"range": [70, 100], "color": "rgba(16,185,129,0.15)"},
            ],
            "threshold": {"line": {"color": "#10b981", "width": 3}, "value": 75},
        },
    ))
    fig.update_layout(
        height=220, **{k: v for k, v in THEME.items() if k not in ("xaxis", "yaxis")})
    return fig


def graphique_temps_projets(df: pd.DataFrame) -> go.Figure:
    """Bar chart horizontal : heures cumulées par projet."""
    if df.empty:
        return _empty("Temps par projet")
    fig = px.bar(df, x="heures", y="projet_nom", orientation="h",
                 title="Heures cumulées par projet",
                 labels={"heures": "Heures", "projet_nom": ""},
                 color="heures", color_continuous_scale="Blues",
                 text="heures")
    fig.update_traces(texttemplate="%{text:.1f}h", textposition="outside")
    fig.update_layout(showlegend=False, coloraxis_showscale=False)
    return _theme(fig)


def graphique_velocite_projets(df: pd.DataFrame) -> go.Figure:
    """Line chart : tâches terminées par projet par semaine."""
    if df.empty:
        return _empty("Vélocité par projet")
    fig = px.line(df, x="semaine", y="nb_taches", color="projet_nom",
                  title="Tâches terminées par projet (hebdo)",
                  labels={"semaine": "Semaine",
                          "nb_taches": "Tâches", "projet_nom": "Projet"},
                  markers=True)
    return _theme(fig)
