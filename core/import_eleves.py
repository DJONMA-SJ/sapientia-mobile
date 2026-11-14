"""
IMPORTATION DES LISTES D'ÉLÈVES
Avec détection automatique des lignes d'en-tête (gestion des bannières/titres Excel)
"""
import os
import re
import pandas as pd

COLONNES_CONNUES = {
    "matricule": [
        "matricule", "mat.", "mat", "n° matricule", "numero matricule",
        "n°", "numéro", "numero", "id", "code", "code élève", "code eleve"
    ],
    "nom": [
        "nom", "noms", "nom de famille", "name", "family name"
    ],
    "prenom": [
        "prenom", "prénom", "prenoms", "prénoms", "firstname", "first name"
    ],
    "sexe": [
        "sexe", "sex", "genre", "gender", "s"
    ],
    "date_naissance": [
        "date de naissance", "date naissance", "date_naissance", "naissance",
        "né le", "nee le", "né(e) le", "birthday", "date naiss", "d. naissance"
    ],
    "lieu_naissance": [
        "lieu de naissance", "lieu naissance", "lieu_naissance",
        "né à", "nee a", "lieu naiss", "l. naissance", "place of birth"
    ],
    "redoublant": [
        "redoublant", "redouble", "red", "redoub", "doublant"
    ],
    "nom_complet": [
        "nom et prenom", "nom et prénom", "noms et prenoms", "noms et prénoms",
        "nom complet", "élève", "eleve", "eleves", "full name", "student name", "noms & prenoms"
    ],
}


def _normaliser(texte):
    if texte is None:
        return ""
    t = str(texte).strip().lower()
    remplacements = {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "î": "i", "ï": "i",
        "ô": "o", "ö": "o",
        "ù": "u", "û": "u", "ü": "u",
        "ç": "c", "œ": "oe",
    }
    for a, b in remplacements.items():
        t = t.replace(a, b)
    t = re.sub(r"\s+", " ", t)
    return t


def _trouver_ligne_entete(df):
    """
    Cherche dans les 15 premières lignes la ligne qui contient les en-têtes (Matricule, Nom, etc.)
    """
    mots_cles = ["nom", "noms", "matricule", "prenom", "sexe", "eleve", "eleves"]
    
    # 1. Vérifier si l'en-tête actuel est déjà le bon
    colonnes_actuelles = [_normaliser(c) for c in df.columns]
    score_actuel = sum(1 for c in colonnes_actuelles if any(mc in c for mc in mots_cles))
    if score_actuel >= 2:
        return df

    # 2. Parcourir les 15 premières lignes pour trouver la vraie ligne d'en-tête
    for i in range(min(15, len(df))):
        ligne_vals = [_normaliser(val) for val in df.iloc[i].values]
        score = sum(1 for val in ligne_vals if any(mc in val for mc in mots_cles))
        
        if score >= 2:
            # Cette ligne est le vrai en-tête !
            nouveaux_headers = [str(val).strip() for val in df.iloc[i].values]
            nouveau_df = df.iloc[i+1:].copy()
            nouveau_df.columns = nouveaux_headers
            return nouveau_df.reset_index(drop=True)

    return df


def _mapper_colonnes(df):
    mapping = {}
    colonnes_df = { _normaliser(c): c for c in df.columns }

    for champ, aliases in COLONNES_CONNUES.items():
        for alias in aliases:
            alias_n = _normaliser(alias)
            # Correspondance exacte
            if alias_n in colonnes_df:
                mapping[champ] = colonnes_df[alias_n]
                break
            # Correspondance partielle
            for col_n, col_orig in colonnes_df.items():
                if alias_n in col_n or col_n in alias_n:
                    mapping[champ] = col_orig
                    break
            if champ in mapping:
                break
    return mapping


