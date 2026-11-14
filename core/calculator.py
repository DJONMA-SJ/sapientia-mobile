"""
MOTEUR DE CALCULS - GESTION DES BULLETINS
Calcule les moyennes, totaux, rangs, appréciations et statistiques de classe.
"""

# ==========================================
# 1. FONCTIONS DE SÉUILS ET APPRÉCIATIONS
# ==========================================

def get_appreciation_matiere(note):
    """
    Retourne l'appréciation par matière selon la moyenne trimestrielle de la matière.
    """
    if note is None:
        return ""
    if note >= 18:
        return "Excellent"
    elif note >= 16:
        return "Très bien"
    elif note >= 14:
        return "Bien"
    elif note >= 12:
        return "Assez Bien"
    elif note >= 10:
        return "Passable"
    elif note >= 7:
        return "Médiocre"
    else:
        return "Faible"


def get_appreciation_generale(moyenne):
    """
    Retourne le profil de compétence général (CA / ECA / NA).
    """
    if moyenne is None:
        return ""
    if moyenne >= 14:
        return "CA"   # Compétences Acquises
    elif moyenne >= 10:
        return "ECA"  # En Cours d'Acquisition
    else:
        return "NA"   # Non Acquises


def get_mention_statistique(moyenne):
    """
    Retourne la mention/sanction pour les tableaux statistiques.
    """
    if moyenne is None:
        return None
    if moyenne >= 16:
        return "THF"
    elif moyenne >= 14:
        return "Tableau d'Honneur"
    elif moyenne >= 12:
        return "Assez Bien"
    elif moyenne >= 10:
        return "Passable"
    elif moyenne >= 7:
        return "Avertissement"
    else:
        return "Blâme"


def get_decision_conseil(moyenne):
    """
    Génère automatiquement la décision du conseil de classe.
    """
    if moyenne is None:
        return "NON ÉVALUÉ"
    if moyenne >= 16:
        return "EXCELLENT TRAVAIL - FÉLICITATIONS DU CONSEIL"
    elif moyenne >= 14:
        return "TRÈS BON TRAVAIL - TABLEAU D'HONNEUR"
    elif moyenne >= 12:
        return "BON TRAVAIL - ENCOURAGEMENTS"
    elif moyenne >= 10:
        return "TRAVAIL PASSABLE - DOIT PERSÉVÉRER"
    elif moyenne >= 7:
        return "TRAVAIL INSUFFISANT - AVERTISSEMENT EN TRAVAIL"
    else:
        return "TRAVAIL TRÈS INSUFFISANT - BLÂME EN TRAVAIL"


# ==========================================
# 2. CALCUL DES RANGS
# ==========================================

def calculer_rangs(liste_valeurs):
    """
    Prend une liste de valeurs (ex: moyennes) et retourne une liste de rangs.
    Gère les égalités (ex: 1er ex aequo).
    Ex: [14.5, 16.0, 14.5, 10.0] -> [2, 1, 2, 4]
    """
    # Filtrer les valeurs None/vides tout en gardant l'index d'origine
    index_valeurs = [(i, val) for i, val in enumerate(liste_valeurs) if val is not None]
    
    # Trier par valeur décroissante
    index_valeurs_triees = sorted(index_valeurs, key=lambda x: x[1], reverse=True)
    
    rangs = [None] * len(liste_valeurs)
    
    if not index_valeurs_triees:
        return rangs

    rang_actuel = 1
    for k, (orig_idx, val) in enumerate(index_valeurs_triees):
        if k > 0 and val < index_valeurs_triees[k - 1][1]:
            rang_actuel = k + 1
        rangs[orig_idx] = rang_actuel

    return rangs


# ==========================================
# 3. MOTEUR DE CALCULS PAR CLASSE
# ==========================================

