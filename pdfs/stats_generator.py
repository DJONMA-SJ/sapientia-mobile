"""
GÉNÉRATEUR DE FICHE STATISTIQUE DE CLASSE (PDF)
Reproduction fidèle de la feuille de statistiques (Effectifs, Échec/Réussite, Mentions/Sanctions, Min/Max)
"""
import os
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# Graphiques natifs ReportLab
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart

NOMS_TRIMESTRES = {1: "PREMIER", 2: "DEUXIÈME", 3: "TROISIÈME"}
GRIS_ENTETE = colors.HexColor("#D9D9D9")
GRIS_LIGNE = colors.HexColor("#F2F2F2")


def _e(txt):
    return escape(str(txt)) if txt is not None else ""


def _fmt_pct(val, total):
    if not total or total == 0:
        return "0%"
    pct = (val / total) * 100
    return f"{pct:.0f}%" if pct.is_integer() else f"{pct:.1f}%".replace(".", ",")


def _creer_graphique_barres(donnees, series_labels, categories, largeur=8*cm, hauteur=4.5*cm):
    """
    Crée un histogramme natif ReportLab pour les tableaux d'effectifs / réussite.
    """
    d = Drawing(largeur, hauteur)
    chart = VerticalBarChart()
    chart.x = 0.5 * cm
    chart.y = 0.5 * cm
    chart.height = hauteur - 1.2 * cm
    chart.width = largeur - 1.0 * cm
    chart.data = donnees
    chart.categoryAxis.categoryNames = categories
    chart.categoryAxis.labels.fontSize = 6
    chart.categoryAxis.labels.dy = -10
    chart.valueAxis.valueMin = 0
    chart.valueAxis.labels.fontSize = 6
    
    # Couleurs des séries
    couleurs = [colors.HexColor("#4F81BD"), colors.HexColor("#F29559"), colors.HexColor("#A5A5A5")]
    for i in range(len(donnees)):
        chart.bars[i].fillColor = couleurs[i % len(couleurs)]

    d.add(chart)
    return d


