import os
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart

GRIS_ENTETE = colors.HexColor("#D9D9D9")
BLEU_TITRE = colors.HexColor("#336699")


def _e(txt):
    return escape(str(txt)) if txt is not None else ""


def _fmt(val):
    if val is None:
        return "-"
    try:
        f = float(val)
        if f == int(f):
            return "{:g}".format(f)
        return "{:.2f}".format(f).replace(".", ",")
    except:
        return str(val)


def _fmt_pct(val, total):
    if not total:
        return "0%"
    pct = (val / total) * 100
    if float(pct).is_integer():
        return "{:.0f}%".format(pct)
    return "{:.1f}%".format(pct).replace(".", ",")


def _get_mention(m_dict, key_ref):
    if key_ref in m_dict:
        return m_dict[key_ref]
    # tolerance accent Blame / Blame
    alt1 = key_ref.replace("Blame", "Blame").replace("Blame", "Blame")
    # cherche sans tenir compte des accents courants
    for k, v in m_dict.items():
        kn = k.replace("a", "a").replace("A", "A")
        kr = key_ref.replace("a", "a").replace("A", "A")
        if kn.lower() == kr.lower():
            return v
    return {"M": 0, "F": 0, "total": 0}


def _creer_graphique_barres(donnees, categories, largeur=8*cm, hauteur=4.5*cm):
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
    couleurs = [colors.HexColor("#4F81BD"), colors.HexColor("#F29559"), colors.HexColor("#A5A5A5"), colors.HexColor("#7BAF6B")]
    for i in range(len(donnees)):
        try:
            chart.bars[i].fillColor = couleurs[i % len(couleurs)]
        except:
            pass
    d.add(chart)
    return d