def calculer_bulletins_classe(conn, classe_id, trimestre):
    """
    Calcule l'ensemble des résultats de tous les élèves d'une classe pour un trimestre.
    Retourne un dictionnaire contenant les résultats complets + stats.
    """
    cursor = conn.cursor()

    # 1. Récupérer les élèves de la classe
    cursor.execute("""
        SELECT id, matricule, nom, prenom, sexe, redoublant 
        FROM eleves WHERE classe_id = ? ORDER BY nom, prenom
    """, (classe_id,))
    eleves = cursor.fetchall()
    effectif = len(eleves)
    try:
        cursor.execute("SELECT id, photo FROM eleves WHERE classe_id = ?", (classe_id,))
        photo_map = {r[0]: (r[1] or "") for r in cursor.fetchall()}
    except Exception:
        photo_map = {}

    if effectif == 0:
        return {"erreur": "Aucun élève dans cette classe."}

    # 2. Récupérer les matières de la classe
    cursor.execute("""
        SELECT id, nom, groupe, coefficient, enseignant, ordre 
        FROM matieres WHERE classe_id = ? ORDER BY groupe, ordre
    """, (classe_id,))
    matieres = cursor.fetchall()

    if not matieres:
        return {"erreur": "Aucune matière configurée pour cette classe."}

    # 3. Structure pour stocker les résultats temporaires
    # eleve_id -> { 'info': ..., 'notes': {matiere_id: {...}}, 'moy_gen': ..., 'tot_pts': ... }
    resultats_eleves = {}
    for el in eleves:
        resultats_eleves[el[0]] = {
            "info": {
                "id": el[0], "matricule": el[1], "nom": el[2], 
                "prenom": el[3], "sexe": el[4], "redoublant": el[5]
            },
            "matieres": {},
            "moy_seq1": None,
            "moy_seq2": None,
            "moy_gen": None,
            "total_points": 0.0,
            "total_coefs": 0.0,
            "groupes": {1: {"pts": 0, "coefs": 0, "moy": None},
                        2: {"pts": 0, "coefs": 0, "moy": None},
                        3: {"pts": 0, "coefs": 0, "moy": None}}
        }

    # 4. Parcourir les matières et calculer les notes de chaque élève
    moyennes_matiere_classe = {m[0]: [] for m in matieres}  # matiere_id -> [moyennes des élèves]

    for m in matieres:
        mat_id, mat_nom, mat_grp, mat_coef, mat_prof, _ = m

        for el_id in resultats_eleves:
            cursor.execute("""
                SELECT seq1, seq2 FROM notes 
                WHERE eleve_id = ? AND matiere_id = ? AND trimestre = ?
            """, (el_id, mat_id, trimestre))
            note_row = cursor.fetchone()

            seq1 = note_row[0] if note_row else None
            seq2 = note_row[1] if note_row else None

            # Calcul moyenne matière
            if seq1 is not None and seq2 is not None:
                moy_mat = round((seq1 + seq2) / 2.0, 2)
            elif seq1 is not None:
                moy_mat = seq1
            elif seq2 is not None:
                moy_mat = seq2
            else:
                moy_mat = None

            total_mat = round(moy_mat * mat_coef, 2) if moy_mat is not None else None
            apprec_mat = get_appreciation_matiere(moy_mat)

            # Enregistrer dans l'élève
            resultats_eleves[el_id]["matieres"][mat_id] = {
                "nom": mat_nom, "groupe": mat_grp, "coef": mat_coef, "prof": mat_prof,
                "seq1": seq1, "seq2": seq2, "moy": moy_mat, "total": total_mat,
                "appreciation": apprec_mat, "rang": None
            }

            if moy_mat is not None:
                moyennes_matiere_classe[mat_id].append(moy_mat)
                resultats_eleves[el_id]["total_points"] += total_mat
                resultats_eleves[el_id]["total_coefs"] += mat_coef
                
                # Sous-totaux par groupe
                resultats_eleves[el_id]["groupes"][mat_grp]["pts"] += total_mat
                resultats_eleves[el_id]["groupes"][mat_grp]["coefs"] += mat_coef

    # 5. Calcul des moyennes générales et sous-groupes de chaque élève
    liste_moy_gen = []
    liste_moy_seq1 = []
    liste_moy_seq2 = []
    ids_eleves = list(resultats_eleves.keys())

    for el_id in ids_eleves:
        d = resultats_eleves[el_id]
        
        # Moyenne Générale
        if d["total_coefs"] > 0:
            d["moy_gen"] = round(d["total_points"] / d["total_coefs"], 2)
        liste_moy_gen.append(d["moy_gen"])

        # Moyennes des sous-groupes
        for grp in d["groupes"]:
            if d["groupes"][grp]["coefs"] > 0:
                d["groupes"][grp]["moy"] = round(d["groupes"][grp]["pts"] / d["groupes"][grp]["coefs"], 2)

        # Moyenne Séquence 1 & 2 globales
        s1_notes = [m["seq1"] for m in d["matieres"].values() if m["seq1"] is not None]
        s2_notes = [m["seq2"] for m in d["matieres"].values() if m["seq2"] is not None]
        d["moy_seq1"] = round(sum(s1_notes) / len(s1_notes), 2) if s1_notes else None
        d["moy_seq2"] = round(sum(s2_notes) / len(s2_notes), 2) if s2_notes else None
        
        liste_moy_seq1.append(d["moy_seq1"])
        liste_moy_seq2.append(d["moy_seq2"])

    # 6. Calcul des rangs
    rangs_gen = calculer_rangs(liste_moy_gen)
    for idx, el_id in enumerate(ids_eleves):
        r = rangs_gen[idx]
        resultats_eleves[el_id]["rang_gen"] = f"{r}/{effectif}" if r else "-"
        resultats_eleves[el_id]["rang_brut"] = r

    # Rangs par matière
    for mat_id in moyennes_matiere_classe:
        notes_mat_eleves = [resultats_eleves[el_id]["matieres"][mat_id]["moy"] for el_id in ids_eleves]
        rangs_mat = calculer_rangs(notes_mat_eleves)
        for idx, el_id in enumerate(ids_eleves):
            rm = rangs_mat[idx]
            resultats_eleves[el_id]["matieres"][mat_id]["rang"] = f"{rm}/{effectif}" if rm else "-"

    # 7. Calcul des moyennes de classe par matière
    moyennes_classe_par_matiere = {}
    for mat_id, liste_notes in moyennes_matiere_classe.items():
        if liste_notes:
            moyennes_classe_par_matiere[mat_id] = round(sum(liste_notes) / len(liste_notes), 2)
        else:
            moyennes_classe_par_matiere[mat_id] = 0.0

    # 8. STATISTIQUES GLOBALES DE LA CLASSE
    moy_gen_valides = [m for m in liste_moy_gen if m is not None]
    moy_classe_generale = round(sum(moy_gen_valides) / len(moy_gen_valides), 2) if moy_gen_valides else 0.0

    # Trouver min et max
    forte_moy = max(moy_gen_valides) if moy_gen_valides else 0.0
    faible_moy = min(moy_gen_valides) if moy_gen_valides else 0.0

    eleve_forte_moy = ""
    eleve_faible_moy = ""
    for el_id, d in resultats_eleves.items():
        if d["moy_gen"] == forte_moy and not eleve_forte_moy:
            eleve_forte_moy = f"{d['info']['nom']} {d['info']['prenom']}"
        if d["moy_gen"] == faible_moy and not eleve_faible_moy:
            eleve_faible_moy = f"{d['info']['nom']} {d['info']['prenom']}"

    # Statistiques Réussite / Échec / Mentions ventilées par Sexe
    stats = {
        "effectif_total": effectif,
        "garcons": sum(1 for d in resultats_eleves.values() if d["info"]["sexe"] == "M"),
        "filles": sum(1 for d in resultats_eleves.values() if d["info"]["sexe"] == "F"),
        "redoublants": sum(1 for d in resultats_eleves.values() if d["info"]["redoublant"] == 1),
        "reussite": {"M": 0, "F": 0, "total": 0},
        "echec": {"M": 0, "F": 0, "total": 0},
        "mentions": {
            "Blâme": {"M": 0, "F": 0, "total": 0},
            "Avertissement": {"M": 0, "F": 0, "total": 0},
            "Passable": {"M": 0, "F": 0, "total": 0},
            "Assez Bien": {"M": 0, "F": 0, "total": 0},
            "Tableau d'Honneur": {"M": 0, "F": 0, "total": 0},
            "THF": {"M": 0, "F": 0, "total": 0},
        },
        "moy_classe_gen": moy_classe_generale,
        "forte_moy": forte_moy,
        "eleve_forte_moy": eleve_forte_moy,
        "faible_moy": faible_moy,
        "eleve_faible_moy": eleve_faible_moy
    }

    for d in resultats_eleves.values():
        sexe = d["info"]["sexe"]
        mg = d["moy_gen"]
        if mg is not None:
            if mg >= 10:
                stats["reussite"][sexe] += 1
                stats["reussite"]["total"] += 1
            else:
                stats["echec"][sexe] += 1
                stats["echec"]["total"] += 1

            mention = get_mention_statistique(mg)
            if mention in stats["mentions"]:
                stats["mentions"][mention][sexe] += 1
                stats["mentions"][mention]["total"] += 1

    return {
        "eleves": resultats_eleves,
        "matieres": matieres,
        "moyennes_classe_matiere": moyennes_classe_par_matiere,
        "stats": stats
    }
