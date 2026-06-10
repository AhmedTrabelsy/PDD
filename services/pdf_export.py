# services/pdf_export.py
from __future__ import annotations
import io
from datetime import date
import pandas as pd
from fpdf import FPDF
from services import kpi_engine as kpi


class RapportPDF(FPDF):
    def __init__(self, periode: str):
        super().__init__()
        self.periode = periode
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()

    def header(self):
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

    def kpi_ligne(self, label: str, valeur: str, delta: str = ""):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 116, 139)
        self.cell(80, 6, label)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(30, 30, 30)
        self.cell(40, 6, valeur)
        if delta:
            self.set_font("Helvetica", "", 8)
            self.set_text_color(16, 185, 129)
            self.cell(0, 6, delta)
        self.ln()

    def en_tete_tableau(self, colonnes: list[str], largeurs: list[int]):
        self.set_fill_color(59, 130, 246)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 8)
        for col, larg in zip(colonnes, largeurs):
            self.cell(larg, 7, col, fill=True)
        self.ln()

    def ligne_tableau(self, vals: list, largeurs: list[int], grise: bool = False):
        self.set_fill_color(245, 247, 250 if grise else 255)
        self.set_text_color(30, 30, 30)
        self.set_font("Helvetica", "", 8)
        for val, larg in zip(vals, largeurs):
            self.cell(larg, 6, str(val)[:35], border="B", fill=grise)
        self.ln()

    def barre_progression(self, pct: int, couleur_rgb=(59, 130, 246)):
        bw = 160
        self.set_fill_color(220, 230, 240)
        self.rect(self.get_x(), self.get_y(), bw, 5, "F")
        self.set_fill_color(*couleur_rgb)
        self.rect(self.get_x(), self.get_y(), bw * pct / 100, 5, "F")
        self.ln(8)


def generer_rapport(
    df_taches: pd.DataFrame,
    df_presence: pd.DataFrame,
    df_notes: pd.DataFrame,
    df_objectifs: pd.DataFrame,
    date_debut: date,
    date_fin: date,
) -> bytes:
    periode = f"{date_debut.strftime('%d/%m/%Y')} – {date_fin.strftime('%d/%m/%Y')}"
    pdf = RapportPDF(periode)

    # Titre
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 30, 30)
    pdf.set_y(20)
    pdf.cell(0, 10, "Rapport de Performance", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, f"Période : {periode}", ln=True, align="C")
    pdf.ln(8)

    # KPIs
    pdf.titre_section("Indicateurs Clés de Performance")
    pdf.kpi_ligne("Tâches terminées (semaine)",    str(kpi.velocite_semaine_courante(df_taches)))
    pdf.kpi_ligne("Lead Time moyen (30j)",         f"{kpi.lead_time_moyen(df_taches)}h")
    pdf.kpi_ligne("Score complexité (semaine)",    str(kpi.score_complexite_semaine(df_taches)))
    pdf.kpi_ligne("Indice de ponctualité",         f"{kpi.indice_ponctualite(df_presence)}%")
    pdf.kpi_ligne("Taux d'efficacité",             f"{kpi.taux_efficacite(df_taches, df_presence)}%")
    pdf.kpi_ligne("Taux de blocage",               f"{kpi.taux_blocage(df_taches)}%")
    pdf.ln(4)

    # Projets
    df_proj = kpi.temps_par_projet(df_taches)
    if not df_proj.empty:
        pdf.titre_section("Temps par Projet")
        pdf.en_tete_tableau(["Projet", "Heures", "Tâches", "Score Cx"], [80, 30, 25, 25])
        for i, (_, row) in enumerate(df_proj.iterrows()):
            pdf.ligne_tableau(
                [row["projet_nom"], f"{row['heures']}h", row["nb_taches"], row["score_cx"]],
                [80, 30, 25, 25], grise=(i % 2 == 0),
            )
        pdf.ln(4)

    # Tâches
    if not df_taches.empty:
        pdf.titre_section("Journal des Tâches")
        pdf.en_tete_tableau(["Titre", "Catégorie", "Zone", "Statut", "Cx"], [65, 35, 30, 22, 10])
        for i, (_, row) in enumerate(df_taches.iterrows()):
            pdf.ligne_tableau(
                [row["titre"], row["categorie"], row["zone_usine"], row["statut"], row["complexite"]],
                [65, 35, 30, 22, 10], grise=(i % 2 == 0),
            )
        pdf.ln(4)

    # Objectifs
    if not df_objectifs.empty:
        pdf.titre_section("Objectifs Stratégiques")
        for _, obj in df_objectifs.iterrows():
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(30, 30, 30)
            pdf.cell(0, 5, f"{obj['titre']}  —  {obj['statut']}  —  {obj['progression']}%", ln=True)
            pdf.barre_progression(int(obj["progression"]))

    # Notes
    if not df_notes.empty:
        pdf.titre_section("Notes Journalières")
        for _, note in df_notes.iterrows():
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(59, 130, 246)
            pdf.cell(0, 5, str(note.get("date_jour", "")), ln=True)
            for champ, label in [("resume", "Résumé"), ("points_bloquants", "Blocages"), ("plan_lendemain", "Demain")]:
                if note.get(champ):
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.set_text_color(80, 80, 80)
                    pdf.cell(28, 5, f"{label} :")
                    pdf.set_font("Helvetica", "", 8)
                    pdf.set_text_color(30, 30, 30)
                    pdf.multi_cell(0, 5, str(note[champ])[:300])
            pdf.ln(2)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()