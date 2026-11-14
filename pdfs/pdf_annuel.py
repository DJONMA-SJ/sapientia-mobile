"""
BULLETIN RECAPITULATIF ANNUEL PDF
Meme presentation que le bulletin trimestriel, avec TRIM1/TRIM2/TRIM3/Moy An.
"""
import os
import io
import unicodedata
from datetime import date
from xml.sax.saxutils import escape

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GRIS_ENTETE = colors.HexColor("#D9D9D9")
GRIS_LIGNE = colors.HexColor("#E8E8E8")
GRIS_CHAMP = colors.HexColor("#EFEFEF")


def _e(txt):
    return escape(str(txt)) if txt is not None else ""


def _sans_accents(txt):
    txt = unicodedata.normalize("NFD", str(txt))
    return "".join(c for c in txt if unicodedata.category(c) != "Mn")


def _fmt(val):
    if val is None:
        return "-"
    try:
        return f"{float(val):.2f}".replace(".", ",")
    except Exception:
        return str(val)


def _fmt_coef(coef):
    if coef is None:
        return "-"
    try:
        coef = float(coef)
    except Exception:
        return str(coef)
    return str(int(coef)) if coef.is_integer() else f"{coef:g}".replace(".", ",")


def _rang(txt):
    if not txt or txt == "-":
        return "-"
    return str(txt).replace("/", " / ")


def _trouver_logo():
    for nom in ("logo.png", "logo.jpg", "logo.jpeg"):
        chemin = os.path.join(BASE_DIR, "assets", nom)
        if os.path.exists(chemin):
            return chemin
    return None


def _cases_travail(moy):
    cases = {"felicitation": False, "tableau_honneur": False, "encouragement": False,
             "avertissement": False, "blame": False}
    if moy is None:
        return cases
    if moy >= 16:
        cases["felicitation"] = True
        cases["tableau_honneur"] = True
    elif moy >= 14:
        cases["tableau_honneur"] = True
    elif moy >= 12:
        cases["encouragement"] = True
    elif moy >= 10:
        pass
    elif moy >= 7:
        cases["avertissement"] = True
    else:
        cases["blame"] = True
    return cases


def _efforts_annuel(matieres):
    notees = [m for m in matieres if m.get("moy_an") is not None]
    faibles = [m.get("nom", "") for m in notees if (m.get("moy_an") or 0) < 10]
    if not faibles:
        return "RAS"
    if notees and len(faibles) > len(notees) / 2:
        return "PRESQUE TOUTES LES MATIERES"
    return ", ".join(faibles)


def _case(contenu, style, largeur=0.6 * cm, hauteur=0.42 * cm):
    t = Table([[Paragraph(_e(contenu), style) if contenu else ""]], colWidths=[largeur], rowHeights=[hauteur])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _ligne_identite(cellules, largeurs, st_label, st_val):
    data = [[Paragraph(_e(txt), st_val if est_val else st_label) for txt, est_val in cellules]]
    t = Table(data, colWidths=[l * cm for l in largeurs])
    t.hAlign = "CENTER"
    style = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("TOPPADDING", (0, 0), (-1, -1), 1.5),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
             ("LEFTPADDING", (0, 0), (-1, -1), 3),
             ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    for i, (_, est_val) in enumerate(cellules):
        if est_val:
            style += [("BACKGROUND", (i, 0), (i, 0), GRIS_CHAMP),
                      ("LINEBELOW", (i, 0), (i, 0), 0.5, colors.grey)]
    t.setStyle(TableStyle(style))
    return t


def _filigrane(texte):
    texte = str(texte).upper()
    def dessiner(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 38)
        canvas.setFillColorRGB(0.81, 0.81, 0.81)
        try:
            canvas.setFillAlpha(0.32)
        except Exception:
            pass
        largeur, hauteur = doc.pagesize
        canvas.translate(largeur / 2, hauteur / 2)
        canvas.rotate(45)
        for dy in (180, 60, -60, -180):
            canvas.drawCentredString(0, dy, texte)
        canvas.restoreState()
    return dessiner


