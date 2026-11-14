import os
import sys
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

from core.calculator import get_decision_conseil, get_appreciation_matiere, get_appreciation_generale

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_assets_dir():
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        c1 = os.path.join(exe_dir, "assets")
        if os.path.exists(c1):
            return c1
        c2 = os.path.join(exe_dir, "_internal", "assets")
        if os.path.exists(c2):
            return c2
        return c1
    return os.path.join(BASE_DIR, "assets")

def get_photos_dir():
    d = os.path.join(get_assets_dir(), "photos")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d

def get_logo_path():
    ad = get_assets_dir()
    for n in ("logo.png", "logo.jpg", "logo.jpeg"):
        p = os.path.join(ad, n)
        if os.path.exists(p):
            return p
    return os.path.join(BASE_DIR, "assets", "logo.png")

def find_photo_path(matricule, photo_field=None):
    photos_dir = get_photos_dir()
    if photo_field:
        pf = str(photo_field).strip()
        if pf:
            if os.path.isabs(pf) and os.path.exists(pf):
                return pf
            c1 = os.path.join(photos_dir, pf)
            if os.path.exists(c1):
                return c1
            c2 = os.path.join(BASE_DIR, pf)
            if os.path.exists(c2):
                return c2
    mat_raw = str(matricule or "").strip()
    mat_clean = "".join(c for c in mat_raw if c.isalnum() or c in "-_")
    for base in [mat_clean, mat_raw]:
        if not base:
            continue
        for ext in [".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"]:
            p = os.path.join(photos_dir, base + ext)
            if os.path.exists(p):
                return p
    return None

def get_photo_flowable(info, largeur=2.8*cm, hauteur=3.2*cm):
    matricule = str(info.get("matricule", "") or "").strip()
    photo_field = str(info.get("photo", "") or "").strip()
    chemin = find_photo_path(matricule, photo_field)
    if chemin and os.path.exists(chemin):
        try:
            return Image(chemin, width=largeur, height=hauteur, kind="proportional")
        except Exception:
            pass
    st_tmp = ParagraphStyle("ph_tmp", fontSize=7, leading=9, alignment=1, fontName="Helvetica-Bold")
    t = Table([[Paragraph("PHOTO<br/>" + escape(matricule), st_tmp)]], colWidths=[largeur], rowHeights=[hauteur])
    t.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.8, colors.black),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F2F2F2")),
    ]))
    return t

NOMS_TRIMESTRES = {1: "Premier", 2: "Deuxieme", 3: "Troisieme"}
AFFICHER_TOTAL_COEFS = False
GRIS_ENTETE = colors.HexColor("#D9D9D9")
GRIS_LIGNE = colors.HexColor("#E8E8E8")
GRIS_CHAMP = colors.HexColor("#EFEFEF")

def _e(txt):
    return escape(str(txt)) if txt is not None else ""

def _fmt(val):
    return "-" if val is None else f"{val:.2f}".replace(".", ",")

def _fmt_coef(coef):
    if coef is None:
        return "-"
    coef = float(coef)
    if coef.is_integer():
        return str(int(coef))
    return f"{coef:g}".replace(".", ",")

def _rang(txt):
    if not txt or txt == "-":
        return "-"
    return str(txt).replace("/", " / ")

def _cases_travail(moy):
    cases = {"felicitation": False, "tableau_honneur": False, "encouragement": False, "avertissement": False, "blame": False}
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

def _efforts_a_fournir(matieres):
    notees = [m for m in matieres if m["moy"] is not None]
    faibles = [m["nom"] for m in notees if m["moy"] < 10]
    if not faibles:
        return "RAS"
    if len(faibles) > len(notees) / 2:
        return "PRESQUE TOUTES LES MATIERES"
    return ", ".join(faibles)

def _case(contenu, style, largeur=0.6*cm, hauteur=0.42*cm):
    t = Table([[Paragraph(_e(contenu), style) if contenu else ""]], colWidths=[largeur], rowHeights=[hauteur])
    t.setStyle(TableStyle([("BOX", (0,0), (-1,-1), 0.7, colors.black), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("LEFTPADDING", (0,0), (-1,-1), 1), ("RIGHTPADDING", (0,0), (-1,-1), 1), ("TOPPADDING", (0,0), (-1,-1), 0), ("BOTTOMPADDING", (0,0), (-1,-1), 0)]))
    return t

