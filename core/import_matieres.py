"""
IMPORTATION DES MATIÈRES / COEFFICIENTS
Depuis Excel (.xlsx, .xls, .csv) et Word (.docx)
"""
import os
import re
import pandas as pd

COLONNES_CONNUES = {
    "nom": [
        "matiere", "matière", "matieres", "matières", "discipline", "disciplines",
        "nom", "intitule", "intitulé", "libelle", "libellé", "cours", "subject"
    ],
    "groupe": [
        "groupe", "group", "grp", "groupe de matieres", "groupe matières",
        "famille", "categorie", "catégorie", "bloc"
    ],
    "coefficient": [
        "coefficient", "coef", "coeff", "coéfficient", "pondération", "ponderation",
        "poids", "credit", "crédit"
    ],
    "enseignant": [
        "enseignant", "professeur", "prof", "enseignant(e)", "professeurs",
        "nom du prof", "nom professeur", "teacher", "formateur"
    ],
    "ordre": [
        "ordre", "order", "n°", "numero", "numéro", "rang", "position", "classement"
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
    return re.sub(r"\s+", " ", t)


def _trouver_ligne_entete(df):
    """Trouve la vraie ligne d'en-têtes (ignore bannières / titres en haut du fichier)."""
    mots_cles = ["matiere", "matière", "discipline", "coef", "coefficient", "groupe", "prof", "enseignant"]
    colonnes_actuelles = [_normaliser(c) for c in df.columns]
    if sum(1 for c in colonnes_actuelles if any(mc in c for mc in mots_cles)) >= 1:
        return df

    for i in range(min(15, len(df))):
        ligne_vals = [_normaliser(v) for v in df.iloc[i].values]
        score = sum(1 for v in ligne_vals if any(mc in v for mc in mots_cles))
        if score >= 1:
            headers = [str(v).strip() for v in df.iloc[i].values]
            nouveau = df.iloc[i + 1:].copy()
            nouveau.columns = headers
            return nouveau.reset_index(drop=True)
    return df


def _mapper_colonnes(df):
    mapping = {}
    colonnes_df = {_normaliser(c): c for c in df.columns}
    for champ, aliases in COLONNES_CONNUES.items():
        for alias in aliases:
            alias_n = _normaliser(alias)
            if alias_n in colonnes_df:
                mapping[champ] = colonnes_df[alias_n]
                break
            for col_n, col_orig in colonnes_df.items():
                if alias_n in col_n or col_n in alias_n:
                    mapping[champ] = col_orig
                    break
            if champ in mapping:
                break
    return mapping


def _parse_groupe(val):
    """1 / '1er GROUPE' / 'Groupe 2' / 'G1' → 1, 2 ou 3."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 1
    s = str(val).strip().upper()
    if s in ("1", "1ER", "1ERE", "1ÈRE", "I", "G1", "GROUPE 1", "GROUPE1", "1ER GROUPE"):
        return 1
    if s in ("2", "2EME", "2ÈME", "II", "G2", "GROUPE 2", "GROUPE2", "2EME GROUPE", "2ÈME GROUPE"):
        return 2
    if s in ("3", "3EME", "3ÈME", "III", "G3", "GROUPE 3", "GROUPE3", "3EME GROUPE"):
        return 3
    # Cherche un chiffre dans la chaîne
    m = re.search(r"([123])", s)
    return int(m.group(1)) if m else 1


def _parse_coef(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(str(val).strip().replace(",", "."))
    except ValueError:
        return None


def _dataframe_vers_matieres(df, mapping):
    matieres, erreurs = [], []

    for idx, row in df.iterrows():
        ligne_n = idx + 2

        # Nom de la matière (obligatoire)
        nom = ""
        if "nom" in mapping:
            v = row.get(mapping["nom"])
            if v is not None and not pd.isna(v):
                nom = str(v).strip()
        if not nom:
            # Ligne vide → ignorer silencieusement
            continue

        # Coefficient
        coef = None
        if "coefficient" in mapping:
            coef = _parse_coef(row.get(mapping["coefficient"]))
        if coef is None:
            erreurs.append(f"Ligne {ligne_n} ({nom}) : coefficient manquant ou invalide → mis à 1.")
            coef = 1.0

        # Groupe
        groupe = 1
        if "groupe" in mapping:
            groupe = _parse_groupe(row.get(mapping["groupe"]))

        # Enseignant
        enseignant = ""
        if "enseignant" in mapping:
            v = row.get(mapping["enseignant"])
            if v is not None and not pd.isna(v):
                enseignant = str(v).strip()

        # Ordre d'affichage
        ordre = idx + 1
        if "ordre" in mapping:
            v = row.get(mapping["ordre"])
            try:
                if v is not None and not pd.isna(v):
                    ordre = int(float(v))
            except ValueError:
                pass

        matieres.append({
            "nom": nom,
            "groupe": groupe,
            "coefficient": coef,
            "enseignant": enseignant,
            "ordre": ordre,
        })

    return matieres, erreurs


def lire_matieres_excel(chemin):
    ext = os.path.splitext(chemin)[1].lower()
    if ext == ".csv":
        df = None
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            for sep in (";", ",", "\t"):
                try:
                    df = pd.read_csv(chemin, sep=sep, encoding=enc, dtype=str, header=None)
                    if df is not None and df.shape[1] >= 1:
                        break
                except Exception:
                    df = None
            if df is not None and df.shape[1] >= 1:
                break
        if df is None:
            raise ValueError("Impossible de lire le CSV.")
    else:
        df = pd.read_excel(chemin, dtype=str, header=None,
                           engine="openpyxl" if ext == ".xlsx" else None)

    df = df.dropna(how="all").reset_index(drop=True)
    df = _trouver_ligne_entete(df)
    mapping = _mapper_colonnes(df)
    matieres, erreurs = _dataframe_vers_matieres(df, mapping)
    return matieres, mapping, erreurs, df.head(10)


def lire_matieres_word(chemin):
    try:
        from docx import Document
    except ImportError:
        raise ImportError("Installez python-docx : pip install python-docx")

    doc = Document(chemin)
    if not doc.tables:
        raise ValueError("Aucun tableau trouvé dans ce document Word.")

    meilleur, meilleur_score = None, -1
    for table in doc.tables:
        rows = [[c.text.strip() for c in row.cells] for row in table.rows]
        rows = [r for r in rows if any(r)]
        if len(rows) < 2:
            continue
        headers, data = rows[0], rows[1:]
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
        raise ValueError("Impossible d'identifier les colonnes (Matière, Coef…) dans le Word.")

    df, mapping = meilleur
    matieres, erreurs = _dataframe_vers_matieres(df, mapping)
    return matieres, mapping, erreurs, df.head(10)


def importer_matieres_dans_bdd(conn, classe_id, matieres, ecraser_existants=False):
    """
    Insère les matières pour une classe.
    Si ecraser_existants=True : met à jour coef/groupe/prof si le nom existe déjà.
    Retourne (ajoutes, ignores, maj).
    """
    cursor = conn.cursor()
    ajoutes, ignores, maj = 0, 0, 0

    for m in matieres:
        cursor.execute(
            "SELECT id FROM matieres WHERE classe_id = ? AND LOWER(TRIM(nom)) = LOWER(TRIM(?))",
            (classe_id, m["nom"])
        )
        existant = cursor.fetchone()

        if existant:
            if ecraser_existants:
                cursor.execute("""
                    UPDATE matieres
                    SET groupe=?, coefficient=?, enseignant=?, ordre=?
                    WHERE id=?
                """, (m["groupe"], m["coefficient"], m["enseignant"], m["ordre"], existant[0]))
                maj += 1
            else:
                ignores += 1
        else:
            cursor.execute("""
                INSERT INTO matieres (nom, groupe, coefficient, enseignant, ordre, classe_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (m["nom"], m["groupe"], m["coefficient"], m["enseignant"], m["ordre"], classe_id))
            ajoutes += 1

    conn.commit()
    return ajoutes, ignores, maj