def construire_contenu_qr_annuel(donnees_eleve, stats, params_etab, decision):
    info = donnees_eleve["info"]
    lignes = [
        f"{_sans_accents(params_etab.get('etablissement_nom', ''))} | "
        f"{params_etab.get('annee_scolaire', '')} | ANNUEL",
        f"{_sans_accents(info['nom'])} {_sans_accents(info['prenom'])} | MAT {info['matricule']} | "
        f"{_sans_accents(info.get('classe_nom', ''))} | EFF {stats['effectif_total']}",
    ]
    for m in donnees_eleve["matieres"].values():
        lignes.append(
            f"{_sans_accents(m['nom'])[:18]}: T1 {_fmt(m.get('trim1'))} "
            f"T2 {_fmt(m.get('trim2'))} T3 {_fmt(m.get('trim3'))} AN {_fmt(m.get('moy_an'))}"
        )
    lignes.append(
        f"MOY AN {_fmt(donnees_eleve.get('moy_gen_an'))}/20 | "
        f"RANG {donnees_eleve.get('rang_gen_an')} | "
        f"MOY CLASSE {_fmt(stats.get('moy_classe_gen'))}"
    )
    lignes.append(f"DECISION: {_sans_accents(decision)}")
    return "\n".join(lignes)


def generer_qr_code(texte, taille=2.8 * cm):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=6, border=2)
    qr.add_data(texte)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Image(buf, width=taille, height=taille)