def _normaliser_sexe(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    v = str(val).strip().upper()
    if v in ("M", "MASCULIN", "GARCON", "GARÇON", "H", "HOMME", "MALE", "1"):
        return "M"
    if v in ("F", "FEMININ", "FÉMININ", "FILLE", "FEMME", "FEMALE", "2"):
        return "F"
    return None


def _normaliser_redoublant(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 0
    v = str(val).strip().upper()
    if v in ("1", "OUI", "O", "YES", "Y", "TRUE", "VRAI", "R", "REDOUBLANT", "D"):
        return 1
    return 0


def _split_nom_complet(texte):
    if not texte:
        return "", ""
    t = str(texte).strip()
    parts = t.split()
    if len(parts) == 1:
        return parts[0], ""
    if parts[0].isupper() and not parts[-1].isupper():
        return parts[0], " ".join(parts[1:])
    if parts[-1].isupper():
        return " ".join(parts), ""
    return " ".join(parts[:-1]), parts[-1]


def _dataframe_vers_eleves(df, mapping):
    eleves = []
    erreurs = []

    for idx, row in df.iterrows():
        ligne_n = idx + 2

        # --- Matricule ---
        matricule = ""
        if "matricule" in mapping:
            val = row.get(mapping["matricule"])
            if val is not None and not pd.isna(val):
                if isinstance(val, float) and val == int(val):
                    matricule = str(int(val))
                else:
                    matricule = str(val).strip()

        # --- Nom / Prénom ---
        nom, prenom = "", ""
        if "nom" in mapping and "prenom" in mapping:
            n = row.get(mapping["nom"])
            p = row.get(mapping["prenom"])
            nom = "" if n is None or pd.isna(n) else str(n).strip()
            prenom = "" if p is None or pd.isna(p) else str(p).strip()
        elif "nom_complet" in mapping:
            nc = row.get(mapping["nom_complet"])
            nom, prenom = _split_nom_complet(nc)
        elif "nom" in mapping:
            n = row.get(mapping["nom"])
            nom = "" if n is None or pd.isna(n) else str(n).strip()

        # Ligne vide → on ignore
        if not matricule and not nom and not prenom:
            continue

        # Si pas de matricule, on génère un matricule temporaire à partir du nom
        if not matricule and nom:
            matricule = f"AUTO_{re.sub(r'[^A-Z0-9]', '', nom.upper())[:6]}_{idx+1}"

        if not nom:
            erreurs.append(f"Ligne {ligne_n} : Nom manquant (ignorée).")
            continue

        # --- Sexe ---
        sexe = None
        if "sexe" in mapping:
            sexe = _normaliser_sexe(row.get(mapping["sexe"]))

        # --- Dates / lieux ---
        date_n, lieu_n = "", ""
        if "date_naissance" in mapping:
            d = row.get(mapping["date_naissance"])
            if d is not None and not pd.isna(d):
                if hasattr(d, "strftime"):
                    date_n = d.strftime("%d/%m/%Y")
                else:
                    date_n = str(d).strip()

        if "lieu_naissance" in mapping:
            l = row.get(mapping["lieu_naissance"])
            if l is not None and not pd.isna(l):
                lieu_n = str(l).strip()

        # --- Redoublant ---
        red = 0
        if "redoublant" in mapping:
            red = _normaliser_redoublant(row.get(mapping["redoublant"]))

        eleves.append({
            "matricule": matricule,
            "nom": nom.upper(),
            "prenom": prenom.title() if prenom else "",
            "sexe": sexe or "M",
            "date_naissance": date_n,
            "lieu_naissance": lieu_n,
            "redoublant": red,
            "sexe_manquant": sexe is None,
        })

    return eleves, erreurs


def lire_fichier_excel(chemin):
    ext = os.path.splitext(chemin)[1].lower()

    if ext == ".csv":
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            for sep in (";", ",", "\t"):
                try:
                    df = pd.read_csv(chemin, sep=sep, encoding=enc, dtype=str, header=None)
                    if df.shape[1] >= 2:
                        break
                except Exception:
                    df = None
            if df is not None and df.shape[1] >= 2:
                break
        if df is None:
            raise ValueError("Impossible de lire le fichier CSV.")
    else:
        df = pd.read_excel(chemin, dtype=str, header=None, engine="openpyxl" if ext == ".xlsx" else None)

    # Nettoyage et recherche automatique de l'en-tête
    df = df.dropna(how="all").reset_index(drop=True)
    df = _trouver_ligne_entete(df)

    mapping = _mapper_colonnes(df)
    eleves, erreurs = _dataframe_vers_eleves(df, mapping)
    return eleves, mapping, erreurs, df.head(8)


def lire_fichier_word(chemin):
    try:
        from docx import Document
    except ImportError:
        raise ImportError("Installez python-docx : pip install python-docx")

    doc = Document(chemin)
    if not doc.tables:
        raise ValueError("Aucun tableau trouvé dans ce document Word.")

    meilleur = None
    meilleur_score = -1

    for table in doc.tables:
        rows = []
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                rows.append(cells)
        if len(rows) < 2:
            continue

        headers = rows[0]
        data = rows[1:]
        n = len(headers)
        data = [r + [""] * (n - len(r)) for r in data]
        data = [r[:n] for r in data]

        df = pd.DataFrame(data, columns=headers)
        df = _trouver_ligne_entete(df)
        mapping = _mapper_colonnes(df)
        score = len(mapping)

        if score > meilleur_score:
            meilleur_score = score
            meilleur = (df, mapping)

    if not meilleur or meilleur_score == 0:
        raise ValueError("Impossible d'identifier les colonnes (Nom, Matricule...) dans les tableaux Word.")

    df, mapping = meilleur
    eleves, erreurs = _dataframe_vers_eleves(df, mapping)
    return eleves, mapping, erreurs, df.head(8)


def importer_eleves_dans_bdd(conn, classe_id, eleves, ecraser_existants=False):
    cursor = conn.cursor()
    ajoutes, ignores, maj = 0, 0, 0
    details = []

    for el in eleves:
        cursor.execute("SELECT id FROM eleves WHERE matricule = ?", (el["matricule"],))
        existant = cursor.fetchone()

        if existant:
            if ecraser_existants:
                cursor.execute("""
                    UPDATE eleves SET nom=?, prenom=?, sexe=?, date_naissance=?,
                    lieu_naissance=?, redoublant=?, classe_id=?
                    WHERE matricule=?
                """, (el["nom"], el["prenom"], el["sexe"], el["date_naissance"],
                      el["lieu_naissance"], el["redoublant"], classe_id, el["matricule"]))
                maj += 1
                details.append(f"🔄 {el['matricule']} — mis à jour")
            else:
                ignores += 1
                details.append(f"⏭️ {el['matricule']} — déjà existant (ignoré)")
        else:
            cursor.execute("""
                INSERT INTO eleves (matricule, nom, prenom, sexe, date_naissance,
                                    lieu_naissance, redoublant, classe_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (el["matricule"], el["nom"], el["prenom"], el["sexe"],
                  el["date_naissance"], el["lieu_naissance"], el["redoublant"], classe_id))
            ajoutes += 1
            details.append(f"✅ {el['matricule']} — {el['nom']} {el['prenom']}")

    conn.commit()
    return ajoutes, ignores, maj, details