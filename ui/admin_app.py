import sys
import os
import json
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog

# Ajoute le dossier racine du projet pour les imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.database import get_connection, init_db
from core.calculator import calculer_bulletins_classe
from core.import_eleves import lire_fichier_excel, lire_fichier_word, importer_eleves_dans_bdd
from core.import_matieres import lire_matieres_excel, lire_matieres_word, importer_matieres_dans_bdd
from pdfs.pdf_generator import generer_bulletin_pdf
from pdfs.stats_generator import generer_fiche_statistiques_pdf

try:
    from core.calculator import calculer_bulletins_annuels
except ImportError:
    calculer_bulletins_annuels = None

try:
    from PIL import Image as PILImage
    PIL_DISPO = True
except ImportError:
    PIL_DISPO = False

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("green")

# Couleurs etablissement - vert / kaki du logo
VERT = "#1E6B3A"
VERT_FONCE = "#123F26"
VERT_HOVER = "#164E2A"
KAKI = "#B7A44A"
KAKI_FONCE = "#85742F"
FOND_CLAIR = "#F7F5EB"
BLANC = "#FFFFFF"
ROUGE = "#A93226"
ROUGE_HOVER = "#7B241C"

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return BASE_DIR

def creer_ctk_logo(taille=86):
    if not PIL_DISPO or not os.path.exists(LOGO_PATH):
        return None
    try:
        img = PILImage.open(LOGO_PATH).convert("RGBA")
        img.thumbnail((taille, taille), PILImage.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(img.size[0], img.size[1]))
    except Exception:
        return None


def creer_ctk_fond(taille=460, opacite=34):
    if not PIL_DISPO or not os.path.exists(LOGO_PATH):
        return None
    try:
        img = PILImage.open(LOGO_PATH).convert("RGBA")
        img.thumbnail((taille, taille), PILImage.LANCZOS)
        r, g, b, a = img.split()
        a = a.point(lambda p: p * opacite // 255)
        img.putalpha(a)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(img.size[0], img.size[1]))
    except Exception:
        return None


class AdminApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        init_db()

        self.title("GESTION DES BULLETINS - College Notre Dame de la Sagesse (ADMIN)")
        self.geometry("1180 x 740")
        self.minsize(980, 620)

        self._img_refs = []
        self._img_fond = None

        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("Treeview", background="#ffffff", foreground="#000000", rowheight=26, fieldbackground="#ffffff")
        self.style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'), background="#E9E2C8", foreground="#123F26", relief="flat")
        self.style.map("Treeview", background=[('selected', VERT)], foreground=[('selected', '#ffffff')])

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=VERT_FONCE)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(11, weight=1)

        logo_img = creer_ctk_logo(taille=86)
        if logo_img is not None:
            self._img_refs.append(logo_img)
            ctk.CTkLabel(self.sidebar_frame, image=logo_img, text="").grid(row=0, column=0, padx=20, pady=(18, 4))
            ctk.CTkLabel(self.sidebar_frame, text="BULLETIN PRO", font=ctk.CTkFont(size=19, weight="bold"), text_color=BLANC).grid(row=1, column=0, padx=20, pady=(0, 2))
            ctk.CTkLabel(self.sidebar_frame, text="College Notre Dame de la Sagesse", font=ctk.CTkFont(size=11), text_color=KAKI).grid(row=2, column=0, padx=20, pady=(0, 14))
            decal = 3
        else:
            ctk.CTkLabel(self.sidebar_frame, text="BULLETIN PRO", font=ctk.CTkFont(size=20, weight="bold"), text_color=BLANC).grid(row=0, column=0, padx=20, pady=(20, 20))
            decal = 1

        def bouton_menu(texte, commande, ligne):
            ctk.CTkButton(self.sidebar_frame, text=texte, command=commande, fg_color="transparent", text_color=BLANC, hover_color=KAKI_FONCE, anchor="w", font=ctk.CTkFont(size=13)).grid(row=ligne, column=0, padx=10, pady=3, sticky="ew")

        bouton_menu("Tableau de Bord", self.show_dashboard_frame, decal + 0)
        bouton_menu("Classes", self.show_classes_frame, decal + 1)
        bouton_menu("Eleves", self.show_eleves_frame, decal + 2)
        bouton_menu("Matieres & Coefs", self.show_matieres_frame, decal + 3)
        bouton_menu("Notes (Saisie & Vue)", self.show_notes_frame, decal + 4)
        bouton_menu("Discipline & Absences", self.show_discipline_frame, decal + 5)
        bouton_menu("Echanges Profs", self.show_echanges_frame, decal + 6)
        bouton_menu("Bulletins & PDF", self.show_pdf_frame, decal + 7)
        bouton_menu("Configuration", self.show_config_frame, decal + 8)

        self.theme_optionmenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["System", "Light", "Dark"], command=ctk.set_appearance_mode, fg_color=KAKI, button_color=KAKI_FONCE, button_hover_color=VERT_FONCE, text_color="#000000")
        self.theme_optionmenu.grid(row=12, column=0, padx=20, pady=(0, 20))

        self.main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=FOND_CLAIR)
        self.main_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self._dash_trim = "1"
        self.show_dashboard_frame()

    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self._ajouter_fond_logo()

    def _ajouter_fond_logo(self):
        try:
            if self._img_fond is None:
                self._img_fond = creer_ctk_fond(taille=460, opacite=34)
                if self._img_fond is not None:
                    self._img_refs.append(self._img_fond)
            if self._img_fond is not None:
                lbl = ctk.CTkLabel(self.main_frame, image=self._img_fond, text="")
                lbl.place(relx=0.5, rely=0.52, anchor="center")
                lbl.lower()
        except Exception:
            pass

    def get_classes_dict(self):
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id, nom FROM classes ORDER BY nom")
        rows = cursor.fetchall(); conn.close()
        return {r[1]: r[0] for r in rows}

    # ==========================================
    # 0. TABLEAU DE BORD
    # ==========================================
    def _on_dash_trim_change(self, val):
        self._dash_trim = val
        self.show_dashboard_frame()

    def show_dashboard_frame(self):
        self.clear_main_frame()
        if not hasattr(self, '_dash_trim'):
            self._dash_trim = "1"
        trim = self._dash_trim

        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT cle, valeur FROM parametres")
        params = dict(cur.fetchall())

        cur.execute("SELECT COUNT(*) FROM classes")
        nb_classes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM eleves")
        nb_eleves = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM matieres")
        nb_mat = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM notes WHERE trimestre=? AND (seq1 IS NOT NULL OR seq2 IS NOT NULL)", (int(trim),))
        nb_notes = cur.fetchone()[0]

        cur.execute("SELECT id, nom, prof_principal FROM classes ORDER BY nom")
        classes = cur.fetchall()

        infos_classes = []
        for cid, cnom, prof in classes:
            cur.execute("SELECT COUNT(*) FROM eleves WHERE classe_id=?", (cid,))
            eff = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM matieres WHERE classe_id=?", (cid,))
            nmat = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM notes n JOIN eleves e ON e.id=n.eleve_id WHERE e.classe_id=? AND n.trimestre=? AND (n.seq1 IS NOT NULL OR n.seq2 IS NOT NULL)", (cid, int(trim)))
            remplies = cur.fetchone()[0]
            attendues = eff * nmat
            pct = round(remplies/attendues*100) if attendues else 0
            infos_classes.append((cnom, eff, nmat, remplies, attendues, pct))
        conn.close()

        ctk.CTkLabel(self.main_frame, text="Tableau de Bord", font=ctk.CTkFont(size=22, weight="bold"), text_color=VERT_FONCE).pack(anchor="w", padx=20, pady=(15, 5))

        top = ctk.CTkFrame(self.main_frame, fg_color=BLANC); top.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(top, text=str(params.get('etablissement_nom','')) + "  |  Annee : " + str(params.get('annee_scolaire','')), font=ctk.CTkFont(weight="bold"), text_color=VERT_FONCE).pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(top, text="Trimestre :").pack(side="right", padx=(5,0), pady=8)
        self.combo_dash_trim = ctk.CTkOptionMenu(top, values=["1","2","3"], width=70, command=self._on_dash_trim_change, fg_color=VERT, button_color=VERT_FONCE)
        self.combo_dash_trim.set(trim)
        self.combo_dash_trim.pack(side="right", padx=10, pady=8)

        cards = ctk.CTkFrame(self.main_frame, fg_color="transparent"); cards.pack(fill="x", padx=20, pady=5)
        card_data = [
            ("Classes", nb_classes, VERT_FONCE),
            ("Eleves", nb_eleves, VERT),
            ("Matieres", nb_mat, KAKI_FONCE),
            ("Notes saisies T"+str(trim), nb_notes, VERT_FONCE),
        ]
        for i, (titre, val, couleur) in enumerate(card_data):
            c = ctk.CTkFrame(cards, fg_color=BLANC); c.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
            cards.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(c, text=titre, font=ctk.CTkFont(size=12), text_color=VERT_FONCE).pack(padx=10, pady=(10,0))
            ctk.CTkLabel(c, text=str(val), font=ctk.CTkFont(size=26, weight="bold"), text_color=couleur).pack(padx=10, pady=(0,10))

        ctk.CTkLabel(self.main_frame, text="Etat de saisie par classe - Trimestre " + str(trim), font=ctk.CTkFont(size=15, weight="bold"), text_color=VERT_FONCE).pack(anchor="w", padx=20, pady=(10,5))
        frame_list = ctk.CTkScrollableFrame(self.main_frame, height=320, fg_color=BLANC)
        frame_list.pack(fill="both", expand=True, padx=20, pady=5)

        if not infos_classes:
            ctk.CTkLabel(frame_list, text="Aucune classe creee pour l'instant. Va dans Classes pour commencer.", text_color="gray").pack(pady=20)
        else:
            ctk.CTkLabel(frame_list, text="Classe", font=ctk.CTkFont(weight="bold"), width=200, anchor="w").grid(row=0, column=0, padx=5, pady=4)
            ctk.CTkLabel(frame_list, text="Eleves", font=ctk.CTkFont(weight="bold"), width=70).grid(row=0, column=1, padx=5, pady=4)
            ctk.CTkLabel(frame_list, text="Matieres", font=ctk.CTkFont(weight="bold"), width=70).grid(row=0, column=2, padx=5, pady=4)
            ctk.CTkLabel(frame_list, text="Progression saisie", font=ctk.CTkFont(weight="bold"), width=260).grid(row=0, column=3, padx=5, pady=4)
            ctk.CTkLabel(frame_list, text="% / Detail", font=ctk.CTkFont(weight="bold"), width=150).grid(row=0, column=4, padx=5, pady=4)

            for idx, (cnom, eff, nmat, remplies, attendues, pct) in enumerate(infos_classes, start=1):
                ctk.CTkLabel(frame_list, text=cnom, width=200, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=idx, column=0, padx=5, pady=4, sticky="w")
                ctk.CTkLabel(frame_list, text=str(eff), width=70).grid(row=idx, column=1, padx=5, pady=4)
                ctk.CTkLabel(frame_list, text=str(nmat), width=70).grid(row=idx, column=2, padx=5, pady=4)
                bar = ctk.CTkProgressBar(frame_list, width=250, progress_color=VERT, fg_color="#E9E2C8")
                bar.set(pct/100)
                bar.grid(row=idx, column=3, padx=5, pady=4)
                coul = VERT if pct==100 else ("#B7791F" if pct>=50 else ROUGE)
                ctk.CTkLabel(frame_list, text=str(pct)+"%  ("+str(remplies)+"/"+str(attendues)+")", width=150, text_color=coul, font=ctk.CTkFont(weight="bold")).grid(row=idx, column=4, padx=5, pady=4)
                if eff==0 or nmat==0:
                    ctk.CTkLabel(frame_list, text="classe incomplete", text_color=ROUGE, width=150).grid(row=idx, column=5, padx=5, pady=4)

        bottom = ctk.CTkFrame(self.main_frame, fg_color="transparent"); bottom.pack(fill="x", padx=20, pady=8)
        ctk.CTkButton(bottom, text="Gerer les Eleves", command=self.show_eleves_frame, fg_color=VERT, hover_color=VERT_HOVER).pack(side="left", padx=5)
        ctk.CTkButton(bottom, text="Saisir / Voir les Notes", command=self.show_notes_frame, fg_color=VERT_FONCE, hover_color=VERT_HOVER).pack(side="left", padx=5)
        ctk.CTkButton(bottom, text="Generer les Bulletins", command=self.show_pdf_frame, fg_color=KAKI_FONCE, hover_color=VERT_FONCE, text_color=BLANC).pack(side="left", padx=5)

    # ==========================================
    # 1. CLASSES
    # ==========================================
    def show_classes_frame(self):
        self.clear_main_frame()
        ctk.CTkLabel(self.main_frame, text="Gestion des Classes", font=ctk.CTkFont(size=22, weight="bold"), text_color=VERT_FONCE).pack(anchor="w", padx=20, pady=(15, 5))
        form_frame = ctk.CTkFrame(self.main_frame, fg_color=BLANC); form_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(form_frame, text="Nom de la classe :").grid(row=0, column=0, padx=10, pady=10)
        self.entry_nom_classe = ctk.CTkEntry(form_frame, placeholder_text="Ex: Premiere 1A4 ESP")
        self.entry_nom_classe.grid(row=0, column=1, padx=10, pady=10)
        ctk.CTkLabel(form_frame, text="Prof. Principal :").grid(row=0, column=2, padx=10, pady=10)
        self.entry_prof_princ = ctk.CTkEntry(form_frame, placeholder_text="Ex: Mme TOUOMGUEM")
        self.entry_prof_princ.grid(row=0, column=3, padx=10, pady=10)
        ctk.CTkButton(form_frame, text="+ Ajouter Classe", command=self.ajouter_classe, fg_color=VERT, hover_color=VERT_HOVER).grid(row=0, column=4, padx=10, pady=10)
        tree_frame = ctk.CTkFrame(self.main_frame, fg_color=BLANC); tree_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.tree_classes = ttk.Treeview(tree_frame, columns=("id", "nom", "prof"), show="headings")
        self.tree_classes.heading("id", text="ID"); self.tree_classes.heading("nom", text="Classe"); self.tree_classes.heading("prof", text="Prof Principal")
        self.tree_classes.pack(fill="both", expand=True)
        self.charger_classes()

    def ajouter_classe(self):
        nom, prof = self.entry_nom_classe.get().strip(), self.entry_prof_princ.get().strip()
        if nom:
            conn = get_connection(); cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO classes (nom, prof_principal) VALUES (?, ?)", (nom, prof))
                conn.commit()
                self.charger_classes()
            except Exception as e: messagebox.showerror("Erreur", str(e))
            finally: conn.close()

    def charger_classes(self):
        for item in self.tree_classes.get_children(): self.tree_classes.delete(item)
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id, nom, prof_principal FROM classes ORDER BY nom")
        for r in cursor.fetchall(): self.tree_classes.insert("", "end", values=r)
        conn.close()

    # ==========================================
    # 2. ELEVES
    # ==========================================
    def show_eleves_frame(self):
        self.clear_main_frame()
        classes_dict = self.get_classes_dict()
        if not classes_dict:
            ctk.CTkLabel(self.main_frame, text="Veuillez creer au moins une classe.", font=ctk.CTkFont(size=16, weight="bold")).pack(expand=True)
            return
        ctk.CTkLabel(self.main_frame, text="Gestion des Eleves", font=ctk.CTkFont(size=22, weight="bold"), text_color=VERT_FONCE).pack(anchor="w", padx=20, pady=(15, 5))
        top = ctk.CTkFrame(self.main_frame, fg_color=BLANC); top.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(top, text="Classe :", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(10, 5))
        self.combo_classe_el = ctk.CTkOptionMenu(top, values=list(classes_dict.keys()), command=lambda _: self.charger_eleves(), fg_color=VERT, button_color=VERT_FONCE)
        self.combo_classe_el.pack(side="left", padx=5, pady=8)
        ctk.CTkButton(top, text="Importer Excel / CSV", command=lambda: self.importer_liste_eleves("excel"), fg_color=VERT, hover_color=VERT_HOVER, font=ctk.CTkFont(weight="bold")).pack(side="right", padx=5, pady=8)
        ctk.CTkButton(top, text="Importer Word", command=lambda: self.importer_liste_eleves("word"), fg_color=KAKI_FONCE, hover_color=VERT_FONCE, font=ctk.CTkFont(weight="bold")).pack(side="right", padx=5, pady=8)
        form = ctk.CTkFrame(self.main_frame, fg_color=BLANC); form.pack(fill="x", padx=20, pady=5)
        self.ent_mat = ctk.CTkEntry(form, width=120, placeholder_text="Matricule")
        self.ent_mat.grid(row=0, column=0, padx=5, pady=5)
        self.ent_nom = ctk.CTkEntry(form, width=160, placeholder_text="Nom")
        self.ent_nom.grid(row=0, column=1, padx=5, pady=5)
        self.ent_prenom = ctk.CTkEntry(form, width=160, placeholder_text="Prenom")
        self.ent_prenom.grid(row=0, column=2, padx=5, pady=5)
        self.combo_sexe = ctk.CTkOptionMenu(form, values=["F", "M"], width=70)
        self.combo_sexe.grid(row=0, column=3, padx=5, pady=5)
        self.ent_date = ctk.CTkEntry(form, width=120, placeholder_text="Date naiss. (JJ/MM/AAAA)")
        self.ent_date.grid(row=1, column=0, padx=5, pady=5)
        self.ent_lieu = ctk.CTkEntry(form, width=160, placeholder_text="Lieu de naissance")
        self.ent_lieu.grid(row=1, column=1, padx=5, pady=5)
        self.var_redoublant = ctk.CTkCheckBox(form, text="Redoublant")
        self.var_redoublant.grid(row=1, column=2, padx=5, pady=5)
        ctk.CTkButton(form, text="+ Ajouter Eleve", command=self.ajouter_eleve, fg_color=VERT, hover_color=VERT_HOVER, font=ctk.CTkFont(weight="bold")).grid(row=1, column=3, columnspan=2, padx=10, pady=5, sticky="ew")
        tree_frame = ctk.CTkFrame(self.main_frame, fg_color=BLANC); tree_frame.pack(fill="both", expand=True, padx=20, pady=10)
        cols = ("id", "matricule", "nom", "prenom", "sexe", "date_naiss", "lieu_naiss", "red")
        self.tree_eleves = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12)
        headers = {"id": "ID", "matricule": "Matricule", "nom": "Nom", "prenom": "Prenom", "sexe": "Sexe", "date_naiss": "Date Naiss.", "lieu_naiss": "Lieu Naiss.", "red": "Red."}
        widths = {"id": 40, "matricule": 100, "nom": 150, "prenom": 150, "sexe": 50, "date_naiss": 100, "lieu_naiss": 120, "red": 50}
        for c in cols:
            self.tree_eleves.heading(c, text=headers[c])
            self.tree_eleves.column(c, width=widths[c], anchor="center" if c in ("id", "sexe", "red") else "w")
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_eleves.yview)
        self.tree_eleves.configure(yscroll=scroll.set)
        self.tree_eleves.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        ctk.CTkButton(self.main_frame, text="Supprimer Eleve Selectionne", command=self.supprimer_eleve, fg_color=ROUGE, hover_color=ROUGE_HOVER).pack(anchor="e", padx=20, pady=5)
        self.charger_eleves()

    def ajouter_eleve(self):
        c_id = self.get_classes_dict().get(self.combo_classe_el.get())
        m, n, p, s = self.ent_mat.get().strip(), self.ent_nom.get().strip(), self.ent_prenom.get().strip(), self.combo_sexe.get()
        d, l = self.ent_date.get().strip(), self.ent_lieu.get().strip()
        red = 1 if self.var_redoublant.get() else 0
        if m and n:
            conn = get_connection(); cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO eleves (matricule, nom, prenom, sexe, date_naissance, lieu_naissance, redoublant, classe_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (m, n.upper(), p.title(), s, d, l, red, c_id))
                conn.commit()
                self.ent_mat.delete(0, "end"); self.ent_nom.delete(0, "end"); self.ent_prenom.delete(0, "end")
                self.charger_eleves()
            except Exception as e: messagebox.showerror("Erreur", str(e))
            finally: conn.close()

    def charger_eleves(self, classe_id_force=None):
        for item in self.tree_eleves.get_children():
            self.tree_eleves.delete(item)
        classes_dict = self.get_classes_dict()
        if classe_id_force: c_id = classe_id_force
        else: c_id = classes_dict.get(self.combo_classe_el.get())
        if not c_id: return
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id, matricule, nom, prenom, sexe, date_naissance, lieu_naissance, redoublant FROM eleves WHERE classe_id = ? ORDER BY nom, prenom", (c_id,))
        for r in cursor.fetchall():
            self.tree_eleves.insert("", "end", values=(r[0], r[1], r[2], r[3], r[4], r[5] or "", r[6] or "", "Oui" if r[7] else "Non"))
        conn.close()

    def supprimer_eleve(self):
        selected = self.tree_eleves.selection()
        if not selected: return
        el_id = self.tree_eleves.item(selected[0])['values'][0]
        if messagebox.askyesno("Confirmation", "Supprimer cet eleve ?"):
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("DELETE FROM eleves WHERE id = ?", (el_id,))
            conn.commit(); conn.close()
            self.charger_eleves()

    def attribuer_photo_eleve(self):
        selected = self.tree_eleves.selection()
        if not selected:
            messagebox.showwarning("Attention", "Selectionne d'abord un eleve dans le tableau.")
            return
        el_id = self.tree_eleves.item(selected[0])['values'][0]
        el_mat = str(self.tree_eleves.item(selected[0])['values'][1])
        chemin = filedialog.askopenfilename(title="Choisir la photo", filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if not chemin:
            return
        import shutil
        photos_dir = os.path.join(BASE_DIR, "assets", "photos")
        os.makedirs(photos_dir, exist_ok=True)
        propre_mat = "".join(c for c in el_mat if c.isalnum() or c in "-_")
        ext = os.path.splitext(chemin)[1].lower() or ".jpg"
        dest = os.path.join(photos_dir, propre_mat + ext)
        shutil.copy(chemin, dest)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("UPDATE eleves SET photo = ? WHERE id = ?", (os.path.basename(dest), el_id))
        conn.commit(); conn.close()
        messagebox.showinfo("Succes", "Photo enregistree pour " + el_mat)
        self.charger_eleves()

        ctk.CTkButton(top, text="Attribuer photo", command=self.attribuer_photo_eleve, fg_color=VERT, hover_color=VERT_HOVER).pack(side="right", padx=5, pady=8)
        ctk.CTkButton(top, text="Dossier photos", command=self.importer_dossier_photos, fg_color=KAKI_FONCE, hover_color=VERT_FONCE).pack(side="right", padx=5, pady=8)

    def importer_dossier_photos(self):
        import shutil
        dossier = filedialog.askdirectory(title="Choisir le dossier contenant les photos")
        if not dossier:
            return
        photos_dir = os.path.join(BASE_DIR, "assets", "photos")
        os.makedirs(photos_dir, exist_ok=True)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT id, matricule FROM eleves")
        map_mat = {"".join(c for c in str(r[1]) if c.isalnum() or c in "-_").lower(): r[0] for r in cur.fetchall()}
        ok = 0
        inconnus = []
        for f in os.listdir(dossier):
            if not f.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            base = os.path.splitext(f)[0]
            cle = "".join(c for c in base if c.isalnum() or c in "-_").lower()
            if cle in map_mat:
                shutil.copy(os.path.join(dossier, f), os.path.join(photos_dir, f))
                cur.execute("UPDATE eleves SET photo = ? WHERE id = ?", (f, map_mat[cle]))
                ok += 1
            else:
                inconnus.append(f)
        conn.commit(); conn.close()
        msg = str(ok) + " photo(s) associee(s)."
        if inconnus:
            msg += "\nFichiers non reconnus :\n" + "\n".join(inconnus[:20])
        messagebox.showinfo("Import photos", msg)
        self.charger_eleves()        

    def importer_liste_eleves(self, type_fichier="excel"):
        classes_dict = self.get_classes_dict()
        classe_id = classes_dict.get(self.combo_classe_el.get())
        nom_classe = self.combo_classe_el.get()
        if not classe_id: return
        if type_fichier == "excel":
            chemin = filedialog.askopenfilename(title="Importer (Excel / CSV)", filetypes=[("Excel / CSV", "*.xlsx *.xls *.csv")])
        else:
            chemin = filedialog.askopenfilename(title="Importer (Word)", filetypes=[("Word", "*.docx")])
        if not chemin: return
        try:
            if type_fichier == "excel": eleves, mapping, erreurs, apercu = lire_fichier_excel(chemin)
            else: eleves, mapping, erreurs, apercu = lire_fichier_word(chemin)
        except Exception as e:
            messagebox.showerror("Erreur", str(e)); return
        if not eleves:
            messagebox.showwarning("Aucun eleve", "Aucun eleve valide trouve.")
            return
        self._afficher_apercu_import(classe_id, nom_classe, eleves, mapping, erreurs)

    def _afficher_apercu_import(self, classe_id, nom_classe, eleves, mapping, erreurs):
        win = ctk.CTkToplevel(self)
        win.title("Apercu de l'importation")
        win.geometry("820x580")
        win.transient(self); win.grab_set()
        ctk.CTkLabel(win, text="Importation dans la classe : " + str(nom_classe), font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(win, text=str(len(eleves)) + " eleve(s) detecte(s)").pack(anchor="w", padx=15, pady=2)
        btns = ctk.CTkFrame(win, fg_color="transparent"); btns.pack(side="bottom", fill="x", padx=15, pady=10)
        var_ecraser = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(win, text="Mettre a jour les eleves existants", variable=var_ecraser).pack(side="bottom", anchor="w", padx=15, pady=5)
        def confirmer():
            conn = get_connection()
            try: aj, ig, maj, _ = importer_eleves_dans_bdd(conn, classe_id, eleves, ecraser_existants=var_ecraser.get())
            finally: conn.close()
            win.destroy()
            self.charger_eleves(classe_id_force=classe_id)
            messagebox.showinfo("Importation terminee", str(aj) + " ajoute(s), " + str(maj) + " mis a jour.")
        ctk.CTkButton(btns, text="Annuler", command=win.destroy, fg_color=KAKI, hover_color=KAKI_FONCE, text_color="#000000").pack(side="right", padx=5)
        ctk.CTkButton(btns, text="Valider et Importer " + str(len(eleves)) + " eleve(s)", command=confirmer, fg_color=VERT, hover_color=VERT_HOVER, font=ctk.CTkFont(size=14, weight="bold"), height=38).pack(side="right", padx=5)
        frame = ctk.CTkFrame(win); frame.pack(fill="both", expand=True, padx=15, pady=5)
        cols = ("matricule", "nom", "prenom", "sexe", "date", "lieu", "red")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=8)
        for c, h in zip(cols, ["Matricule", "Nom", "Prenom", "Sexe", "Date Naiss.", "Lieu", "Red."]):
            tree.heading(c, text=h); tree.column(c, width=100)
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview); tree.configure(yscroll=sb.set); sb.pack(side="right", fill="y")
        for el in eleves:
            tree.insert("", "end", values=(el["matricule"], el["nom"], el["prenom"], el["sexe"], el["date_naissance"], el["lieu_naissance"], "Oui" if el["redoublant"] else "Non"))

    # ==========================================
    # 3. MATIERES
    # ==========================================
    def show_matieres_frame(self):
        self.clear_main_frame()
        classes_dict = self.get_classes_dict()
        if not classes_dict:
            ctk.CTkLabel(self.main_frame, text="Creez d'abord une classe.", font=ctk.CTkFont(size=16, weight="bold")).pack(expand=True)
            return
        ctk.CTkLabel(self.main_frame, text="Matieres & Coefficients", font=ctk.CTkFont(size=22, weight="bold"), text_color=VERT_FONCE).pack(anchor="w", padx=20, pady=(15, 5))
        top = ctk.CTkFrame(self.main_frame, fg_color=BLANC); top.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(top, text="Classe :", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(10, 5))
        self.combo_classe_mat = ctk.CTkOptionMenu(top, values=list(classes_dict.keys()), command=lambda _: self.charger_matieres(), fg_color=VERT, button_color=VERT_FONCE)
        self.combo_classe_mat.pack(side="left", padx=5, pady=8)
        ctk.CTkButton(top, text="Importer Excel / CSV", command=lambda: self.importer_liste_matieres("excel"), fg_color=VERT, hover_color=VERT_HOVER, font=ctk.CTkFont(weight="bold")).pack(side="right", padx=5, pady=8)
        ctk.CTkButton(top, text="Importer Word", command=lambda: self.importer_liste_matieres("word"), fg_color=KAKI_FONCE, hover_color=VERT_FONCE, font=ctk.CTkFont(weight="bold")).pack(side="right", padx=5, pady=8)
        form = ctk.CTkFrame(self.main_frame, fg_color=BLANC); form.pack(fill="x", padx=20, pady=5)
        self.ent_mat_nom = ctk.CTkEntry(form, width=180, placeholder_text="Matiere")
        self.ent_mat_nom.grid(row=0, column=0, padx=5, pady=5)
        self.combo_grp = ctk.CTkOptionMenu(form, values=["1er GROUPE", "2eme GROUPE", "3eme GROUPE"], width=130)
        self.combo_grp.grid(row=0, column=1, padx=5, pady=5)
        self.ent_coef = ctk.CTkEntry(form, width=70, placeholder_text="Coef")
        self.ent_coef.grid(row=0, column=2, padx=5, pady=5)
        self.ent_prof = ctk.CTkEntry(form, width=180, placeholder_text="Professeur")
        self.ent_prof.grid(row=0, column=3, padx=5, pady=5)
        ctk.CTkButton(form, text="+ Ajouter", command=self.ajouter_matiere, fg_color=VERT, hover_color=VERT_HOVER).grid(row=0, column=4, padx=10, pady=5)
        tree_frame = ctk.CTkFrame(self.main_frame, fg_color=BLANC); tree_frame.pack(fill="both", expand=True, padx=20, pady=10)
        cols = ("id", "nom", "groupe", "coef", "prof", "ordre")
        self.tree_matieres = ttk.Treeview(tree_frame, columns=cols, show="headings", height=14)
        headers = {"id": "ID", "nom": "Matiere", "groupe": "Groupe", "coef": "Coef", "prof": "Enseignant", "ordre": "Ordre"}
        widths = {"id": 40, "nom": 200, "groupe": 100, "coef": 60, "prof": 180, "ordre": 60}
        for c in cols:
            self.tree_matieres.heading(c, text=headers[c])
            self.tree_matieres.column(c, width=widths[c], anchor="center" if c in ("id", "groupe", "coef", "ordre") else "w")
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_matieres.yview)
        self.tree_matieres.configure(yscroll=scroll.set)
        self.tree_matieres.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        ctk.CTkButton(self.main_frame, text="Supprimer la matiere selectionnee", command=self.supprimer_matiere, fg_color=ROUGE, hover_color=ROUGE_HOVER).pack(anchor="e", padx=20, pady=5)
        self.charger_matieres()

    def ajouter_matiere(self):
        c_id = self.get_classes_dict().get(self.combo_classe_mat.get())
        n, g_str, coef_str, p = self.ent_mat_nom.get().strip(), self.combo_grp.get(), self.ent_coef.get().strip(), self.ent_prof.get().strip()
        if "1er" in g_str:
            g = 1
        elif "2eme" in g_str:
            g = 2
        else:
            g = 3
        if not n or not coef_str:
            messagebox.showwarning("Attention", "Matiere et coefficient obligatoires.")
            return
        try: coef = float(coef_str.replace(",", "."))
        except ValueError: messagebox.showerror("Erreur", "Le coef doit etre un nombre."); return
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(ordre), 0) + 1 FROM matieres WHERE classe_id = ?", (c_id,))
        ordre = cursor.fetchone()[0]
        cursor.execute("INSERT INTO matieres (nom, groupe, coefficient, enseignant, ordre, classe_id) VALUES (?, ?, ?, ?, ?, ?)", (n, g, coef, p, ordre, c_id))
        conn.commit(); conn.close()
        self.ent_mat_nom.delete(0, "end"); self.ent_coef.delete(0, "end"); self.ent_prof.delete(0, "end")
        self.charger_matieres()

    def charger_matieres(self):
        for item in self.tree_matieres.get_children(): self.tree_matieres.delete(item)
        c_id = self.get_classes_dict().get(self.combo_classe_mat.get())
        if not c_id: return
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id, nom, groupe, coefficient, enseignant, ordre FROM matieres WHERE classe_id = ? ORDER BY groupe, ordre, id", (c_id,))
        for r in cursor.fetchall():
            grp_label = "1er GROUPE" if r[2] == 1 else str(r[2]) + "eme GROUPE"
            self.tree_matieres.insert("", "end", values=(r[0], r[1], grp_label, r[3], r[4] or "", r[5]))
        conn.close()

    def supprimer_matiere(self):
        selected = self.tree_matieres.selection()
        if not selected: return
        mat_id = self.tree_matieres.item(selected[0])["values"][0]
        if messagebox.askyesno("Confirmation", "Supprimer cette matiere ?"):
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("DELETE FROM matieres WHERE id = ?", (mat_id,))
            conn.commit(); conn.close()
            self.charger_matieres()

    def importer_liste_matieres(self, type_fichier="excel"):
        classes_dict = self.get_classes_dict()
        nom_classe = self.combo_classe_mat.get()
        classe_id = classes_dict.get(nom_classe)
        if not classe_id: return
        if type_fichier == "excel":
            chemin = filedialog.askopenfilename(title="Importer matieres (Excel)", filetypes=[("Excel", "*.xlsx *.xls *.csv")])
        else:
            chemin = filedialog.askopenfilename(title="Importer matieres (Word)", filetypes=[("Word", "*.docx")])
        if not chemin: return
        try:
            if type_fichier == "excel": matieres, mapping, erreurs, _ = lire_matieres_excel(chemin)
            else: matieres, mapping, erreurs, _ = lire_matieres_word(chemin)
        except Exception as e:
            messagebox.showerror("Erreur", str(e)); return
        if not matieres: return
        self._afficher_apercu_import_matieres(classe_id, nom_classe, matieres, mapping, erreurs)

    def _afficher_apercu_import_matieres(self, classe_id, nom_classe, matieres, mapping, erreurs):
        win = ctk.CTkToplevel(self)
        win.title("Apercu import matieres")
        win.geometry("780x520")
        win.transient(self); win.grab_set()
        ctk.CTkLabel(win, text="Importation des matieres - classe : " + str(nom_classe), font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(win, text=str(len(matieres)) + " matiere(s) detectee(s)").pack(anchor="w", padx=15, pady=2)
        btns = ctk.CTkFrame(win, fg_color="transparent"); btns.pack(side="bottom", fill="x", padx=15, pady=10)
        var_ecraser = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(win, text="Mettre a jour les matieres existantes", variable=var_ecraser).pack(side="bottom", anchor="w", padx=15, pady=5)
        def confirmer():
            conn = get_connection()
            try: aj, ig, maj = importer_matieres_dans_bdd(conn, classe_id, matieres, ecraser_existants=var_ecraser.get())
            finally: conn.close()
            win.destroy()
            self.charger_matieres()
            messagebox.showinfo("Importation terminee", str(aj) + " ajoutee(s), " + str(maj) + " mise(s) a jour.")
        ctk.CTkButton(btns, text="Annuler", command=win.destroy, fg_color=KAKI, hover_color=KAKI_FONCE, text_color="#000000").pack(side="right", padx=5)
        ctk.CTkButton(btns, text="Valider et Importer " + str(len(matieres)) + " matiere(s)", command=confirmer, fg_color=VERT, hover_color=VERT_HOVER, font=ctk.CTkFont(size=14, weight="bold"), height=38).pack(side="right", padx=5)
        frame = ctk.CTkFrame(win); frame.pack(fill="both", expand=True, padx=15, pady=5)
        cols = ("nom", "groupe", "coef", "prof", "ordre")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=10)
        for c, h in zip(cols, ["Matiere", "Groupe", "Coef", "Enseignant", "Ordre"]): tree.heading(c, text=h); tree.column(c, width=100)
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview); tree.configure(yscroll=sb.set); sb.pack(side="right", fill="y")
        for m in matieres: tree.insert("", "end", values=(m["nom"], m["groupe"], m["coefficient"], m["enseignant"], m["ordre"]))

    # ==========================================
    # 4. NOTES
    # ==========================================
    def show_notes_frame(self):
        self.clear_main_frame()
        classes_dict = self.get_classes_dict()
        if not classes_dict:
            ctk.CTkLabel(self.main_frame, text="Creez d'abord une classe.", font=ctk.CTkFont(size=16, weight="bold")).pack(expand=True)
            return
        ctk.CTkLabel(self.main_frame, text="Notes - Saisie & Consultation", font=ctk.CTkFont(size=22, weight="bold"), text_color=VERT_FONCE).pack(anchor="w", padx=20, pady=(15, 5))
        top = ctk.CTkFrame(self.main_frame, fg_color=BLANC); top.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(top, text="Classe :").pack(side="left", padx=5)
        self.combo_classe_notes = ctk.CTkOptionMenu(top, values=list(classes_dict.keys()), command=lambda _: self.charger_combo_matieres_notes(), fg_color=VERT, button_color=VERT_FONCE)
        self.combo_classe_notes.pack(side="left", padx=5)
        ctk.CTkLabel(top, text="Trimestre :").pack(side="left", padx=5)
        self.combo_trim_notes = ctk.CTkOptionMenu(top, values=["1", "2", "3"], width=60)
        self.combo_trim_notes.pack(side="left", padx=5)
        ctk.CTkLabel(top, text="Matiere :").pack(side="left", padx=5)
        self.combo_matiere_notes = ctk.CTkOptionMenu(top, values=["- Choisir une classe -"], width=200)
        self.combo_matiere_notes.pack(side="left", padx=5)
        ctk.CTkButton(top, text="Voir / Modifier cette matiere", command=self.charger_grille_notes, fg_color=VERT, hover_color=VERT_HOVER, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
        ctk.CTkButton(top, text="Releve complet (toutes matieres)", command=self.afficher_releve_complet, fg_color=KAKI_FONCE, hover_color=VERT_FONCE, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        self.lbl_notes_info = ctk.CTkLabel(self.main_frame, text="Choisissez une classe, un trimestre, puis soit une matiere (saisie), soit le releve complet.", text_color="gray")
        self.lbl_notes_info.pack(anchor="w", padx=25, pady=(0, 5))
        self.frame_grille = ctk.CTkScrollableFrame(self.main_frame, height=380, fg_color=BLANC)
        self.frame_grille.pack(fill="both", expand=True, padx=20, pady=5)
        self.bottom_notes = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.bottom_notes.pack(fill="x", padx=20, pady=8)
        self.btn_save_notes = ctk.CTkButton(self.bottom_notes, text="Enregistrer les notes de cette matiere", command=self.enregistrer_notes, fg_color=VERT, hover_color=VERT_HOVER, font=ctk.CTkFont(weight="bold"), height=36)
        self.entries_notes = {}
        self.mode_notes = None
        self.charger_combo_matieres_notes()

    def charger_combo_matieres_notes(self):
        c_id = self.get_classes_dict().get(self.combo_classe_notes.get())
        if not c_id: return
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id, nom FROM matieres WHERE classe_id = ? ORDER BY groupe, ordre, nom", (c_id,))
        mats = cursor.fetchall(); conn.close()
        self.dict_matieres_notes = {m[1]: m[0] for m in mats}
        if mats:
            self.combo_matiere_notes.configure(values=list(self.dict_matieres_notes.keys()))
            self.combo_matiere_notes.set(mats[0][1])
        else:
            self.combo_matiere_notes.configure(values=["(aucune matiere)"])
            self.combo_matiere_notes.set("(aucune matiere)")

    def _clear_grille_notes(self):
        for w in self.frame_grille.winfo_children(): w.destroy()
        self.entries_notes = {}
        for w in self.bottom_notes.winfo_children(): w.pack_forget()

    def charger_grille_notes(self):
        self._clear_grille_notes()
        self.mode_notes = "matiere"
        c_id = self.get_classes_dict().get(self.combo_classe_notes.get())
        mat_nom = self.combo_matiere_notes.get()
        mat_id = self.dict_matieres_notes.get(mat_nom)
        trim = int(self.combo_trim_notes.get())
        if not c_id or not mat_id:
            self.lbl_notes_info.configure(text="Classe ou matiere invalide.")
            return
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id, matricule, nom, prenom FROM eleves WHERE classe_id = ? ORDER BY nom, prenom", (c_id,))
        eleves = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM notes n JOIN eleves e ON e.id = n.eleve_id WHERE e.classe_id = ? AND n.matiere_id = ? AND n.trimestre = ? AND (n.seq1 IS NOT NULL OR n.seq2 IS NOT NULL)", (c_id, mat_id, trim))
        nb_remplies = cursor.fetchone()[0]
        self.lbl_notes_info.configure(text="Matiere : " + str(mat_nom) + "  |  Trimestre " + str(trim) + "  |  " + str(nb_remplies) + "/" + str(len(eleves)) + " eleve(s) ont deja des notes.")
        ctk.CTkLabel(self.frame_grille, text="N", font=ctk.CTkFont(weight="bold"), width=40).grid(row=0, column=0, padx=4, pady=4)
        ctk.CTkLabel(self.frame_grille, text="Matricule", font=ctk.CTkFont(weight="bold"), width=110).grid(row=0, column=1, padx=4, pady=4)
        ctk.CTkLabel(self.frame_grille, text="Eleve", font=ctk.CTkFont(weight="bold"), width=260, anchor="w").grid(row=0, column=2, padx=4, pady=4)
        ctk.CTkLabel(self.frame_grille, text="SEQ 1 (/20)", font=ctk.CTkFont(weight="bold"), width=100).grid(row=0, column=3, padx=4, pady=4)
        ctk.CTkLabel(self.frame_grille, text="SEQ 2 (/20)", font=ctk.CTkFont(weight="bold"), width=100).grid(row=0, column=4, padx=4, pady=4)
        ctk.CTkLabel(self.frame_grille, text="Moyenne", font=ctk.CTkFont(weight="bold"), width=80).grid(row=0, column=5, padx=4, pady=4)
        ctk.CTkLabel(self.frame_grille, text="Source", font=ctk.CTkFont(weight="bold"), width=90).grid(row=0, column=6, padx=4, pady=4)
        self.entries_notes = {}
        for idx, el in enumerate(eleves, start=1):
            el_id, mat, nom, prenom = el
            cursor.execute("SELECT seq1, seq2 FROM notes WHERE eleve_id=? AND matiere_id=? AND trimestre=?", (el_id, mat_id, trim))
            n = cursor.fetchone()
            s1 = n[0] if n else None
            s2 = n[1] if n else None
            s1_val = "" if s1 is None else str(s1)
            s2_val = "" if s2 is None else str(s2)
            if s1 is not None and s2 is not None: moy = "{:.2f}".format((s1 + s2) / 2)
            elif s1 is not None: moy = "{:.2f}".format(s1)
            elif s2 is not None: moy = "{:.2f}".format(s2)
            else: moy = "-"
            a_des_notes = s1 is not None or s2 is not None
            source = "Importee" if a_des_notes else "-"
            couleur = VERT if a_des_notes else "gray"
            ctk.CTkLabel(self.frame_grille, text=str(idx), width=40).grid(row=idx, column=0, padx=4, pady=3)
            ctk.CTkLabel(self.frame_grille, text=mat, width=110).grid(row=idx, column=1, padx=4, pady=3)
            ctk.CTkLabel(self.frame_grille, text=nom + " " + prenom, width=260, anchor="w").grid(row=idx, column=2, padx=4, pady=3)
            e1 = ctk.CTkEntry(self.frame_grille, width=90, placeholder_text="0-20"); e1.insert(0, s1_val); e1.grid(row=idx, column=3, padx=4, pady=3)
            e2 = ctk.CTkEntry(self.frame_grille, width=90, placeholder_text="0-20"); e2.insert(0, s2_val); e2.grid(row=idx, column=4, padx=4, pady=3)
            ctk.CTkLabel(self.frame_grille, text=moy, width=80, font=ctk.CTkFont(weight="bold")).grid(row=idx, column=5, padx=4, pady=3)
            ctk.CTkLabel(self.frame_grille, text=source, width=90, text_color=couleur).grid(row=idx, column=6, padx=4, pady=3)
            self.entries_notes[el_id] = (e1, e2)
        conn.close()
        self.btn_save_notes.pack(side="right", padx=5)

    def afficher_releve_complet(self):
        self._clear_grille_notes()
        self.mode_notes = "releve"
        c_id = self.get_classes_dict().get(self.combo_classe_notes.get())
        trim = int(self.combo_trim_notes.get())
        nom_classe = self.combo_classe_notes.get()
        if not c_id: return
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id, nom, coefficient FROM matieres WHERE classe_id=? ORDER BY groupe, ordre, nom", (c_id,))
        matieres = cursor.fetchall()
        if not matieres:
            self.lbl_notes_info.configure(text="Aucune matiere enregistree pour cette classe.")
            conn.close(); return
        cursor.execute("SELECT id, matricule, nom, prenom FROM eleves WHERE classe_id=? ORDER BY nom, prenom", (c_id,))
        eleves = cursor.fetchall()
        cursor.execute("SELECT eleve_id, matiere_id, seq1, seq2 FROM notes WHERE trimestre = ? AND eleve_id IN (SELECT id FROM eleves WHERE classe_id = ?)", (trim, c_id))
        notes_map = {(el_id, mat_id): (s1, s2) for el_id, mat_id, s1, s2 in cursor.fetchall()}
        conn.close()
        nb_cells = sum(1 for v in notes_map.values() if v[0] is not None or v[1] is not None)
        self.lbl_notes_info.configure(text="Proces-Verbal (PV) - Classe : " + str(nom_classe) + " | Trimestre " + str(trim) + " | " + str(len(eleves)) + " eleve(s) x " + str(len(matieres)) + " matiere(s) | " + str(nb_cells) + " note(s) saisie(s)", text_color=VERT_FONCE)
        btn_exp_excel = ctk.CTkButton(self.bottom_notes, text="Exporter ce Releve (PV) sous Excel", command=lambda: self.exporter_pv_excel(nom_classe, trim, eleves, matieres, notes_map), fg_color=VERT, hover_color=VERT_HOVER, font=ctk.CTkFont(weight="bold"))
        btn_exp_excel.pack(side="right", padx=10)

        cols = ["matricule", "nom"]
        headers = {"matricule": "Matricule", "nom": "Nom & Prenom de l'Eleve"}
        largeurs = {"matricule": 110, "nom": 230}
        for m in matieres:
            mid, mnom, coef = m
            mnom_clean = mnom.strip()
            k_s1, k_s2, k_moy = "m"+str(mid)+"_s1", "m"+str(mid)+"_s2", "m"+str(mid)+"_moy"
            cols.extend([k_s1, k_s2, k_moy])
            headers[k_s1] = mnom_clean + " S1"
            headers[k_s2] = mnom_clean + " S2"
            headers[k_moy] = mnom_clean + " Moy"
            for k in (k_s1, k_s2, k_moy):
                largeurs[k] = max(135, len(headers[k]) * 7 + 30)

        tree = ttk.Treeview(self.frame_grille, columns=cols, show="headings", height=15)
        tree.heading("matricule", text="Matricule")
        tree.column("matricule", width=largeurs["matricule"], minwidth=110, stretch=False, anchor="center")
        tree.heading("nom", text="Nom & Prenom de l'Eleve")
        tree.column("nom", width=largeurs["nom"], minwidth=200, stretch=False, anchor="w")
        for m in matieres:
            mid = m[0]
            for suffix in ("s1", "s2", "moy"):
                key = "m"+str(mid)+"_"+suffix
                tree.heading(key, text=headers[key])
                tree.column(key, width=largeurs[key], minwidth=135, stretch=False, anchor="center")
        vsb = ttk.Scrollbar(self.frame_grille, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(self.frame_grille, orient="horizontal", command=tree.xview)
        tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.frame_grille.grid_rowconfigure(0, weight=1)
        self.frame_grille.grid_columnconfigure(0, weight=1)

        def _fmt(v):
            if v is None: return "-"
            try: return ("{:g}".format(v) if float(v) == int(v) else "{:.2f}".format(v))
            except: return str(v)

        for el in eleves:
            el_id, mat, nom, prenom = el
            row = [mat, nom + " " + prenom]
            for m in matieres:
                mid = m[0]
                s1, s2 = notes_map.get((el_id, mid), (None, None))
                if s1 is not None and s2 is not None: moy = (s1 + s2) / 2
                elif s1 is not None: moy = s1
                elif s2 is not None: moy = s2
                else: moy = None
                row.extend([_fmt(s1), _fmt(s2), _fmt(moy)])
            tree.insert("", "end", values=row)

    def exporter_pv_excel(self, nom_classe, trim, eleves, matieres, notes_map):
        try:
            import pandas as pd
            data = []
            for el in eleves:
                el_id, mat, nom, prenom = el
                row = {"Matricule": mat, "Nom & Prenom": nom + " " + prenom}
                for m in matieres:
                    mid, mnom, coef = m
                    s1, s2 = notes_map.get((el_id, mid), (None, None))
                    moy = ((s1 + s2) / 2) if (s1 is not None and s2 is not None) else (s1 if s1 is not None else s2)
                    row[mnom + " (S1)"] = s1 if s1 is not None else ""
                    row[mnom + " (S2)"] = s2 if s2 is not None else ""
                    row[mnom + " (Moy)"] = round(moy, 2) if moy is not None else ""
                data.append(row)
            df = pd.DataFrame(data)
            c_clean = "".join(c for c in nom_classe if c.isalnum() or c in "-_")
            suggere = "PV_NOTES_" + c_clean + "_Trim" + str(trim) + ".xlsx"
            chemin = filedialog.asksaveasfilename(title="Enregistrer le PV sous Excel", initialfile=suggere, defaultextension=".xlsx", filetypes=[("Fichiers Excel", "*.xlsx")])
            if chemin:
                df.to_excel(chemin, index=False)
                messagebox.showinfo("Export Reussi", "PV exporte avec succes :\n\n" + chemin)
                try: os.startfile(chemin)
                except Exception: pass
        except Exception as e:
            messagebox.showerror("Erreur Export", "Impossible d'exporter : " + str(e))

    def enregistrer_notes(self):
        if self.mode_notes != "matiere":
            messagebox.showinfo("Info", "Ouvrez d'abord une matiere avec Voir / Modifier cette matiere.")
            return
        mat_id = self.dict_matieres_notes.get(self.combo_matiere_notes.get())
        trim = int(self.combo_trim_notes.get())
        if not mat_id: return
        conn = get_connection(); cursor = conn.cursor()
        nb = 0
        try:
            for el_id, (e1, e2) in self.entries_notes.items():
                s1 = e1.get().strip().replace(",", ".")
                s2 = e2.get().strip().replace(",", ".")
                v1 = float(s1) if s1 != "" else None
                v2 = float(s2) if s2 != "" else None
                if v1 is not None and not (0 <= v1 <= 20): raise ValueError("Note SEQ1 hors limites (0-20).")
                if v2 is not None and not (0 <= v2 <= 20): raise ValueError("Note SEQ2 hors limites (0-20).")
                cursor.execute("INSERT INTO notes (eleve_id, matiere_id, trimestre, seq1, seq2) VALUES (?, ?, ?, ?, ?) ON CONFLICT(eleve_id, matiere_id, trimestre) DO UPDATE SET seq1=excluded.seq1, seq2=excluded.seq2", (el_id, mat_id, trim, v1, v2))
                nb += 1
            conn.commit()
            messagebox.showinfo("Succes", str(nb) + " ligne(s) enregistree(s).")
            self.charger_grille_notes()
        except ValueError as e: messagebox.showerror("Erreur de saisie", str(e))
        finally: conn.close()

    # ==========================================
    # 4.5 DISCIPLINE
    # ==========================================
    def show_discipline_frame(self):
        self.clear_main_frame()
        classes_dict = self.get_classes_dict()
        if not classes_dict:
            ctk.CTkLabel(self.main_frame, text="Creez d'abord une classe.", font=ctk.CTkFont(size=16, weight="bold")).pack(expand=True)
            return
        ctk.CTkLabel(self.main_frame, text="Discipline & Absences", font=ctk.CTkFont(size=22, weight="bold"), text_color=VERT_FONCE).pack(anchor="w", padx=20, pady=(15, 5))
        top = ctk.CTkFrame(self.main_frame, fg_color=BLANC); top.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(top, text="Classe :", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        self.combo_classe_disc = ctk.CTkOptionMenu(top, values=list(classes_dict.keys()), fg_color=VERT, button_color=VERT_FONCE)
        self.combo_classe_disc.pack(side="left", padx=5)
        ctk.CTkLabel(top, text="Trimestre :", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        self.combo_trim_disc = ctk.CTkOptionMenu(top, values=["1", "2", "3"], width=60)
        self.combo_trim_disc.pack(side="left", padx=5)
        ctk.CTkButton(top, text="Charger la Classe", command=self.charger_grille_discipline, fg_color=VERT, hover_color=VERT_HOVER, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=15)
        self.lbl_disc_info = ctk.CTkLabel(self.main_frame, text="Remplissez les absences, avertissements, blames et exclusions par eleve.", text_color="gray")
        self.lbl_disc_info.pack(anchor="w", padx=25, pady=(0, 5))
        self.frame_grille_disc = ctk.CTkScrollableFrame(self.main_frame, height=380, fg_color=BLANC)
        self.frame_grille_disc.pack(fill="both", expand=True, padx=20, pady=5)
        bottom = ctk.CTkFrame(self.main_frame, fg_color="transparent"); bottom.pack(fill="x", padx=20, pady=8)
        ctk.CTkButton(bottom, text="Enregistrer la Discipline", command=self.enregistrer_discipline, fg_color=VERT, hover_color=VERT_HOVER, font=ctk.CTkFont(weight="bold"), height=36).pack(side="right", padx=5)
        self.charger_grille_discipline()

    def charger_grille_discipline(self):
        for w in self.frame_grille_disc.winfo_children(): w.destroy()
        c_id = self.get_classes_dict().get(self.combo_classe_disc.get())
        trim = int(self.combo_trim_disc.get())
        if not c_id: return
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id, matricule, nom, prenom FROM eleves WHERE classe_id = ? ORDER BY nom, prenom", (c_id,))
        eleves = cursor.fetchall()
        cursor.execute("SELECT eleve_id, heures_absences, avertissements, blames, jours_exclusion FROM disciplines WHERE trimestre = ?", (trim,))
        disc_map = {r[0]: (r[1], r[2], r[3], r[4]) for r in cursor.fetchall()}
        conn.close()
        headers = ["N", "Matricule", "Eleve", "Absences (heures)", "Avertissements", "Blames", "Jours Exclusion"]
        widths = [40, 100, 240, 130, 120, 100, 130]
        for col_idx, (h, w) in enumerate(zip(headers, widths)):
            ctk.CTkLabel(self.frame_grille_disc, text=h, font=ctk.CTkFont(weight="bold"), width=w, anchor="w" if col_idx==2 else "center").grid(row=0, column=col_idx, padx=5, pady=5)
        self.entries_discipline = {}
        for idx, el in enumerate(eleves, start=1):
            el_id, mat, nom, prenom = el
            h_abs, avert, blam, excl = disc_map.get(el_id, (0, 0, 0, 0))
            ctk.CTkLabel(self.frame_grille_disc, text=str(idx), width=40).grid(row=idx, column=0, padx=5, pady=3)
            ctk.CTkLabel(self.frame_grille_disc, text=mat, width=100).grid(row=idx, column=1, padx=5, pady=3)
            ctk.CTkLabel(self.frame_grille_disc, text=nom + " " + prenom, width=240, anchor="w").grid(row=idx, column=2, padx=5, pady=3)
            e_abs = ctk.CTkEntry(self.frame_grille_disc, width=80); e_abs.insert(0, str(h_abs or 0)); e_abs.grid(row=idx, column=3, padx=5, pady=3)
            e_avert = ctk.CTkEntry(self.frame_grille_disc, width=80); e_avert.insert(0, str(avert or 0)); e_avert.grid(row=idx, column=4, padx=5, pady=3)
            e_blam = ctk.CTkEntry(self.frame_grille_disc, width=80); e_blam.insert(0, str(blam or 0)); e_blam.grid(row=idx, column=5, padx=5, pady=3)
            e_excl = ctk.CTkEntry(self.frame_grille_disc, width=80); e_excl.insert(0, str(excl or 0)); e_excl.grid(row=idx, column=6, padx=5, pady=3)
            self.entries_discipline[el_id] = (e_abs, e_avert, e_blam, e_excl)

    def enregistrer_discipline(self):
        trim = int(self.combo_trim_disc.get())
        conn = get_connection(); cursor = conn.cursor()
        nb = 0
        try:
            for el_id, (e_abs, e_avert, e_blam, e_excl) in self.entries_discipline.items():
                h_abs = int(e_abs.get().strip() or 0)
                avert = int(e_avert.get().strip() or 0)
                blam = int(e_blam.get().strip() or 0)
                excl = int(e_excl.get().strip() or 0)
                cursor.execute("INSERT INTO disciplines (eleve_id, trimestre, heures_absences, avertissements, blames, jours_exclusion) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(eleve_id, trimestre) DO UPDATE SET heures_absences=excluded.heures_absences, avertissements=excluded.avertissements, blames=excluded.blames, jours_exclusion=excluded.jours_exclusion", (el_id, trim, h_abs, avert, blam, excl))
                nb += 1
            conn.commit()
            messagebox.showinfo("Succes", "Discipline enregistree pour " + str(nb) + " eleve(s).")
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez entrer uniquement des nombres entiers.")
        finally: conn.close()

    # ==========================================
    # 5. ECHANGES PROFS
    # ==========================================
    def show_echanges_frame(self):
        self.clear_main_frame()
        classes_dict = self.get_classes_dict()
        ctk.CTkLabel(self.main_frame, text="Echanges de Fichiers avec les Professeurs", font=ctk.CTkFont(size=22, weight="bold"), text_color=VERT_FONCE).pack(anchor="w", padx=20, pady=10)
        box_export = ctk.CTkFrame(self.main_frame, fg_color=BLANC); box_export.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(box_export, text="1. EXPORTER UN FICHIER DE SAISIE SECURISE POUR UN PROF", font=ctk.CTkFont(size=15, weight="bold"), text_color=VERT_FONCE).pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(box_export, text="Verrouille le fichier sur la matiere du prof.").pack(anchor="w", padx=15, pady=(0, 10))
        f_row1 = ctk.CTkFrame(box_export, fg_color="transparent"); f_row1.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_row1, text="Classe :", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        self.combo_classe_export = ctk.CTkOptionMenu(f_row1, values=list(classes_dict.keys()) if classes_dict else ["Aucune classe"], command=lambda _: self.charger_combo_matieres_export(), fg_color=VERT, button_color=VERT_FONCE)
        self.combo_classe_export.pack(side="left", padx=10)
        ctk.CTkLabel(f_row1, text="Matiere Ciblee :", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        self.combo_matiere_export = ctk.CTkOptionMenu(f_row1, values=["Toutes les matieres (Non verrouille)"])
        self.combo_matiere_export.pack(side="left", padx=10)
        f_row2 = ctk.CTkFrame(box_export, fg_color="transparent"); f_row2.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(f_row2, text="Code PIN Secret (Optionnel) :", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        self.ent_pin_export = ctk.CTkEntry(f_row2, width=100, placeholder_text="Ex: 1234")
        self.ent_pin_export.pack(side="left", padx=10)
        btn_exp_notes = ctk.CTkButton(f_row2, text="Exporter Fichier Verrouille (.notes)", command=self.exporter_fichier_classe, fg_color=VERT_FONCE, hover_color=VERT_HOVER, font=ctk.CTkFont(weight="bold"), height=35)
        btn_exp_notes.pack(side="left", padx=20)
        box_import = ctk.CTkFrame(self.main_frame, fg_color=BLANC); box_import.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(box_import, text="2. IMPORTER LES NOTES RENVOYEES PAR UN PROF", font=ctk.CTkFont(size=15, weight="bold"), text_color=VERT).pack(anchor="w", padx=15, pady=(15, 5))
        btn_imp_notes = ctk.CTkButton(box_import, text="Importer Fichier de Notes (.notes)", command=self.importer_fichier_notes, fg_color=VERT, hover_color=VERT_HOVER, font=ctk.CTkFont(size=15, weight="bold"), height=42)
        btn_imp_notes.pack(padx=15, pady=(5, 15), anchor="w")
        self.charger_combo_matieres_export()

    def charger_combo_matieres_export(self):
        classes_dict = self.get_classes_dict()
        c_id = classes_dict.get(self.combo_classe_export.get())
        if not c_id: return
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id, nom, enseignant FROM matieres WHERE classe_id = ?", (c_id,))
        mats = cursor.fetchall(); conn.close()
        self.dict_matieres_export = {m[1] + " (" + m[2] + ")" if m[2] else m[1]: m[0] for m in mats}
        options = ["Toutes les matieres (Non verrouille)"] + list(self.dict_matieres_export.keys())
        self.combo_matiere_export.configure(values=options)
        self.combo_matiere_export.set(options[0])

    def exporter_fichier_classe(self):
        classes_dict = self.get_classes_dict()
        nom_classe = self.combo_classe_export.get()
        classe_id = classes_dict.get(nom_classe)
        if not classe_id: return
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id, matricule, nom, prenom, sexe FROM eleves WHERE classe_id = ? ORDER BY nom, prenom", (classe_id,))
        eleves = [{"id": r[0], "matricule": r[1], "nom": r[2], "prenom": r[3], "sexe": r[4]} for r in cursor.fetchall()]
        cursor.execute("SELECT id, nom, coefficient, enseignant FROM matieres WHERE classe_id = ?", (classe_id,))
        matieres = [{"id": r[0], "nom": r[1], "coef": r[2], "prof": r[3]} for r in cursor.fetchall()]
        conn.close()
        if not eleves:
            messagebox.showwarning("Attention", "Aucun eleve dans cette classe.")
            return
        choix_mat = self.combo_matiere_export.get()
        mat_cible_id = self.dict_matieres_export.get(choix_mat)
        pin_code = self.ent_pin_export.get().strip()
        donnees = {"classe_id": classe_id, "classe_nom": nom_classe, "matiere_cible_id": mat_cible_id, "pin_code": pin_code if pin_code else None, "matieres": matieres, "eleves": eleves}
        c_nom_clean = "".join(c for c in nom_classe if c.isalnum() or c in "-_")
        mat_clean = "".join(c for c in choix_mat.split("(")[0] if c.isalnum() or c in "-_").strip()
        fichier_suggere = "CLASSE_" + c_nom_clean + "_" + mat_clean + ".notes" if mat_cible_id else "CLASSE_" + c_nom_clean + ".notes"
        chemin = filedialog.asksaveasfilename(title="Enregistrer le fichier de saisie", initialfile=fichier_suggere, defaultextension=".notes", filetypes=[("Fichiers Notes", "*.notes")])
        if chemin:
            with open(chemin, "w", encoding="utf-8") as f: json.dump(donnees, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Export Reussi", "Fichier genere :\n" + chemin)

    def importer_fichier_notes(self):
        chemin = filedialog.askopenfilename(title="Selectionner le fichier de notes", filetypes=[("Fichiers Notes", "*.notes"), ("Fichiers JSON", "*.json")])
        if not chemin: return
        try:
            with open(chemin, "r", encoding="utf-8") as f: donnees = json.load(f)
            c_id = donnees.get("classe_id")
            mat_cible_id = donnees.get("matiere_cible_id")
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("SELECT id, nom FROM matieres WHERE classe_id = ?", (c_id,))
            mat_map = {r[1]: r[0] for r in cursor.fetchall()}
            nb = 0
            for el in donnees.get("eleves", []):
                el_id = el["id"]
                for trim_str, mats in el.get("notes", {}).items():
                    trim = int(trim_str)
                    for mat_nom, vals in mats.items():
                        if mat_nom in mat_map:
                            mat_id = mat_map[mat_nom]
                            if mat_cible_id and mat_id != mat_cible_id: continue
                            s1, s2 = vals.get("seq1"), vals.get("seq2")
                            if s1 is not None or s2 is not None:
                                cursor.execute("INSERT INTO notes (eleve_id, matiere_id, trimestre, seq1, seq2) VALUES (?, ?, ?, ?, ?) ON CONFLICT(eleve_id, matiere_id, trimestre) DO UPDATE SET seq1=excluded.seq1, seq2=excluded.seq2", (el_id, mat_id, trim, s1, s2))
                                nb += 1
            conn.commit(); conn.close()
            msg = str(nb) + " note(s) importee(s) avec succes."
            if nb > 0 and messagebox.askyesno("Importation reussie", msg + "\n\nVoulez-vous consulter les notes maintenant ?"):
                self.show_notes_frame()
                try:
                    conn2 = get_connection(); cur2 = conn2.cursor()
                    cur2.execute("SELECT nom FROM classes WHERE id = ?", (c_id,))
                    row = cur2.fetchone(); conn2.close()
                    if row:
                        self.combo_classe_notes.set(row[0])
                        self.charger_combo_matieres_notes()
                        if mat_cible_id:
                            conn3 = get_connection(); cur3 = conn3.cursor()
                            cur3.execute("SELECT nom FROM matieres WHERE id = ?", (mat_cible_id,))
                            m_row = cur3.fetchone(); conn3.close()
                            if m_row: self.combo_matiere_notes.set(m_row[0])
                        self.charger_grille_notes()
                except Exception: pass
            else:
                messagebox.showinfo("Importation Reussie", msg)
        except Exception as e:
            messagebox.showerror("Erreur", "Erreur lors de l'importation : " + str(e))

    # ==========================================
    # 6. BULLETINS & PDF
    # ==========================================
    def show_pdf_frame(self):
        self.clear_main_frame()
        classes_dict = self.get_classes_dict()
        if not classes_dict: return
        ctk.CTkLabel(self.main_frame, text="Generation des Documents PDF", font=ctk.CTkFont(size=22, weight="bold"), text_color=VERT_FONCE).pack(anchor="w", padx=20, pady=10)
        top = ctk.CTkFrame(self.main_frame, fg_color=BLANC); top.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(top, text="Selectionner la classe :").pack(side="left", padx=10)
        self.combo_classe_pdf = ctk.CTkOptionMenu(top, values=list(classes_dict.keys()), fg_color=VERT, button_color=VERT_FONCE); self.combo_classe_pdf.pack(side="left", padx=10)
        ctk.CTkLabel(top, text="Trimestre :").pack(side="left", padx=10)
        self.combo_trim_pdf = ctk.CTkOptionMenu(top, values=["1", "2", "3", "Annuel"], width=90); self.combo_trim_pdf.pack(side="left", padx=10)
        frame_boutons = ctk.CTkFrame(self.main_frame, fg_color=BLANC); frame_boutons.pack(fill="x", padx=20, pady=20)
        ctk.CTkButton(frame_boutons, text="Generer TOUS LES BULLETINS en PDF", command=self.generer_tous_bulletins, fg_color=VERT_FONCE, hover_color=VERT_HOVER, font=ctk.CTkFont(size=15, weight="bold"), height=50).pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(frame_boutons, text="Generer la FICHE STATISTIQUE de Classe (PDF)", command=self.generer_statistiques_pdf, fg_color=KAKI_FONCE, hover_color=VERT_FONCE, font=ctk.CTkFont(size=15, weight="bold"), height=50).pack(fill="x", padx=20, pady=10)

    def generer_tous_bulletins(self):
        trim_str = self.combo_trim_pdf.get()
        if trim_str == "Annuel":
            self.generer_bulletins_annuels()
            return
        trim = int(trim_str)
        conn = get_connection()
        c_id = self.get_classes_dict().get(self.combo_classe_pdf.get())
        res = calculer_bulletins_classe(conn, c_id, trim)
        if "erreur" in res: conn.close(); messagebox.showerror("Erreur", res["erreur"]); return
        cursor = conn.cursor()
        cursor.execute("SELECT cle, valeur FROM parametres"); params_etab = dict(cursor.fetchall())
        params_etab["trimestre"] = trim
        params_etab["trimestre_actif"] = str(trim)
        cursor.execute("SELECT nom, prof_principal FROM classes WHERE id = ?", (c_id,)); classe_nom, prof_principal = cursor.fetchone()
        cursor.execute("SELECT id, date_naissance, lieu_naissance FROM eleves WHERE classe_id = ?", (c_id,)); naissances = {r[0]: (r[1] or "", r[2] or "") for r in cursor.fetchall()}
        cursor.execute("SELECT eleve_id, heures_absences, avertissements, blames, jours_exclusion FROM disciplines WHERE trimestre = ?", (trim,)); disciplines = {r[0]: {"heures_absences": r[1], "avertissements": r[2], "blames": r[3], "jours_exclusion": r[4]} for r in cursor.fetchall()}
        conn.close()
        res["stats"]["moyennes_classe_matiere"] = res["moyennes_classe_matiere"]
        propre = lambda s: "".join(c if c.isalnum() or c in "-_" else "_" for c in str(s))
        racine = get_app_dir()
        dossier = os.path.join(racine, "output_bulletins", propre(classe_nom) + "_Trim" + str(trim))
        os.makedirs(dossier, exist_ok=True)
        nb = 0
        for el_id, d in res["eleves"].items():
            d["info"]["classe_nom"] = classe_nom; d["info"]["prof_principal"] = prof_principal
            d["info"]["date_naissance"], d["info"]["lieu_naissance"] = naissances.get(el_id, ("", ""))
            d["discipline"] = disciplines.get(el_id, {})
            fichier = os.path.join(dossier, "Bulletin_" + propre(d['info']['matricule']) + "_" + propre(d['info']['nom']) + "_" + propre(d['info']['prenom']) + ".pdf")
            generer_bulletin_pdf(d, res["stats"], params_etab, fichier, trimestre=trim)
            nb += 1
        messagebox.showinfo("Termine", str(nb) + " bulletin(s) genere(s) dans :\n" + dossier)
        try: os.startfile(dossier)
        except Exception: pass

    def generer_bulletins_annuels(self):
        if calculer_bulletins_annuels is None:
            messagebox.showerror("Erreur", "Fonction annuelle manquante dans core/calculator.py. Ajoute calculer_bulletins_annuels.")
            return
        from pdfs.pdf_annuel import generer_bulletin_annuel_pdf
        c_id = self.get_classes_dict().get(self.combo_classe_pdf.get())
        conn = get_connection()
        res = calculer_bulletins_annuels(conn, c_id)
        if "erreur" in res:
            conn.close()
            messagebox.showerror("Erreur", res["erreur"])
            return
        cur = conn.cursor()
        cur.execute("SELECT cle, valeur FROM parametres")
        params_etab = dict(cur.fetchall())
        cur.execute("SELECT nom, prof_principal FROM classes WHERE id = ?", (c_id,))
        classe_nom, prof_principal = cur.fetchone()
        cur.execute("SELECT id, date_naissance, lieu_naissance FROM eleves WHERE classe_id = ?", (c_id,))
        naiss = {r[0]: (r[1] or "", r[2] or "") for r in cur.fetchall()}
        cur.execute("SELECT eleve_id, SUM(heures_absences), SUM(avertissements), SUM(blames), SUM(jours_exclusion) FROM disciplines GROUP BY eleve_id")
        disc_an = {r[0]: {"heures_absences": r[1] or 0, "avertissements": r[2] or 0, "blames": r[3] or 0, "jours_exclusion": r[4] or 0} for r in cur.fetchall()}
        conn.close()
        res["stats"]["moyennes_classe_matiere"] = res["moyennes_classe_matiere"]
        propre = lambda s: "".join(c if c.isalnum() or c in "-_" else "_" for c in str(s))
        racine = get_app_dir()
        dossier = os.path.join(racine, "output_bulletins", propre(classe_nom) + "_Annuel")
        os.makedirs(dossier, exist_ok=True)
        nb = 0
        for el_id, d in res["eleves"].items():
            d["info"]["classe_nom"] = classe_nom
            d["info"]["prof_principal"] = prof_principal
            d["info"]["date_naissance"], d["info"]["lieu_naissance"] = naiss.get(el_id, ("", ""))
            d["discipline_an"] = disc_an.get(el_id, {})
            d["discipline"] = disc_an.get(el_id, {})
            fichier = os.path.join(dossier, "Bulletin_Annuel_" + propre(d['info']['matricule']) + "_" + propre(d['info']['nom']) + ".pdf")
            generer_bulletin_annuel_pdf(d, res["stats"], params_etab, fichier)
            nb += 1
        messagebox.showinfo("Termine", str(nb) + " bulletin(s) annuel(s) genere(s) dans :\n" + dossier)
        try: os.startfile(dossier)
        except: pass

    def generer_statistiques_pdf(self):
        trim_str = self.combo_trim_pdf.get()
        if trim_str == "Annuel":
            self.generer_statistiques_annuelles()
            return
        trim = int(trim_str)
        c_id = self.get_classes_dict().get(self.combo_classe_pdf.get())
        conn = get_connection(); res = calculer_bulletins_classe(conn, c_id, trim)
        if "erreur" in res: conn.close(); messagebox.showerror("Erreur", res["erreur"]); return
        cursor = conn.cursor()
        cursor.execute("SELECT cle, valeur FROM parametres"); params_etab = dict(cursor.fetchall())
        cursor.execute("SELECT nom FROM classes WHERE id = ?", (c_id,)); classe_nom = cursor.fetchone()[0]; conn.close()
        propre = lambda s: "".join(c if c.isalnum() or c in "-_" else "_" for c in str(s))
        racine = get_app_dir()
        dossier = os.path.join(racine, "output_bulletins", propre(classe_nom) + "_Trim" + str(trim))
        os.makedirs(dossier, exist_ok=True)
        fichier_pdf = os.path.join(dossier, "Statistiques_Trim" + str(trim) + "_" + propre(classe_nom) + ".pdf")
        generer_fiche_statistiques_pdf(classe_nom, trim, res["stats"], params_etab, fichier_pdf)
        messagebox.showinfo("Succes", "Fiche Statistique generee :\n" + fichier_pdf)
        try: os.startfile(dossier)
        except Exception: pass

    def generer_statistiques_annuelles(self):
        if calculer_bulletins_annuels is None:
            messagebox.showerror("Erreur", "Fonction annuelle manquante dans core/calculator.py. Ajoute calculer_bulletins_annuels.")
            return
        try:
            from pdfs.stats_annuel import generer_fiche_statistiques_annuelle_pdf
        except ImportError as e:
            messagebox.showerror("Erreur", "Fichier pdfs/stats_annuel.py introuvable : " + str(e))
            return
        c_id = self.get_classes_dict().get(self.combo_classe_pdf.get())
        conn = get_connection()
        res_an = calculer_bulletins_annuels(conn, c_id)
        if "erreur" in res_an:
            conn.close()
            messagebox.showerror("Erreur", res_an["erreur"])
            return
        rappels_moy = {}
        for t in (1, 2, 3):
            res_t = calculer_bulletins_classe(conn, c_id, t)
            if "erreur" in res_t:
                rappels_moy[t] = None
            else:
                rappels_moy[t] = res_t["stats"].get("moy_classe_gen")
        cur = conn.cursor()
        cur.execute("SELECT cle, valeur FROM parametres")
        params_etab = dict(cur.fetchall())
        cur.execute("SELECT nom FROM classes WHERE id = ?", (c_id,))
        classe_nom = cur.fetchone()[0]
        conn.close()
        propre = lambda s: "".join(c if c.isalnum() or c in "-_" else "_" for c in str(s))
        racine = get_app_dir()
        dossier = os.path.join(racine, "output_bulletins", propre(classe_nom) + "_Annuel")
        os.makedirs(dossier, exist_ok=True)
        fichier_pdf = os.path.join(dossier, "Statistiques_Annuelle_" + propre(classe_nom) + ".pdf")
        generer_fiche_statistiques_annuelle_pdf(classe_nom, res_an["stats"], rappels_moy, params_etab, fichier_pdf)
        messagebox.showinfo("Succes", "Fiche Statistique Annuelle generee :\n" + fichier_pdf)
        try: os.startfile(dossier)
        except: pass

    # ==========================================
    # 7. CONFIGURATION + MOT DE PASSE
    # ==========================================
    def show_config_frame(self):
        self.clear_main_frame()
        ctk.CTkLabel(self.main_frame, text="Configuration", font=ctk.CTkFont(size=22, weight="bold"), text_color=VERT_FONCE).pack(anchor="w", padx=20, pady=10)
        champs = [("etablissement_nom", "Nom etablissement"), ("etablissement_devise", "Devise du college"), ("etablissement_bp", "BP"), ("etablissement_tel", "Telephone"), ("etablissement_email", "Email"), ("etablissement_ville", "Ville"), ("annee_scolaire", "Annee scolaire")]
        conn = get_connection(); cursor = conn.cursor(); cursor.execute("SELECT cle, valeur FROM parametres"); valeurs = dict(cursor.fetchall()); conn.close()
        form = ctk.CTkFrame(self.main_frame, fg_color=BLANC); form.pack(fill="x", padx=20, pady=10)
        self.entries_config = {}
        for i, (cle, label) in enumerate(champs):
            ctk.CTkLabel(form, text=label+" :", anchor="w", width=180).grid(row=i, column=0, padx=10, pady=6, sticky="w")
            e = ctk.CTkEntry(form, width=420); e.insert(0, valeurs.get(cle, "")); e.grid(row=i, column=1, padx=10, pady=6, sticky="w")
            self.entries_config[cle] = e
        ctk.CTkLabel(form, text="Mot de passe Admin :", anchor="w", width=180).grid(row=len(champs), column=0, padx=10, pady=6, sticky="w")
        self.entry_new_pass = ctk.CTkEntry(form, width=420, placeholder_text="Laisser vide pour ne pas changer", show="*")
        self.entry_new_pass.grid(row=len(champs), column=1, padx=10, pady=6, sticky="w")
        ctk.CTkButton(self.main_frame, text="Enregistrer", command=self.enregistrer_config, fg_color=VERT, hover_color=VERT_HOVER).pack(anchor="e", padx=20, pady=10)

    def enregistrer_config(self):
        conn = get_connection(); cursor = conn.cursor()
        for cle, entry in self.entries_config.items():
            cursor.execute("INSERT INTO parametres (cle, valeur) VALUES (?, ?) ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur", (cle, entry.get().strip()))
        new_pass = self.entry_new_pass.get().strip()
        if new_pass:
            cursor.execute("INSERT INTO parametres (cle, valeur) VALUES ('admin_password', ?) ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur", (new_pass,))
        conn.commit(); conn.close()
        messagebox.showinfo("Succes", "Configuration enregistree.")


if __name__ == "__main__":
    app = AdminApp()
    app.mainloop()
    