def calculer_bulletins_annuels(conn, classe_id):
    cursor = conn.cursor()

    cursor.execute("SELECT id, matricule, nom, prenom, sexe, redoublant FROM eleves WHERE classe_id = ? ORDER BY nom, prenom", (classe_id,))
    eleves = cursor.fetchall()
    effectif = len(eleves)
    if effectif == 0:
        return {"erreur": "Aucun eleve dans cette classe."}

    try:
        cursor.execute("SELECT id, photo FROM eleves WHERE classe_id = ?", (classe_id,))
        photo_map = {r[0]: (r[1] or "") for r in cursor.fetchall()}
    except Exception:
        photo_map = {}
    
    cursor.execute("SELECT id, nom, groupe, coefficient, enseignant, ordre FROM matieres WHERE classe_id = ? ORDER BY groupe, ordre", (classe_id,))
    matieres = cursor.fetchall()
    if not matieres:
        return {"erreur": "Aucune matiere pour cette classe."}

    resultats = {}
    for el in eleves:
        resultats[el[0]] = {
            "info": {"id": el[0], "matricule": el[1], "nom": el[2], "prenom": el[3], "sexe": el[4], "redoublant": el[5]},
            "matieres": {},
            "moy_gen_t1": None, "moy_gen_t2": None, "moy_gen_t3": None,
            "moy_gen_an": None,
            "total_points_an": 0.0, "total_coefs_an": 0.0,
            "groupes": {1: {"pts": 0, "coefs": 0, "moy": None}, 2: {"pts": 0, "coefs": 0, "moy": None}, 3: {"pts": 0, "coefs": 0, "moy": None}},
            "photo": photo_map.get(el[0], ""),
        }

    moyennes_mat_classe = {m[0]: [] for m in matieres}

    for m in matieres:
        mat_id, mat_nom, mat_grp, mat_coef, mat_prof, _ = m
        for el_id in resultats:
            moy_trims = []
            for t in (1, 2, 3):
                cursor.execute("SELECT seq1, seq2 FROM notes WHERE eleve_id = ? AND matiere_id = ? AND trimestre = ?", (el_id, mat_id, t))
                row = cursor.fetchone()
                s1 = row[0] if row else None
                s2 = row[1] if row else None
                if s1 is not None and s2 is not None:
                    moy = round((s1 + s2) / 2.0, 2)
                elif s1 is not None:
                    moy = float(s1)
                elif s2 is not None:
                    moy = float(s2)
                else:
                    moy = None
                moy_trims.append(moy)

            moy_t1, moy_t2, moy_t3 = moy_trims
            vals = [v for v in moy_trims if v is not None]
            if vals:
                moy_an = round(sum(vals) / len(vals), 2)
            else:
                moy_an = None

            total_an = round(moy_an * mat_coef, 2) if moy_an is not None else None

            resultats[el_id]["matieres"][mat_id] = {
                "nom": mat_nom, "groupe": mat_grp, "coef": mat_coef, "prof": mat_prof,
                "moy_t1": moy_t1, "moy_t2": moy_t2, "moy_t3": moy_t3,
                "moy_an": moy_an, "total_an": total_an,
                "appreciation": get_appreciation_matiere(moy_an),
                "rang": None
            }

            if moy_an is not None:
                moyennes_mat_classe[mat_id].append(moy_an)
                resultats[el_id]["total_points_an"] += total_an
                resultats[el_id]["total_coefs_an"] += mat_coef
                resultats[el_id]["groupes"][mat_grp]["pts"] += total_an
                resultats[el_id]["groupes"][mat_grp]["coefs"] += mat_coef

    # Moyennes générales annuelles + rappels T1 T2 T3 par élève
    ids = list(resultats.keys())
    liste_moy_an = []
    for el_id in ids:
        d = resultats[el_id]
        if d["total_coefs_an"] > 0:
            d["moy_gen_an"] = round(d["total_points_an"] / d["total_coefs_an"], 2)
        liste_moy_an.append(d["moy_gen_an"])

        for grp in d["groupes"]:
            if d["groupes"][grp]["coefs"] > 0:
                d["groupes"][grp]["moy"] = round(d["groupes"][grp]["pts"] / d["groupes"][grp]["coefs"], 2)

        # Rappels trimestriels : recalcule Somme(MoyTx x Coef)/Somme Coefs
        for t_idx, key in enumerate(["moy_gen_t1", "moy_gen_t2", "moy_gen_t3"], start=0):
            pts = 0.0
            cfs = 0.0
            for mat_id, md in d["matieres"].items():
                mv = [md["moy_t1"], md["moy_t2"], md["moy_t3"]][t_idx]
                if mv is not None:
                    pts += mv * md["coef"]
                    cfs += md["coef"]
            d[key] = round(pts / cfs, 2) if cfs > 0 else None

    rangs_an = calculer_rangs(liste_moy_an)
    for idx, el_id in enumerate(ids):
        r = rangs_an[idx]
        resultats[el_id]["rang_an"] = str(r) + "/" + str(effectif) if r else "-"
        resultats[el_id]["rang_brut"] = r

    for mat_id in moyennes_mat_classe:
        notes_m = [resultats[e]["matieres"][mat_id]["moy_an"] for e in ids]
        rangs_m = calculer_rangs(notes_m)
        for idx, el_id in enumerate(ids):
            rm = rangs_m[idx]
            resultats[el_id]["matieres"][mat_id]["rang"] = str(rm) + "/" + str(effectif) if rm else "-"

    moy_classe_mat = {}
    for mat_id, lst in moyennes_mat_classe.items():
        moy_classe_mat[mat_id] = round(sum(lst) / len(lst), 2) if lst else 0.0

    vals_an = [v for v in liste_moy_an if v is not None]
    moy_classe_gen = round(sum(vals_an) / len(vals_an), 2) if vals_an else 0.0
    forte = max(vals_an) if vals_an else 0.0
    faible = min(vals_an) if vals_an else 0.0

    eleve_fort = ""
    eleve_faible = ""
    for el_id, d in resultats.items():
        if d["moy_gen_an"] == forte and not eleve_fort:
            eleve_fort = d["info"]["nom"] + " " + d["info"]["prenom"]
        if d["moy_gen_an"] == faible and not eleve_faible:
            eleve_faible = d["info"]["nom"] + " " + d["info"]["prenom"]


    stats = {
        "effectif_total": effectif,
        "garcons": sum(1 for d in resultats.values() if d["info"]["sexe"] == "M"),
        "filles": sum(1 for d in resultats.values() if d["info"]["sexe"] == "F"),
        "redoublants": sum(1 for d in resultats.values() if d["info"]["redoublant"] == 1),
        "reussite": {"M": 0, "F": 0, "total": 0},
        "echec": {"M": 0, "F": 0, "total": 0},
        "mentions": {
            "Blame": {"M": 0, "F": 0, "total": 0},
            "Avertissement": {"M": 0, "F": 0, "total": 0},
            "Passable": {"M": 0, "F": 0, "total": 0},
            "Assez Bien": {"M": 0, "F": 0, "total": 0},
            "Tableau d'Honneur": {"M": 0, "F": 0, "total": 0},
            "THF": {"M": 0, "F": 0, "total": 0},
        },
        "moy_classe_gen": moy_classe_gen,
        "forte_moy": forte,
        "eleve_forte_moy": eleve_fort,
        "faible_moy": faible,
        "eleve_faible_moy": eleve_faible
    }

    for d in resultats.values():
        mg = d["moy_gen_an"]
        if mg is None:
            continue
        sexe = d["info"]["sexe"]
        if mg >= 10:
            stats["reussite"][sexe] += 1
            stats["reussite"]["total"] += 1
        else:
            stats["echec"][sexe] += 1
            stats["echec"]["total"] += 1
        mention = get_mention_statistique(mg)
        if mention in stats["mentions"]:
            stats["mentions"][mention][sexe] += 1
            stats["mentions"][mention]["total"] += 1

    return {"eleves": resultats, "matieres": matieres, "moyennes_classe_matiere": moy_classe_mat, "stats": stats}


def get_decision_annuelle(moy_an):
    if moy_an is None:
        return "NON EVALUE"
    if moy_an >= 16:
        return "ADMIS - EXCELLENT TRAVAIL ANNUEL"
    if moy_an >= 14:
        return "ADMIS - TRES BON TRAVAIL ANNUEL"
    if moy_an >= 12:
        return "ADMIS - BON TRAVAIL"
    if moy_an >= 10:
        return "ADMIS - TRAVAIL PASSABLE"
    return "REDOUBLE - TRAVAIL INSUFFISANT"