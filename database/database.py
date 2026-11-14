import sqlite3
import os
import sys


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


BASE_DIR = get_base_dir()
DB_PATH = os.path.join(BASE_DIR, "gestion_bulletins.db")

# Ancien nom utilise dans certains scripts
ROOT_DIR = BASE_DIR
DB_NAME = DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE NOT NULL,
            prof_principal TEXT DEFAULT ''
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eleves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricule TEXT UNIQUE NOT NULL,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            sexe TEXT CHECK(sexe IN ('M', 'F')) NOT NULL,
            date_naissance TEXT,
            lieu_naissance TEXT,
            redoublant INTEGER DEFAULT 0,
            classe_id INTEGER NOT NULL,
            FOREIGN KEY (classe_id) REFERENCES classes(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matieres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            groupe INTEGER CHECK(groupe IN (1, 2, 3)) NOT NULL DEFAULT 1,
            coefficient REAL NOT NULL DEFAULT 1.0,
            enseignant TEXT DEFAULT '',
            ordre INTEGER DEFAULT 1,
            classe_id INTEGER NOT NULL,
            FOREIGN KEY (classe_id) REFERENCES classes(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eleve_id INTEGER NOT NULL,
            matiere_id INTEGER NOT NULL,
            trimestre INTEGER CHECK(trimestre IN (1, 2, 3)) NOT NULL,
            seq1 REAL CHECK(seq1 IS NULL OR (seq1 >= 0 AND seq1 <= 20)),
            seq2 REAL CHECK(seq2 IS NULL OR (seq2 >= 0 AND seq2 <= 20)),
            FOREIGN KEY (eleve_id) REFERENCES eleves(id) ON DELETE CASCADE,
            FOREIGN KEY (matiere_id) REFERENCES matieres(id) ON DELETE CASCADE,
            UNIQUE(eleve_id, matiere_id, trimestre)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS disciplines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eleve_id INTEGER NOT NULL,
            trimestre INTEGER CHECK(trimestre IN (1, 2, 3)) NOT NULL,
            heures_absences INTEGER DEFAULT 0,
            avertissements INTEGER DEFAULT 0,
            blames INTEGER DEFAULT 0,
            jours_exclusion INTEGER DEFAULT 0,
            FOREIGN KEY (eleve_id) REFERENCES eleves(id) ON DELETE CASCADE,
            UNIQUE(eleve_id, trimestre)
        )
    ''')
    cursor.execute("PRAGMA table_info(eleves)")
    cols = [r[1] for r in cursor.fetchall()]
    if "photo" not in cols:
        cursor.execute("ALTER TABLE eleves ADD COLUMN photo TEXT DEFAULT ''")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parametres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cle TEXT UNIQUE NOT NULL,
            valeur TEXT NOT NULL
        )
    ''')

    params_etab = [
    ('etablissement_nom', 'COLLEGE BILINGUE NOTRE DAME DE LA SAGESSE "SAPIENTIA"'),
    ('etablissement_tutelle', "MINESEC/REGION DE L'EXTREME-NORD/DEPARTEMENT DU DIAMARE/ ARRONDISSEMENT DE MAROUA II"),
    ('etablissement_devise', 'SAPIENTIA'),
    ('etablissement_bp', 'BP 228 Maroua'),
    ('etablissement_tel', '698 12 22 87'),
    ('etablissement_email', 'Sapientia237@gmail.com'),
    ('etablissement_ville', 'Maroua'),
    ('etablissement_signataire', 'LE PRINCIPAL'),
    ('devise_nationale', 'Paix - Travail - Patrie'),
    ('annee_scolaire', '2026/2027'),
    ('trimestre_actif', '1'),
    ('admin_password', 'admin123'),
    ('mention_nb', 'N.B : En cas de doute, bien vouloir saisir notre etablissement'),
    ('mention_edition', 'Bulletin edite par le Secretariat du College'),
]


    for cle, val in params_etab:
        cursor.execute("INSERT OR IGNORE INTO parametres (cle, valeur) VALUES (?, ?)", (cle, val))

    conn.commit()
    conn.close()
    print("Base initialisee : " + DB_PATH)


if __name__ == "__main__":
    init_db()