def generer_fiche_statistiques_annuelle_pdf(classe_nom, stats_an, rappels_moy, params_etab, chemin_pdf):
    params_etab = params_etab or {}
    stats_an = stats_an or {}
    rappels_moy = rappels_moy or {}

    doc = SimpleDocTemplate(
        chemin_pdf,
        pagesize=A4,
        leftMargin=1.0 * cm,
        rightMargin=1.0 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm
    )
    story = []

    base = getSampleStyleSheet()["Normal"]
    st = ParagraphStyle("st", parent=base, fontSize=8, leading=10)
    st_b = ParagraphStyle("st_b", parent=st, fontName="Helvetica-Bold")
    st_c = ParagraphStyle("st_c", parent=st, alignment=1)
    st_cb = ParagraphStyle("st_cb", parent=st_b, alignment=1)
    st_etab = ParagraphStyle("st_etab", parent=st_b, fontSize=11, leading=13, alignment=1)
    st_titre = ParagraphStyle("st_titre", parent=st_b, fontSize=12, leading=14, alignment=1)

    nom_etab = _e(params_etab.get("etablissement_nom", "COLLEGE NOTRE DAME DE LA SAGESSE"))
    annee = _e(params_etab.get("annee_scolaire", "2025/2026"))

    story.append(Paragraph(nom_etab, st_etab))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("<b><u>STATISTIQUES ANNUELLES DE LA CLASSE DE " + _e(classe_nom) + "</u></b>", st_titre))
    story.append(Paragraph("Annee scolaire : " + annee, st_c))
    story.append(Spacer(1, 0.4 * cm))

    total_eff = stats_an.get("effectif_total", 0)
    g_count = stats_an.get("garcons", 0)
    f_count = stats_an.get("filles", 0)
    red_count = stats_an.get("redoublants", 0)
    non_red = total_eff - red_count if total_eff else 0

    # 1. EFFECTIFS
    data_eff = [
        [Paragraph("<b>RAPPORT DES EFFECTIFS - ANNEE</b>", st_cb), "", ""],
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
        ("BACKGROUND", (0, 0), (2, 0), BLEU_TITRE),
        ("TEXTCOLOR", (0, 0), (2, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), GRIS_ENTETE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    graph_eff = _creer_graphique_barres(
        [[g_count, f_count, total_eff, red_count, non_red]],
        ["GARCONS", "FILLES", "TOTAL", "Red.", "Non Red."]
    )
    story.append(Table([[t_eff, graph_eff]], colWidths=[8.5 * cm, 9.5 * cm]))
    story.append(Spacer(1, 0.4 * cm))

    # 2. ECHEC / REUSSITE ANNUEL
    reu = stats_an.get("reussite", {"M": 0, "F": 0, "total": 0})
    ech = stats_an.get("echec", {"M": 0, "F": 0, "total": 0})
    reu_g = reu.get("M", 0)
    reu_f = reu.get("F", 0)
    reu_tot = reu.get("total", 0)
    ech_g = ech.get("M", 0)
    ech_f = ech.get("F", 0)
    ech_tot = ech.get("total", 0)

    data_ech = [
        [Paragraph("<b>RAPPORT ECHEC - REUSSITE ANNUEL (MOY ANNUELLE)</b>", st_cb), "", ""],
        [Paragraph("", st), Paragraph("<b>ECHEC (&lt;10)</b>", st_cb), Paragraph("<b>REUSSITE (&gt;=10)</b>", st_cb)],
        [Paragraph("GARCONS", st_b), Paragraph(str(ech_g), st_c), Paragraph(str(reu_g), st_c)],
        [Paragraph("FILLES", st_b), Paragraph(str(ech_f), st_c), Paragraph(str(reu_f), st_c)],
        [Paragraph("TOTAL", st_b), Paragraph(str(ech_tot), st_cb), Paragraph(str(reu_tot), st_cb)],
        [Paragraph("POURCENTAGE", st_b), Paragraph(_fmt_pct(ech_tot, total_eff), st_cb), Paragraph(_fmt_pct(reu_tot, total_eff), st_cb)],
    ]
    t_ech = Table(data_ech, colWidths=[3.5 * cm, 2.2 * cm, 2.3 * cm])
    t_ech.setStyle(TableStyle([
        ("SPAN", (0, 0), (2, 0)),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("BACKGROUND", (0, 0), (2, 0), BLEU_TITRE),
        ("TEXTCOLOR", (0, 0), (2, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), GRIS_ENTETE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    graph_ech = _creer_graphique_barres(
        [[ech_g, ech_f, ech_tot], [reu_g, reu_f, reu_tot]],
        ["GARCONS", "FILLES", "TOTAL"]
    )
    story.append(Table([[t_ech, graph_ech]], colWidths=[8.5 * cm, 9.5 * cm]))
    story.append(Spacer(1, 0.4 * cm))

    # 3. MENTIONS ANNUELLES
    m_dict = stats_an.get("mentions", {})
    m_bl = _get_mention(m_dict, "Blame")
    m_av = _get_mention(m_dict, "Avertissement")
    m_pa = _get_mention(m_dict, "Passable")
    m_ab = _get_mention(m_dict, "Assez Bien")
    m_th = _get_mention(m_dict, "Tableau d'Honneur")
    m_thf = _get_mention(m_dict, "THF")

    data_sanc = [
        [Paragraph("<b>SANCTIONS ET APPRECIATIONS ANNUELLES</b>", st_cb), "", "", ""],
        [Paragraph("", st), Paragraph("<b>GARCONS</b>", st_cb), Paragraph("<b>FILLES</b>", st_cb), Paragraph("<b>TOTAL</b>", st_cb)],
        [Paragraph("Blame (<7)", st_b), Paragraph(str(m_bl.get("M", 0)), st_c), Paragraph(str(m_bl.get("F", 0)), st_c), Paragraph(str(m_bl.get("total", 0)), st_cb)],
        [Paragraph("Avertissement (7-10)", st_b), Paragraph(str(m_av.get("M", 0)), st_c), Paragraph(str(m_av.get("F", 0)), st_c), Paragraph(str(m_av.get("total", 0)), st_cb)],
        [Paragraph("Passable (10-12)", st_b), Paragraph(str(m_pa.get("M", 0)), st_c), Paragraph(str(m_pa.get("F", 0)), st_c), Paragraph(str(m_pa.get("total", 0)), st_cb)],
        [Paragraph("Assez Bien (12-14)", st_b), Paragraph(str(m_ab.get("M", 0)), st_c), Paragraph(str(m_ab.get("F", 0)), st_c), Paragraph(str(m_ab.get("total", 0)), st_cb)],
        [Paragraph("TH (14-16)", st_b), Paragraph(str(m_th.get("M", 0)), st_c), Paragraph(str(m_th.get("F", 0)), st_c), Paragraph(str(m_th.get("total", 0)), st_cb)],
        [Paragraph("THF (16-20)", st_b), Paragraph(str(m_thf.get("M", 0)), st_c), Paragraph(str(m_thf.get("F", 0)), st_c), Paragraph(str(m_thf.get("total", 0)), st_cb)],
    ]
    t_sanc = Table(data_sanc, colWidths=[3.5 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm])
    t_sanc.setStyle(TableStyle([
        ("SPAN", (0, 0), (3, 0)),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("BACKGROUND", (0, 0), (3, 0), BLEU_TITRE),
        ("TEXTCOLOR", (0, 0), (3, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), GRIS_ENTETE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    graph_sanc = _creer_graphique_barres(
        [
            [m_bl.get("M", 0), m_av.get("M", 0), m_pa.get("M", 0), m_ab.get("M", 0), m_th.get("M", 0), m_thf.get("M", 0)],
            [m_bl.get("F", 0), m_av.get("F", 0), m_pa.get("F", 0), m_ab.get("F", 0), m_th.get("F", 0), m_thf.get("F", 0)]
        ],
        ["Blame", "Avert.", "Passable", "A. Bien", "TH", "THF"]
    )
    story.append(Table([[t_sanc, graph_sanc]], colWidths=[8.5 * cm, 9.5 * cm]))
    story.append(Spacer(1, 0.4 * cm))

    # 4. INDICATEURS ANNUELS
    forte = stats_an.get("forte_moy")
    faible = stats_an.get("faible_moy")
    moy_gen = stats_an.get("moy_classe_gen")
    data_ind = [
        [Paragraph("<b>Faible Moyenne Annuelle</b>", st_b), Paragraph("<b>" + _fmt(faible) + "</b>", st_cb), Paragraph(_e(stats_an.get("eleve_faible_moy", "")), st_b)],
        [Paragraph("<b>Haute Moyenne Annuelle</b>", st_b), Paragraph("<b>" + _fmt(forte) + "</b>", st_cb), Paragraph(_e(stats_an.get("eleve_forte_moy", "")), st_b)],
        [Paragraph("<b>Moy. Gen. Classe Annuelle</b>", st_b), Paragraph("<b>" + _fmt(moy_gen) + "</b>", st_cb), Paragraph("", st)],
    ]
    t_ind = Table(data_ind, colWidths=[4.0 * cm, 2.2 * cm, 11.8 * cm])
    t_ind.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), GRIS_ENTETE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_ind)
    story.append(Spacer(1, 0.4 * cm))

    # 5. RAPPELS TRIMESTRIELS
    r1 = rappels_moy.get(1)
    r2 = rappels_moy.get(2)
    r3 = rappels_moy.get(3)
    data_rap = [
        [Paragraph("<b>RAPPELS DES MOYENNES DE CLASSE PAR TRIMESTRE</b>", st_cb), "", "", ""],
        [Paragraph("", st), Paragraph("<b>Trimestre 1</b>", st_cb), Paragraph("<b>Trimestre 2</b>", st_cb), Paragraph("<b>Trimestre 3</b>", st_cb)],
        [Paragraph("<b>Moyenne de classe</b>", st_b), Paragraph(_fmt(r1), st_c), Paragraph(_fmt(r2), st_c), Paragraph(_fmt(r3), st_c)],
        [Paragraph("<b>Moyenne annuelle</b>", st_b), Paragraph("<b>" + _fmt(moy_gen) + "</b>", st_cb), Paragraph("", st), Paragraph("", st)],
    ]
    t_rap = Table(data_rap, colWidths=[4.0 * cm, 3.0 * cm, 3.0 * cm, 3.0 * cm])
    t_rap.setStyle(TableStyle([
        ("SPAN", (0, 0), (3, 0)),
        ("SPAN", (1, 3), (3, 3)),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("BACKGROUND", (0, 0), (3, 0), BLEU_TITRE),
        ("TEXTCOLOR", (0, 0), (3, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), GRIS_ENTETE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    vals_graph = [float(r1 or 0), float(r2 or 0), float(r3 or 0), float(moy_gen or 0)]
    graph_rap = _creer_graphique_barres(
        [vals_graph],
        ["T1", "T2", "T3", "An"]
    )
    story.append(Table([[t_rap, graph_rap]], colWidths=[13.0 * cm, 5.0 * cm]))
    story.append(Spacer(1, 0.6 * cm))

    ville = params_etab.get("etablissement_ville", "Maroua")
    date_ed = date.today().strftime("%d/%m/%Y")
    signataire = params_etab.get("etablissement_signataire", "Le chef d'etablissement")
    story.append(Paragraph("Fait a " + _e(ville) + " le " + date_ed + "<br/><br/><br/><b>" + _e(signataire) + "</b>", ParagraphStyle("sig", parent=st, alignment=2)))

    dossier = os.path.dirname(os.path.abspath(chemin_pdf))
    if dossier:
        os.makedirs(dossier, exist_ok=True)
    doc.build(story)
    return chemin_pdf