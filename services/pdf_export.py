# services/pdf_export.py
# ─────────────────────────────────────────────────────────────
# Génération du rapport PDF hebdomadaire via fpdf2.
# ─────────────────────────────────────────────────────────────

from __future__ import annotations

import io
from datetime import date, timedelta

import pandas as pd
from fpdf import FPDF

from services import kpi_engine as kpi


class RapportPDF(FPDF):
    """Classe PDF personnalisée avec en-tête et pied de page."""

    def __init__(self, periode: str):
        super().__init__()
        self.periode = periode
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()

    def header(self):
        # Bande bleue en haut
        self.set_fill_color(59, 130, 246)
        self.rect(0, 0, 210, 14, "F")
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(255, 255, 255)
        self.set_y(3)
        self.cell(0, 8, "Tableau de Bord de Performance Personnelle — PPD", align="C")
        self.set_y(18)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, f"Rapport généré le {date.today().strftime('%d/%m/%Y')} — Page {self.page_no()}", align="C")

    def titre_section(self, texte: str):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(59, 130, 246)
        self.set_fill_color(235, 243, 255)
        self.cell(0, 9, f"  {texte}", ln=True, fill=True)
        self.ln(2)

    def kpi_box(self, label: str, valeur: str, delta: str = ""):
        x = self.get_x()
        y = self.get_y()
        self.set_fill_color(18, 24, 40)
        self.rect(x, y, 60, 22, "F")
        self.set_xy(x + 2, y + 3)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(100, 116, 139)
        self.cell(56, 5, label.upper())
        self.set_xy(x + 2, y + 9)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(226, 232, 240)
        self.cell(56, 8, valeur)
        if delta:
            self.set_xy(x + 2, y + 17)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(16, 185, 129)
            self.cell(56, 4, delta)
        self.set_xy(x + 65, y)

    def ligne_tableau(self, colonnes: list[str], largeurs: list[int], grise: bool = False):
        if grise:
            self.set_fill_color(245, 247, 250)
        else:
            self.set_fill_color(255, 255, 255)
        self.set_text_color(30, 30, 30)
        self.set_font("Helvetica", "", 9)
        for val, larg in zip(colonnes, largeurs):
            self.cell(larg, 7, str(val)[:30], border="B", fill=True)
        self.ln()

    def en_tete_tableau(self, colonnes: list[str], largeurs: list[int]):
        self.set_fill_color(59, 130, 246)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 9)
        for col, larg in zip(colonnes, largeurs):
            self.cell(larg, 8, col, fill=True)
        self.ln()


def generer_rapport(
    df_taches: pd.DataFrame,
    df_presence: pd.DataFrame,
    df_notes: pd.DataFrame,
    df_objectifs: pd.DataFrame,
    date_debut: date,
    date_fin: date,
) -> bytes:
    """
    Génère le rapport PDF et retourne les bytes (utilisables avec st.download_button).
    """
    periode = f"{date_debut.strftime('%d/%m/%Y')} – {date_fin.strftime('%d/%m/%Y')}"
    pdf = RapportPDF(periode)

    # ── Titre principal ────────────────────────────────────
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(11, 15, 26)
    pdf.rect(0, 14, 210, 35, "F")
    pdf.set_xy(10, 20)
    pdf.cell(0, 10, "Rapport de Performance Hebdomadaire")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(148, 163, 184)
    pdf.set_xy(10, 33)
    pdf.cell(0, 8, f"Période : {periode}")
    pdf.set_y(55)

    # ── KPI Flash ─────────────────────────────────────────
    pdf.titre_section("📊  Indicateurs Clés de Performance")
    pdf.set_y(pdf.get_y() + 2)
    x_start = pdf.get_x()

    v_curr = kpi.velocite_semaine_courante(df_taches)
    lt     = kpi.lead_time_moyen(df_taches)
    sc     = kpi.score_complexite_semaine(df_taches)
    ponct  = kpi.indice_ponctualite(df_presence)

    pdf.kpi_box("Tâches terminées", str(v_curr), "Cette semaine")
    pdf.kpi_box("Lead Time moyen", f"{lt}h", "30 derniers jours")
    pdf.kpi_box("Score complexité", str(sc), "Cette semaine")
    pdf.set_xy(x_start, pdf.get_y() + 25)
    pdf.kpi_box("Indice ponctualité", f"{ponct}%", "Régularité horaire")
    effi = kpi.taux_efficacite(df_taches, df_presence)
    pdf.kpi_box("Taux d'efficacité", f"{effi}%", "Temps utilisé / présent")
    bloc = kpi.taux_blocage(df_taches)
    pdf.kpi_box("Taux de blocage", f"{bloc}%", "Tâches bloquées")
    pdf.set_y(pdf.get_y() + 30)

    # ── Tableau des tâches ────────────────────────────────
    pdf.titre_section("✅  Journal des Tâches")
    if not df_taches.empty:
        cols   = ["Titre", "Catégorie", "Zone", "Statut", "Cx"]
        widths = [70, 35, 35, 25, 10]
        pdf.en_tete_tableau(cols, widths)
        for i, (_, row) in enumerate(df_taches.iterrows()):
            pdf.ligne_tableau(
                [row["titre"], row["categorie"], row["zone_usine"], row["statut"], row["complexite"]],
                widths,
                grise=(i % 2 == 0),
            )
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 8, "Aucune tâche enregistrée pour cette période.", ln=True)

    pdf.ln(5)

    # ── Objectifs ─────────────────────────────────────────
    if not df_objectifs.empty:
        pdf.titre_section("🎯  Objectifs Stratégiques")
        for _, obj in df_objectifs.iterrows():
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.cell(0, 6, f"{obj['titre']}", ln=True)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(0, 5, f"Progression : {obj['progression']}%  |  Échéance : {obj['date_echeance']}  |  Statut : {obj['statut']}", ln=True)
            # Barre de progression
            bw = 160
            pdf.set_fill_color(30, 41, 59)
            pdf.rect(pdf.get_x(), pdf.get_y(), bw, 5, "F")
            pdf.set_fill_color(59, 130, 246)
            pdf.rect(pdf.get_x(), pdf.get_y(), bw * obj["progression"] / 100, 5, "F")
            pdf.ln(9)

    # ── Notes ─────────────────────────────────────────────
    if not df_notes.empty:
        pdf.titre_section("📝  Notes Journalières")
        for _, note in df_notes.iterrows():
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(59, 130, 246)
            pdf.cell(0, 6, str(note.get("date_jour", "")), ln=True)
            for champ, label in [("resume", "Résumé"), ("points_bloquants", "Blocages"), ("plan_lendemain", "Demain")]:
                if note.get(champ):
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.set_text_color(80, 80, 80)
                    pdf.cell(30, 5, f"{label} :")
                    pdf.set_font("Helvetica", "", 8)
                    pdf.set_text_color(30, 30, 30)
                    pdf.multi_cell(0, 5, str(note[champ])[:200])
            pdf.ln(3)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