def generer_fiche_statistiques_pdf(classe_nom, trim, stats, params_etab, chemin_pdf):
    doc = SimpleDocTemplate(
        chemin_pdf,
        pagesize=A4,
        leftMargin=1.0 * cm,
        rightMargin=1.0 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm
    )
    story = []

    # Styles
    base = getSampleStyleSheet()["Normal"]
    st = ParagraphStyle("st", parent=base, fontSize=8, leading=10)
    st_b = ParagraphStyle("st_b", parent=st, fontName="Helvetica-Bold")
    st_c = ParagraphStyle("st_c", parent=st, alignment=1)
    st_cb = ParagraphStyle("st_cb", parent=st_b, alignment=1)
    st_etab = ParagraphStyle("st_etab", parent=st_b, fontSize=11, leading=13, alignment=1)
    st_titre = ParagraphStyle("st_titre", parent=st_b, fontSize=12, leading=14, alignment=1)

    # 1. En-tête Institutionnel
    nom_etab = _e(params_etab.get("etablissement_nom", "COLLÈGE NOTRE DAME DE LA SAGESSE"))
    annee = _e(params_etab.get("annee_scolaire", "2025-2026"))
    
    story.append(Paragraph(nom_etab, st_etab))
    story.append(Spacer(1, 0.2 * cm))
    
    titre_text = f"STATISTIQUES DU {NOMS_TRIMESTRES.get(trim, '')} TRIMESTRE DE LA CLASSE DE {_e(classe_nom)}"
    story.append(Paragraph(f"<b><u>{titre_text}</u></b>", st_titre))
    story.append(Paragraph(f"Année scolaire : {annee}", st_c))
    story.append(Spacer(1, 0.4 * cm))

    # 2. Tableau 1 : RAPPORT DES EFFECTIFS
    total_eff = stats["effectif_total"]
    g_count = stats["garcons"]
    f_count = stats["filles"]
    red_count = stats["redoublants"]
    non_red = total_eff - red_count

    data_eff = [
        [Paragraph("<b>RAPPORT DES EFFECTIFS</b>", st_cb), "", ""],
        [Paragraph("", st), Paragraph("<b>Effectif</b>", st_cb), Paragraph("<b>Pourcentage</b>", st_cb)],
        [Paragraph("GARCONS", st_b), Paragraph(str(g_count), st_c), Paragraph(_fmt_pct(g_count, total_eff), st_c)],
        [Paragraph("FILLES", st_b), Paragraph(str(f_count), st_c), Paragraph(_fmt_pct(f_count, total_eff), st_c)],
        [Paragraph("TOTAL", st_b), Paragraph(str(total_eff), st_cb), Paragraph("100%", st_cb)],
        [Paragraph("Redoublant", st_b), Paragraph(str(red_count), st_c), Paragraph(_fmt_pct(red_count, total_eff), st_c)],
        [Paragraph("Non redoublant", st_b), Paragraph(str(non_red), st_c), Paragraph(_fmt_pct(non_red, total_eff), st_c)],
    ]

    t_eff = Table(data_eff, colWidths=[3.5 * cm, 2.2 * cm, 2.3 * cm])
    t_eff.setStyle(TableStyle([
        ("SPAN", (0, 0), (2, 0)),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("BACKGROUND", (0, 0), (2, 0), colors.HexColor("#336699")),
        ("TEXTCOLOR", (0, 0), (2, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), GRIS_ENTETE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    # Graphique Effectifs
    graph_eff = _creer_graphique_barres(
        [[g_count, f_count, total_eff, red_count, non_red]],
        ["Effectif"],
        ["GARCONS", "FILLES", "TOTAL", "Red.", "Non Red."]
    )

    t_bloc_eff = Table([[t_eff, graph_eff]], colWidths=[8.5 * cm, 9.5 * cm])
    t_bloc_eff.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(t_bloc_eff)
    story.append(Spacer(1, 0.4 * cm))

    # 3. Tableau 2 : RAPPORT D'ÉCHEC - RÉUSSITE
    reu_g = stats["reussite"]["M"]
    reu_f = stats["reussite"]["F"]
    reu_tot = stats["reussite"]["total"]
    ech_g = stats["echec"]["M"]
    ech_f = stats["echec"]["F"]
    ech_tot = stats["echec"]["total"]

    data_ech = [
        [Paragraph("<b>RAPPORT D'ECHEC - REUSSITE</b>", st_cb), "", ""],
        [Paragraph("", st), Paragraph("<b>ECHEC</b>", st_cb), Paragraph("<b>REUSSITE</b>", st_cb)],
        [Paragraph("GARCONS", st_b), Paragraph(str(ech_g), st_c), Paragraph(str(reu_g), st_c)],
        [Paragraph("FILLES", st_b), Paragraph(str(ech_f), st_c), Paragraph(str(reu_f), st_c)],
        [Paragraph("TOTAL", st_b), Paragraph(str(ech_tot), st_cb), Paragraph(str(reu_tot), st_cb)],
        [Paragraph("POURCENTAGE", st_b), Paragraph(_fmt_pct(ech_tot, total_eff), st_cb), Paragraph(_fmt_pct(reu_tot, total_eff), st_cb)],
    ]

    t_ech = Table(data_ech, colWidths=[3.5 * cm, 2.2 * cm, 2.3 * cm])
    t_ech.setStyle(TableStyle([
        ("SPAN", (0, 0), (2, 0)),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("BACKGROUND", (0, 0), (2, 0), colors.HexColor("#336699")),
        ("TEXTCOLOR", (0, 0), (2, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), GRIS_ENTETE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    graph_ech = _creer_graphique_barres(
        [[ech_g, ech_f, ech_tot], [reu_g, reu_f, reu_tot]],
        ["Échec", "Réussite"],
        ["GARCONS", "FILLES", "TOTAL"]
    )

    t_bloc_ech = Table([[t_ech, graph_ech]], colWidths=[8.5 * cm, 9.5 * cm])
    t_bloc_ech.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(t_bloc_ech)
    story.append(Spacer(1, 0.4 * cm))

    # 4. Tableau 3 : SANCTIONS ET APPRÉCIATIONS
    m_dict = stats["mentions"]
    data_sanc = [
        [Paragraph("<b>SANCTIONS ET APPRECIATIONS</b>", st_cb), "", "", ""],
        [Paragraph("", st), Paragraph("<b>GARCONS</b>", st_cb), Paragraph("<b>FILLES</b>", st_cb), Paragraph("<b>TOTAL</b>", st_cb)],
        [Paragraph("Blâme", st_b), Paragraph(str(m_dict["Blâme"]["M"]), st_c), Paragraph(str(m_dict["Blâme"]["F"]), st_c), Paragraph(str(m_dict["Blâme"]["total"]), st_cb)],
        [Paragraph("Avertissement", st_b), Paragraph(str(m_dict["Avertissement"]["M"]), st_c), Paragraph(str(m_dict["Avertissement"]["F"]), st_c), Paragraph(str(m_dict["Avertissement"]["total"]), st_cb)],
        [Paragraph("Passable", st_b), Paragraph(str(m_dict["Passable"]["M"]), st_c), Paragraph(str(m_dict["Passable"]["F"]), st_c), Paragraph(str(m_dict["Passable"]["total"]), st_cb)],
        [Paragraph("Assez Bien", st_b), Paragraph(str(m_dict["Assez Bien"]["M"]), st_c), Paragraph(str(m_dict["Assez Bien"]["F"]), st_c), Paragraph(str(m_dict["Assez Bien"]["total"]), st_cb)],
        [Paragraph("TH", st_b), Paragraph(str(m_dict["Tableau d'Honneur"]["M"]), st_c), Paragraph(str(m_dict["Tableau d'Honneur"]["F"]), st_c), Paragraph(str(m_dict["Tableau d'Honneur"]["total"]), st_cb)],
        [Paragraph("THF", st_b), Paragraph(str(m_dict["THF"]["M"]), st_c), Paragraph(str(m_dict["THF"]["F"]), st_c), Paragraph(str(m_dict["THF"]["total"]), st_cb)],
    ]

    t_sanc = Table(data_sanc, colWidths=[3.5 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm])
    t_sanc.setStyle(TableStyle([
        ("SPAN", (0, 0), (3, 0)),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("BACKGROUND", (0, 0), (3, 0), colors.HexColor("#336699")),
        ("TEXTCOLOR", (0, 0), (3, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), GRIS_ENTETE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))

    graph_sanc = _creer_graphique_barres(
        [
            [m_dict["Blâme"]["M"], m_dict["Avertissement"]["M"], m_dict["Passable"]["M"], m_dict["Assez Bien"]["M"], m_dict["Tableau d'Honneur"]["M"], m_dict["THF"]["M"]],
            [m_dict["Blâme"]["F"], m_dict["Avertissement"]["F"], m_dict["Passable"]["F"], m_dict["Assez Bien"]["F"], m_dict["Tableau d'Honneur"]["F"], m_dict["THF"]["F"]]
        ],
        ["Garçons", "Filles"],
        ["Blâme", "Avert.", "Passable", "A. Bien", "TH", "THF"]
    )

    t_bloc_sanc = Table([[t_sanc, graph_sanc]], colWidths=[8.5 * cm, 9.5 * cm])
    t_bloc_sanc.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(t_bloc_sanc)
    story.append(Spacer(1, 0.4 * cm))

    # 5. INDICATEURS CLÉS (Moyenne Min, Max, Moyenne Générale)
    forte_moy_str = f"{stats['forte_moy']:.2f}".replace(".", ",")
    faible_moy_str = f"{stats['faible_moy']:.2f}".replace(".", ",")
    moy_gen_cl_str = f"{stats['moy_classe_gen']:.2f}".replace(".", ",")

    data_ind = [
        [Paragraph("<b>Faible Moyenne</b>", st_b), Paragraph(f"<b>{faible_moy_str}</b>", st_cb), Paragraph(_e(stats["eleve_faible_moy"]), st_b)],
        [Paragraph("<b>Haute Moyenne</b>", st_b), Paragraph(f"<b>{forte_moy_str}</b>", st_cb), Paragraph(_e(stats["eleve_forte_moy"]), st_b)],
        [Paragraph("<b>Moy. Gén. Cl.</b>", st_b), Paragraph(f"<b>{moy_gen_cl_str}</b>", st_cb), ""],
    ]

    t_ind = Table(data_ind, colWidths=[3.5 * cm, 2.0 * cm, 8.0 * cm])
    t_ind.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), GRIS_ENTETE),
        ("SPAN", (1, 2), (2, 2)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_ind)
    story.append(Spacer(1, 0.6 * cm))

    # 6. Pied de page & Signature
    ville = params_etab.get("etablissement_ville", "Maroua")
    date_ed = date.today().strftime("%d %B %Y").replace("March", "mars").replace("April", "avril")
    signataire = params_etab.get("etablissement_signataire", "Le chef d'établissement")

    p_sig = Paragraph(f"Fait à {ville} le {date_ed}<br/><br/><br/><b>{signataire}</b>", ParagraphStyle("sig", parent=st, alignment=2))
    story.append(p_sig)

    doc.build(story)
    return chemin_pdf