def generer_bulletin_annuel_pdf(donnees_eleve, stats, params_etab, chemin_fichier_pdf):
    info = donnees_eleve["info"]
    moy_an = donnees_eleve.get("moy_gen_an")
    decision = donnees_eleve.get("decision_an", "")
    discipline = donnees_eleve.get("discipline_an") or {}
    nom_etab = params_etab.get("etablissement_nom", "COLLEGE NOTRE DAME DE LA SAGESSE")
    annee = params_etab.get("annee_scolaire", "")

    moy_classe_mat = (
        stats.get("moyennes_classe_matiere_an")
        or stats.get("moyennes_classe_an")
        or stats.get("moyennes_classe_matiere")
        or {}
    )

    doc = SimpleDocTemplate(
        chemin_fichier_pdf, pagesize=A4,
        leftMargin=0.6 * cm, rightMargin=0.6 * cm,
        topMargin=0.6 * cm, bottomMargin=0.6 * cm,
    )
    story = []

    base = getSampleStyleSheet()["Normal"]
    st = ParagraphStyle("st", parent=base, fontSize=7.5, leading=9.5)
    st_b = ParagraphStyle("st_b", parent=st, fontName="Helvetica-Bold")
    st_c = ParagraphStyle("st_c", parent=st, alignment=1)
    st_cb = ParagraphStyle("st_cb", parent=st_b, alignment=1)
    st_r = ParagraphStyle("st_r", parent=st, alignment=2)
    st_rb = ParagraphStyle("st_rb", parent=st_b, alignment=2)
    st_small = ParagraphStyle("st_small", parent=st, fontSize=6.3, leading=7.8)
    st_small_c = ParagraphStyle("st_small_c", parent=st_small, alignment=1)
    st_etab = ParagraphStyle("st_etab", parent=st_b, fontSize=11.5, leading=13.5)
    st_titre = ParagraphStyle("st_titre", parent=st_b, fontSize=12.5, leading=15, alignment=1)
    st_bloc_titre = ParagraphStyle("st_bloc_titre", parent=st_b, fontSize=6.8, leading=8.5, alignment=1)
    st_fil = ParagraphStyle("st_fil", parent=st_b, fontSize=7, leading=8, alignment=1, textColor=colors.HexColor("#A8A8A8"))

    gauche = [
        Paragraph(_e(params_etab.get("etablissement_tutelle",
                  "MINESEC / REGION DE L'EXTREME-NORD / DEPARTEMENT DU DIAMARE / COMMUNE DE MAROUA")), st_small),
        Paragraph(_e(nom_etab), st_etab),
    ]
    devise = params_etab.get("etablissement_devise", "")
    if devise:
        gauche.append(Paragraph(f"<i>{_e(devise)}</i>", st_small))
    gauche.append(Paragraph(
        f"{_e(params_etab.get('etablissement_bp', 'BP 228 Maroua'))} &nbsp;&nbsp; "
        f"Tel : {_e(params_etab.get('etablissement_tel', ''))} &nbsp;&nbsp;&nbsp;&nbsp; "
        f"Email : {_e(params_etab.get('etablissement_email', ''))}", st))

    droite = [
        Paragraph("REPUBLIQUE DU CAMEROUN", st_rb),
        Paragraph("Paix - Travail - Patrie", st_r),
        Spacer(1, 0.25 * cm),
        Paragraph(f"Annee scolaire : <b>{_e(annee)}</b>", st_r),
    ]
    t_entete = Table([[gauche, droite]], colWidths=[13.3 * cm, 6.0 * cm])
    t_entete.hAlign = "CENTER"
    t_entete.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                  ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(t_entete)
    story.append(Spacer(1, 0.15 * cm))

    logo_path = _trouver_logo()
    if logo_path:
        logo = Image(logo_path, width=2.3 * cm, height=2.3 * cm, kind="proportional")
    else:
        logo = ""
    boite_titre = Table([[Paragraph(f"BULLETIN RECAPITULATIF ANNUEL {_e(annee)}", st_titre)]],
                        colWidths=[12.9 * cm])
    boite_titre.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.2, colors.black),
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_ENTETE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    qr_img = generer_qr_code(construire_contenu_qr_annuel(donnees_eleve, stats, params_etab, decision))
    t_titre = Table([[logo, boite_titre, qr_img]], colWidths=[3.2 * cm, 12.9 * cm, 3.2 * cm])
    t_titre.hAlign = "CENTER"
    t_titre.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (1, 0), (1, 0), 0),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
    ]))
    story.append(t_titre)
    story.append(Spacer(1, 0.15 * cm))

    red_str = "Oui" if info.get("redoublant") == 1 else "Non"
    date_lieu = f"{info.get('date_naissance') or ''}   a   {info.get('lieu_naissance') or ''}"
    nb_txt = params_etab.get("mention_nb", "N.B : En cas de doute, bien vouloir saisir notre etablissement")

    story.append(_ligne_identite(
        [("Nom :", False), (info["nom"], True), ("Prenom :", False), (info["prenom"], True)],
        [1.5, 8.1, 2.0, 7.7], st_b, st))
    story.append(_ligne_identite(
        [("Date et lieu de naissance :", False), (date_lieu, True), ("", False), ("Sexe :", False), (info["sexe"], True)],
        [4.3, 8.7, 1.5, 1.3, 3.5], st_b, st))
    story.append(_ligne_identite(
        [("Classe :", False), (info.get("classe_nom", ""), True),
         ("Effectif :", False), (stats["effectif_total"], True),
         ("Matricule :", False), (info["matricule"], True),
         ("Redoublant :", False), (red_str, True)],
        [1.5, 4.9, 1.6, 1.4, 1.9, 2.6, 2.1, 3.3], st_b, st))
    story.append(_ligne_identite(
        [(nb_txt, False), ("Professeur Principal :", False), (info.get("prof_principal") or "", True)],
        [9.4, 3.6, 6.3], st_b, st))
    story.append(Spacer(1, 0.2 * cm))

    entetes = ["Discipline", "TRIM1", "TRIM2", "TRIM3", "Moy An.<br/>/20",
               "Coef", "Totaux", "Moy<br/>Classe", "RANG", "Appreciation<br/>Nom Professeur"]
    data = [[Paragraph(h, st_cb) for h in entetes]]
    style = [
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), GRIS_ENTETE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]

    for grp in (1, 2, 3):
        items = [(mid, m) for mid, m in donnees_eleve["matieres"].items() if m["groupe"] == grp]
        if not items:
            continue
        for mid, m in items:
            moy_cl = moy_classe_mat.get(mid)
            moy_cl_txt = _fmt(moy_cl) if moy_cl else "-"
            data.append([
                Paragraph(_e(m["nom"]), st),
                Paragraph(_fmt(m.get("trim1")), st_c),
                Paragraph(_fmt(m.get("trim2")), st_c),
                Paragraph(_fmt(m.get("trim3")), st_c),
                Paragraph(_fmt(m.get("moy_an")), st_c),
                Paragraph(_fmt_coef(m["coef"]), st_c),
                Paragraph(_fmt(m.get("total_an")), st_c),
                Paragraph(moy_cl_txt, st_c),
                Paragraph(_rang(m.get("rang_an")), st_c),
                Paragraph(f"{_e(m.get('appreciation')) or '-'}<br/><font color='#444444'>{_e(m.get('prof'))}</font>", st),
            ])
        g = donnees_eleve["groupes"][grp]
        r = len(data)
        libelle = "MATIERES DU 1er GROUPE" if grp == 1 else f"MATIERES DU {grp}eme GROUPE"
        try:
            from core.calculator import get_appreciation_matiere
            apprec_grp = get_appreciation_matiere(g.get("moy")) if g.get("moy") is not None else ""
        except Exception:
            apprec_grp = ""
        data.append([
            Paragraph(libelle, st_b),
            Paragraph(f"<i>{_e(nom_etab)}</i>", st_fil), "", "",
            Paragraph(_fmt(g.get("moy")), st_cb),
            Paragraph(_fmt_coef(g.get("coefs")) if g.get("coefs") else "-", st_cb),
            Paragraph(_fmt(g.get("pts")) if g.get("coefs") else "-", st_cb),
            Paragraph("", st),
            Paragraph(_rang(g.get("rang")), st_cb),
            Paragraph(f"<b>{_e(apprec_grp)}</b>", st),
        ])
        style.append(("BACKGROUND", (0, r), (-1, r), GRIS_LIGNE))
        style.append(("SPAN", (1, r), (3, r)))
        style.append(("ALIGN", (1, r), (3, r), "CENTER"))
        style.append(("VALIGN", (1, r), (3, r), "MIDDLE"))

    r = len(data)
    mg_str = _fmt(moy_an)
    data.append([
        Paragraph("Total general / Moyenne Annuelle", st_b),
        Paragraph("", st), Paragraph("", st), Paragraph("", st),
        Paragraph(mg_str, st_cb),
        Paragraph(_fmt_coef(donnees_eleve.get("total_coefs_an")) if donnees_eleve.get("total_coefs_an") else "-", st_cb),
        Paragraph(_fmt(donnees_eleve.get("total_points_an")) if donnees_eleve.get("total_coefs_an") else "-", st_cb),
        Paragraph(_fmt(stats.get("moy_classe_gen")), st_cb),
        Paragraph(_rang(donnees_eleve.get("rang_gen_an")), st_cb),
        Paragraph(f"<b>{_e(donnees_eleve.get('appreciation_an', ''))}</b>", st),
    ])
    style.append(("BACKGROUND", (0, r), (-1, r), GRIS_LIGNE))

    col_widths = [4.2 * cm, 1.3 * cm, 1.3 * cm, 1.3 * cm, 1.4 * cm,
                  0.9 * cm, 1.4 * cm, 1.4 * cm, 1.3 * cm, 4.8 * cm]
    t_notes = Table(data, colWidths=col_widths, repeatRows=1)
    t_notes.hAlign = "CENTER"
    t_notes.setStyle(TableStyle(style))
    story.append(t_notes)
    story.append(Paragraph(_e(params_etab.get("mention_edition", "Bulletin edite par le Secretariat du College")), st_small_c))
    story.append(Spacer(1, 0.15 * cm))

    # 5. Les 4 blocs - pleine largeur 19.8 cm
    cases = _cases_travail(moy_an)

    bloc1 = [
        Paragraph("<b>Moyenne Annuelle :</b> <b>" + mg_str + "</b> /20", st),
        Paragraph("<b>Rang Annuel :</b> <b>" + _rang(donnees_eleve.get("rang_gen_an")) + "</b>", st),
        Spacer(1, 0.12 * cm),
        Paragraph("Moy. An./20 = <b>(TRIM1 + TRIM2 + TRIM3) / 3</b>", st_small),
        Paragraph("Moy. Annuelle = <b>Somme(MoyAn x Coef) / Somme Coef</b>", st_small),
    ]

    bloc2 = [
        Paragraph("<u><b>PROFIL DE LA CLASSE (AN) :</b></u>", st_small),
        Spacer(1, 0.08 * cm),
        Paragraph(f"Moy Premier : <b>{_fmt(stats.get('forte_moy'))}</b> /20", st),
        Paragraph(f"Moy Dernier : <b>{_fmt(stats.get('faible_moy'))}</b> /20", st),
        Paragraph(f"Moy Classe : <b>{_fmt(stats.get('moy_classe_gen'))}</b> /20", st),
    ]

    style_cases = TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ])

    bloc3 = Table([
        [_case("X" if cases["avertissement"] else "", st_cb), Paragraph("Avertissement", st)],
        [_case("X" if cases["blame"] else "", st_cb), Paragraph("Blame", st)],
        [_case("X" if cases["tableau_honneur"] else "", st_cb), Paragraph("Tableau d'Honneur", st)],
        [_case("X" if cases["encouragement"] else "", st_cb), Paragraph("Encouragement", st)],
        [_case("X" if cases["felicitation"] else "", st_cb), Paragraph("Felicitation", st)],
    ], colWidths=[0.9 * cm, 3.6 * cm])
    bloc3.setStyle(style_cases)

    bloc4 = [
        Paragraph("Moy Trimestre 1 : <b>" + _fmt(donnees_eleve.get("moy_gen_t1")) + "</b> /20", st),
        Paragraph("Moy Trimestre 2 : <b>" + _fmt(donnees_eleve.get("moy_gen_t2")) + "</b> /20", st),
        Paragraph("Moy Trimestre 3 : <b>" + _fmt(donnees_eleve.get("moy_gen_t3")) + "</b> /20", st),
        Spacer(1, 0.1 * cm),
        Paragraph("Heures abs an : <b>" + str(discipline.get("heures_absences") or 0) + "</b>", st),
    ]

    titres = ["RESULTAT ANNUEL DE L'ELEVE", "PROFIL DE LA CLASSE", "APPRECIATION TRAVAIL", "RAPPELS DES TRIMESTRES"]
    t_bas = Table([[Paragraph(t, st_bloc_titre) for t in titres], [bloc1, bloc2, bloc3, bloc4]],
                  colWidths=[5.3 * cm, 4.7 * cm, 4.8 * cm, 5.0 * cm])
    t_bas.hAlign = "CENTER"
    t_bas.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("VALIGN", (0, 1), (-1, 1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_bas)
    story.append(Spacer(1, 0.2 * cm))

    ville = params_etab.get("etablissement_ville", "Maroua")
    signataire = params_etab.get("etablissement_signataire", "LE PRINCIPAL")
    date_edition = params_etab.get("date_edition") or date.today().strftime("%d/%m/%Y")
    efforts = _efforts_annuel(donnees_eleve["matieres"].values())
    apprec_travail = donnees_eleve.get("appreciation_an", "")

    cell_apprec = [
        Paragraph(f"<b>{_e(apprec_travail).upper() or '-'}</b>", st_cb),
        Spacer(1, 0.3 * cm),
        Paragraph("VISA DU PARENT", st_small_c),
    ]
    cell_decision = [
        Paragraph(f"<b>{_e(decision)}</b>", st),
        Spacer(1, 0.12 * cm),
        Paragraph("<u><b>Des efforts s'imposent en :</b></u>", st),
        Paragraph(_e(efforts), st),
    ]
    cell_signature = [
        Paragraph(f"Fait a {_e(ville)}, le <b>{_e(date_edition)}</b>", st_r),
        Spacer(1, 0.9 * cm),
        Paragraph(f"<b>{_e(signataire)}</b>", st_rb),
    ]
    t_foot = Table([
        [Paragraph("<b>APPRECIATION DU TRAVAIL</b>", st), Paragraph("<b>DECISION FINALE DU CONSEIL</b>", st_cb), ""],
        [cell_apprec, cell_decision, cell_signature],
    ], colWidths=[5.0 * cm, 9.3 * cm, 5.0 * cm], rowHeights=[0.55 * cm, 2.1 * cm])
    t_foot.hAlign = "CENTER"
    t_foot.setStyle(TableStyle([
        ("BOX", (0, 1), (0, 1), 0.8, colors.black),
        ("BOX", (1, 1), (1, 1), 1.0, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("VALIGN", (0, 1), (0, 1), "MIDDLE"),
        ("TOPPADDING", (0, 1), (-1, 1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_foot)

    doc.build(story, onFirstPage=_filigrane(nom_etab), onLaterPages=_filigrane(nom_etab))
    return chemin_fichier_pdf