def _ligne_identite(cellules, largeurs, st_label, st_val):
    data = [[Paragraph(_e(txt), st_val if est_val else st_label) for txt, est_val in cellules]]
    t = Table(data, colWidths=[l*cm for l in largeurs])
    style = [("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 1.5), ("BOTTOMPADDING", (0,0), (-1,-1), 1.5), ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3)]
    for i, (_, est_val) in enumerate(cellules):
        if est_val:
            style += [("BACKGROUND", (i,0), (i,0), GRIS_CHAMP), ("LINEBELOW", (i,0), (i,0), 0.5, colors.grey)]
    t.setStyle(TableStyle(style))
    return t

def _filigrane(texte):
    def dessiner(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 36)
        canvas.setFillColorRGB(0.80, 0.80, 0.80)
        try:
            canvas.setFillAlpha(0.35)
        except Exception:
            pass
        largeur, hauteur = doc.pagesize
        canvas.translate(largeur/2, hauteur/2)
        canvas.rotate(50)
        canvas.drawCentredString(0, 0, texte)
        canvas.restoreState()
    return dessiner

def generer_bulletin_pdf(donnees_eleve, stats_classe, params_etab, chemin_fichier_pdf, trimestre=None):
    dossier = os.path.dirname(os.path.abspath(chemin_fichier_pdf))
    if dossier:
        os.makedirs(dossier, exist_ok=True)
    if trimestre is None:
        trimestre = params_etab.get("trimestre", params_etab.get("trimestre_actif", 2))
    trim = int(trimestre)
    info = donnees_eleve["info"]
    moy_gen = donnees_eleve["moy_gen"]
    decision = get_decision_conseil(moy_gen)
    moy_classe_mat = stats_classe.get("moyennes_classe_matiere") or {}
    discipline = donnees_eleve.get("discipline") or {}
    nom_etab = params_etab.get("etablissement_nom", 'COLLEGE BILINGUE NOTRE DAME DE LA SAGESSE "SAPIENTIA"')
    tutelle = params_etab.get("etablissement_tutelle", "MINESEC/REGION DE L'EXTREME-NORD/DEPARTEMENT DU DIAMARE/ ARRONDISSEMENT DE MAROUA II")
    doc = SimpleDocTemplate(chemin_fichier_pdf, pagesize=A4, leftMargin=0.6*cm, rightMargin=0.6*cm, topMargin=0.6*cm, bottomMargin=0.6*cm)
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
    st_fil = ParagraphStyle("st_fil", parent=st_b, fontSize=8, alignment=1, textColor=colors.HexColor("#A8A8A8"))
    st_result_big = ParagraphStyle("st_result_big", parent=st_b, fontSize=10.5, leading=12.5)
    gauche = [Paragraph(_e(tutelle), st_small), Paragraph(_e(nom_etab), st_etab)]
    devise = params_etab.get("etablissement_devise", "")
    if devise:
        gauche.append(Paragraph("<i>" + _e(devise) + "</i>", st_small))
    gauche.append(Paragraph(_e(params_etab.get("etablissement_bp", "BP 228 Maroua")) + " &nbsp;&nbsp; Tel : " + _e(params_etab.get("etablissement_tel", "698 12 22 87")) + " &nbsp;&nbsp;&nbsp;&nbsp; Email : " + _e(params_etab.get("etablissement_email", "Sapientia237@gmail.com")), st))
    droite = [Paragraph("REPUBLIQUE DU CAMEROUN", st_rb), Paragraph("Paix - Travail - Patrie", st_r), Spacer(1, 0.25*cm), Paragraph("Annee scolaire : <b>" + _e(params_etab.get("annee_scolaire", "")) + "</b>", st_r)]
    t_entete = Table([[gauche, droite]], colWidths=[13.3*cm, 6.0*cm])
    t_entete.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 0)]))
    story.append(t_entete)
    story.append(Spacer(1, 0.15*cm))
    logo_path = get_logo_path()
    logo = Image(logo_path, width=2.3*cm, height=2.3*cm, kind="proportional") if os.path.exists(logo_path) else ""
    boite_titre = Table([[Paragraph("Bulletin de Notes du " + NOMS_TRIMESTRES.get(trim, "") + " Trimestre", st_titre)]], colWidths=[12.5*cm])
    boite_titre.setStyle(TableStyle([("BOX", (0,0), (-1,-1), 1.2, colors.black), ("BACKGROUND", (0,0), (-1,-1), GRIS_ENTETE), ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7)]))
    photo_img = get_photo_flowable(info)
    t_titre = Table([[logo, boite_titre, photo_img]], colWidths=[2.8*cm, 12.9*cm, 3.6*cm])
    t_titre.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("ALIGN", (0,0), (-1,-1), "CENTER"), ("LEFTPADDING", (1,0), (1,0), 0.2*cm), ("RIGHTPADDING", (1,0), (1,0), 0.2*cm)]))
    story.append(t_titre)
    story.append(Spacer(1, 0.15*cm))
    red_str = "Oui" if info.get("redoublant") == 1 else "Non"
    nom_complet = (str(info.get("nom", "")) + " " + str(info.get("prenom", ""))).strip()
    date_lieu = str(info.get("date_naissance") or "") + "   a   " + str(info.get("lieu_naissance") or "")
    nb_txt = params_etab.get("mention_nb", "N.B : En cas de doute, bien vouloir saisir notre etablissement")
    story.append(_ligne_identite([("NOM ET PRENOM :", False), (nom_complet, True)], [3.5, 15.8], st_b, st))
    story.append(_ligne_identite([("Date et lieu de naissance :", False), (date_lieu, True), ("", False), ("Sexe :", False), (info["sexe"], True)], [4.3, 8.7, 1.5, 1.3, 3.5], st_b, st))
    story.append(_ligne_identite([("Classe :", False), (info.get("classe_nom", ""), True), ("Effectif :", False), (stats_classe["effectif_total"], True), ("Matricule :", False), (info["matricule"], True), ("Redoublant :", False), (red_str, True)], [1.5, 4.9, 1.6, 1.4, 1.9, 2.6, 2.1, 3.3], st_b, st))
    story.append(_ligne_identite([(nb_txt, False), ("Professeur Principal :", False), (info.get("prof_principal") or "", True)], [9.4, 3.6, 6.3], st_b, st))
    story.append(Spacer(1, 0.2*cm))
    entetes = ["Matieres", "Moy Trim<br/>/20", "Coefs", "Moy x<br/>Coef", "Moy<br/>Classe", "SEQ1", "SEQ2", "RANG", "Appreciations<br/>Nom de Professeur"]
    data = [[Paragraph(h, st_cb) for h in entetes]]
    style = [("GRID", (0,0), (-1,-1), 0.6, colors.black), ("BACKGROUND", (0,0), (-1,0), GRIS_ENTETE), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 2.5), ("BOTTOMPADDING", (0,0), (-1,-1), 2.5), ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3)]
    for grp in (1, 2, 3):
        items = [(mid, m) for mid, m in donnees_eleve["matieres"].items() if m["groupe"] == grp]
        if not items:
            continue
        for mid, m in items:
            moy_cl = moy_classe_mat.get(mid)
            data.append([Paragraph(_e(m["nom"]), st), Paragraph(_fmt(m["moy"]), st_c), Paragraph(_fmt_coef(m["coef"]), st_c), Paragraph(_fmt(m["total"]), st_c), Paragraph(_fmt(moy_cl) if moy_cl else "-", st_c), Paragraph(_fmt(m["seq1"]), st_c), Paragraph(_fmt(m["seq2"]), st_c), Paragraph(_rang(m["rang"]), st_c), Paragraph((_e(m["appreciation"]) or "-") + "<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<font color='#444444'>" + _e(m["prof"]) + "</font>", st)])
        g = donnees_eleve["groupes"][grp]
        r = len(data)
        data.append([Paragraph("MATIERES DU 1er GROUPE" if grp == 1 else "MATIERES DU " + str(grp) + "eme GROUPE", st_b), Paragraph(_fmt(g["moy"]), st_cb), Paragraph(_fmt_coef(g["coefs"]) if AFFICHER_TOTAL_COEFS else "", st_cb), Paragraph(_fmt(g["pts"]) if g["coefs"] else "-", st_cb), Paragraph("<i>" + _e(nom_etab) + "</i>", st_fil), "", "", "", ""])
        style += [("BACKGROUND", (0,r), (-1,r), GRIS_LIGNE), ("SPAN", (4,r), (8,r))]
    r = len(data)
    data.append([Paragraph("Moyenne Generale", st_b), Paragraph(_fmt(moy_gen), st_cb), Paragraph(_fmt_coef(donnees_eleve["total_coefs"]) if AFFICHER_TOTAL_COEFS else "", st_cb), Paragraph(_fmt(donnees_eleve["total_points"]) if donnees_eleve["total_coefs"] else "-", st_cb), Paragraph(_fmt(stats_classe.get("moy_classe_gen")) if stats_classe.get("moy_classe_gen") is not None else "-", st_cb), Paragraph(_fmt(donnees_eleve["moy_seq1"]), st_cb), Paragraph(_fmt(donnees_eleve["moy_seq2"]), st_cb), Paragraph(_rang(donnees_eleve.get("rang_gen", "-")), st_cb), Paragraph("", st)])
    style += [("BACKGROUND", (0,r), (-1,r), GRIS_LIGNE)]
    t_notes = Table(data, colWidths=[4.3*cm, 1.5*cm, 1.0*cm, 1.5*cm, 1.4*cm, 1.2*cm, 1.2*cm, 1.6*cm, 5.6*cm], repeatRows=1)
    t_notes.setStyle(TableStyle(style))
    story.append(t_notes)
    story.append(Paragraph(_e(params_etab.get("mention_edition", "Bulletin edite par le Secretariat du College")), st_small_c))
    story.append(Spacer(1, 0.15*cm))
    cases = _cases_travail(moy_gen)
    bloc1 = [Paragraph("<b>Moyenne Trimestrielle :</b> &nbsp; <b>" + _fmt(moy_gen) + "</b> /20", st_result_big), Paragraph("<b>Rang Trimestriel :</b> &nbsp; <b>" + _rang(donnees_eleve["rang_gen"]) + "</b>", st_result_big), Spacer(1, 0.12*cm), Paragraph("Moy. Trim./20 (par matiere) = <b>(SEQ1 + SEQ2) / 2</b>", st_small), Paragraph("Moyenne Trimestrielle = <b>Somme (Moy x Coef) / Somme Coef</b>", st_small)]
    mini = Table([["", Paragraph("<b>SEQ 1</b>", st_small_c), Paragraph("<b>SEQ 2</b>", st_small_c), Paragraph("<b>TRIM</b>", st_small_c)], [Paragraph("<b>Moy</b>", st_small_c), Paragraph(_fmt(donnees_eleve["moy_seq1"]), st_small_c), Paragraph(_fmt(donnees_eleve["moy_seq2"]), st_small_c), Paragraph(_fmt(moy_gen), st_small_c)], [Paragraph("<b>Rang</b>", st_small_c), Paragraph(_rang(donnees_eleve.get("rang_seq1")), st_small_c), Paragraph(_rang(donnees_eleve.get("rang_seq2")), st_small_c), Paragraph(_rang(donnees_eleve["rang_gen"]), st_small_c)]], colWidths=[0.85*cm, 1.1*cm, 1.1*cm, 1.1*cm])
    mini.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.5, colors.black), ("BACKGROUND", (0,0), (-1,0), GRIS_LIGNE), ("TOPPADDING", (0,0), (-1,-1), 1), ("BOTTOMPADDING", (0,0), (-1,-1), 1), ("LEFTPADDING", (0,0), (-1,-1), 1), ("RIGHTPADDING", (0,0), (-1,-1), 1)]))
    bloc2 = [mini, Spacer(1, 0.1*cm), Paragraph("<u><b>PROFIL DE LA CLASSE :</b></u>", st_small), Paragraph("Moy Premier : &nbsp;<b>" + _fmt(stats_classe["forte_moy"]) + "</b> /20", st), Paragraph("Moy Dernier : &nbsp;<b>" + _fmt(stats_classe["faible_moy"]) + "</b> /20", st), Paragraph("Moy Classe : &nbsp;<b>" + _fmt(stats_classe["moy_classe_gen"]) + "</b> /20", st)]
    style_cases = TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 1.5), ("BOTTOMPADDING", (0,0), (-1,-1), 1.5), ("LEFTPADDING", (0,0), (-1,-1), 0), ("RIGHTPADDING", (0,0), (-1,-1), 2)])
    bloc3 = Table([[_case("X" if cases["avertissement"] else "", st_cb), Paragraph("Avertissements", st)], [_case("X" if cases["blame"] else "", st_cb), Paragraph("Blames", st)], [_case("X" if cases["tableau_honneur"] else "", st_cb), Paragraph("Tableau d'Honneur", st)], [_case("X" if cases["encouragement"] else "", st_cb), Paragraph("Encouragement", st)], [_case("X" if cases["felicitation"] else "", st_cb), Paragraph("Felicitation", st)]], colWidths=[0.9*cm, 3.6*cm])
    bloc3.setStyle(style_cases)
    bloc4 = Table([[_case(str(discipline.get("heures_absences") or 0), st_cb), Paragraph("Heures d'absences", st)], [_case(str(discipline.get("avertissements") or 0), st_cb), Paragraph("Avertissements", st)], [_case(str(discipline.get("blames") or 0), st_cb), Paragraph("Blame", st)], [_case(str(discipline.get("jours_exclusion") or 0), st_cb), Paragraph("Jours d'exclusions temporaires", st)]], colWidths=[0.9*cm, 3.6*cm])
    bloc4.setStyle(style_cases)
    t_bas = Table([[Paragraph("RESULTAT TRIMESTRIEL DE L'ELEVE", st_bloc_titre), Paragraph("PROFIL DE LA CLASSE", st_bloc_titre), Paragraph("DISCIPLINE ET DECISION", st_bloc_titre), ""], [bloc1, bloc2, bloc3, bloc4]], colWidths=[5.0*cm, 4.6*cm, 4.85*cm, 4.85*cm])
    t_bas.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.8, colors.black), ("SPAN", (2,0), (3,0)), ("VALIGN", (0,0), (-1,0), "MIDDLE"), ("VALIGN", (0,1), (-1,1), "TOP"), ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3), ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4)]))
    story.append(t_bas)
    story.append(Spacer(1, 0.2*cm))
    ville = params_etab.get("etablissement_ville", "Maroua")
    signataire = params_etab.get("etablissement_signataire", "LE PRINCIPAL")
    date_edition = params_etab.get("date_edition") or date.today().strftime("%d/%m/%Y")
    efforts = _efforts_a_fournir(donnees_eleve["matieres"].values())
    apprec_travail = get_appreciation_matiere(moy_gen)
    competence = get_appreciation_generale(moy_gen)
    visa_box = Table([[""]], colWidths=[4.2*cm], rowHeights=[0.9*cm])
    visa_box.setStyle(TableStyle([("BOX", (0,0), (-1,-1), 0.6, colors.black)]))
    cell_apprec = [Paragraph("<b>" + _e(apprec_travail).upper() + "</b>" if apprec_travail else "-", st_cb)]
    if competence:
        cell_apprec.append(Paragraph("Competences : <b>" + competence + "</b>", st_small_c))
    cell_apprec.append(Spacer(1, 0.25*cm))
    cell_apprec.append(Paragraph("<b>VISA DU PARENT</b>", st_small_c))
    cell_apprec.append(Spacer(1, 0.15*cm))
    cell_apprec.append(visa_box)
    cell_decision = [Paragraph("<b>" + _e(decision) + "</b>", st), Spacer(1, 0.12*cm), Paragraph("<u><b>Des efforts s'imposent en :</b></u>", st), Paragraph(_e(efforts), st)]
    cell_signature = [Paragraph("Fait a " + _e(ville) + ", le <b>" + _e(date_edition) + "</b>", st_r), Spacer(1, 0.9*cm), Paragraph("<b>" + _e(signataire) + "</b>", st_rb)]
    t_foot = Table([[Paragraph("<b>APPRECIATION DU TRAVAIL</b>", st), Paragraph("<b>DECISION DU CONSEIL DE CLASSE</b>", st_c), ""], [cell_apprec, cell_decision, cell_signature]], colWidths=[5.2*cm, 8.8*cm, 4.6*cm])
    t_foot.setStyle(TableStyle([("BOX", (0,1), (0,1), 0.8, colors.black), ("BOX", (1,1), (1,1), 1.0, colors.black), ("VALIGN", (0,0), (-1,-1), "TOP"), ("VALIGN", (0,1), (0,1), "MIDDLE"), ("TOPPADDING", (0,1), (-1,1), 5), ("BOTTOMPADDING", (0,1), (-1,1), 5), ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 12)]))
    story.append(t_foot)
    doc.build(story, onFirstPage=_filigrane("COBINSA"), onLaterPages=_filigrane("COBINSA"))
    return chemin_fichier_pdf