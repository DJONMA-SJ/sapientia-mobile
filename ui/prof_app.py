import sys
import os
import json
import customtkinter as ctk
from tkinter import filedialog, messagebox

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("green")

COULEUR_VERT_FONCE = "#14532D"
COULEUR_VERT = "#1E6B3A"
COULEUR_VERT_HOVER = "#2A7F4B"
COULEUR_KAKI = "#C9BC8A"
COULEUR_KAKI_FONCE = "#8F8252"
COULEUR_KAKI_CLAIR = "#E8E0C3"
COULEUR_FOND = "#F4F1E6"


class ProfApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("BULLETIN PRO - Espace Professeur (Saisie des Notes)")
        self.geometry("980 x 640")
        self.minsize(850, 520)
        self.configure(fg_color=COULEUR_FOND)

        self.donnees_classe = None
        self.entries_notes = {}
        self.matieres_autorisees_ids = []
        self._logo_top_image = None

        self.top_frame = ctk.CTkFrame(self, fg_color=COULEUR_VERT_FONCE, corner_radius=0, height=90)
        self.top_frame.pack(fill="x", padx=0, pady=0)

        self._logo_top_image = self._charger_logo_top(taille=64)
        if self._logo_top_image is not None:
            self.logo_label = ctk.CTkLabel(self.top_frame, image=self._logo_top_image, text="  Espace Professeur - Saisie SECURISEE", compound="left", text_color="white", font=ctk.CTkFont(size=18, weight="bold"))
        else:
            self.logo_label = ctk.CTkLabel(self.top_frame, text="Espace Professeur - Saisie SECURISEE", text_color="white", font=ctk.CTkFont(size=18, weight="bold"))
        self.logo_label.pack(side="left", padx=20, pady=12)

        self.btn_ouvrir = ctk.CTkButton(
            self.top_frame, text="Ouvrir Fichier Classe (.notes)",
            command=self.ouvrir_fichier_classe,
            fg_color=COULEUR_KAKI, hover_color=COULEUR_KAKI_CLAIR, text_color="#1A1A1A",
            font=ctk.CTkFont(weight="bold"), height=38
        )
        self.btn_ouvrir.pack(side="right", padx=20, pady=12)

        self.info_frame = ctk.CTkFrame(self, fg_color="white")
        self.info_frame.pack(fill="x", padx=20, pady=10)

        self.lbl_info_classe = ctk.CTkLabel(
            self.info_frame,
            text="Veuillez ouvrir un fichier classe fourni par l'administration pour commencer.",
            font=ctk.CTkFont(size=13)
        )
        self.lbl_info_classe.pack(side="left", padx=15, pady=10)

        self.lbl_verrou = ctk.CTkLabel(
            self.info_frame, text="Non charge",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="gray"
        )
        self.lbl_verrou.pack(side="right", padx=15, pady=10)

        self.combo_matiere = ctk.CTkOptionMenu(
            self.info_frame, values=["Matieres..."], command=self.changer_matiere, width=220
        )
        self.combo_matiere.pack(side="right", padx=10, pady=10)

        self.combo_trimestre = ctk.CTkOptionMenu(
            self.info_frame, values=["Trimestre 1", "Trimestre 2", "Trimestre 3"],
            width=130, command=lambda _: self.afficher_grille()
        )
        self.combo_trimestre.set("Trimestre 2")
        self.combo_trimestre.pack(side="right", padx=5, pady=10)

        self.grille_frame = ctk.CTkScrollableFrame(self, fg_color="white")
        self.grille_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.bottom_frame = ctk.CTkFrame(self, fg_color="white")
        self.bottom_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.btn_exporter = ctk.CTkButton(
            self.bottom_frame, text="Enregistrer et Exporter mes Notes",
            command=self.exporter_notes, fg_color=COULEUR_VERT, hover_color=COULEUR_VERT_FONCE,
            font=ctk.CTkFont(size=14, weight="bold"), height=40, state="disabled"
        )
        self.btn_exporter.pack(side="right", padx=15, pady=10)

    def _trouver_fichier_logo(self):
        if getattr(sys, 'frozen', False):
            base_exe = os.path.dirname(sys.executable)
            for rel in [os.path.join("assets", "logo.png"), os.path.join("assets", "logo.jpg"), os.path.join("logo.png")]:
                p = os.path.join(base_exe, rel)
                if os.path.exists(p):
                    return p
            if hasattr(sys, '_MEIPASS'):
                p2 = os.path.join(sys._MEIPASS, "assets", "logo.png")
                if os.path.exists(p2):
                    return p2
        racine = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        for rel in [os.path.join("assets", "logo.png"), os.path.join("Assets", "logo.png"),
                    os.path.join("assets", "logo.jpg"), os.path.join("Assets", "logo.jpg"),
                    os.path.join("assets", "logo.jpeg"), os.path.join("logo.png")]:
            p = os.path.join(racine, rel)
            if os.path.exists(p):
                return p
        return None

    def _charger_logo_top(self, taille=64):
        try:
            from PIL import Image
            chemin = self._trouver_fichier_logo()
            if not chemin:
                return None
            img = Image.open(chemin).convert("RGBA")
            img.thumbnail((taille, taille))
            canvas = Image.new("RGBA", (taille, taille), (255, 255, 255, 255))
            x = (taille - img.size[0]) // 2
            y = (taille - img.size[1]) // 2
            canvas.paste(img, (x, y), img)
            return ctk.CTkImage(light_image=canvas, dark_image=canvas, size=(taille, taille))
        except Exception:
            return None

    def ouvrir_fichier_classe(self):
        filename = filedialog.askopenfilename(
            title="Ouvrir un fichier de classe",
            filetypes=[("Fichiers Notes", "*.notes"), ("Fichiers JSON", "*.json")]
        )
        if not filename:
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                self.donnees_classe = json.load(f)
            if "classe_nom" not in self.donnees_classe or "eleves" not in self.donnees_classe:
                messagebox.showerror("Erreur", "Format de fichier invalide ou corrompu.")
                return
            c_nom = self.donnees_classe["classe_nom"]
            nb_el = len(self.donnees_classe["eleves"])

            pin_requis = self.donnees_classe.get("pin_code")
            if pin_requis:
                dialog = ctk.CTkInputDialog(
                    text="Ce fichier est protege par un Code PIN.\nSaisissez le code secret fourni par l'administration :",
                    title="Deverrouillage Securise"
                )
                code_saisi = dialog.get_input()
                if str(code_saisi).strip() != str(pin_requis).strip():
                    messagebox.showerror("Acces Refuse", "Code PIN incorrect. Ouverture annulee.")
                    self.donnees_classe = None
                    return

            mats = self.donnees_classe.get("matieres", [])
            mat_cible_id = self.donnees_classe.get("matiere_cible_id")
            prof_cible = self.donnees_classe.get("prof_cible")

            if mat_cible_id:
                mats_autorisees = [m for m in mats if m.get("id") == mat_cible_id]
            elif prof_cible:
                mats_autorisees = [m for m in mats if str(m.get("prof", "")).strip().lower() == str(prof_cible).strip().lower()]
            else:
                mats_autorisees = mats

            self.matieres_autorisees_ids = [m.get("id") for m in mats_autorisees]
            noms_mats_auto = [m.get("nom", "") for m in mats_autorisees]

            if not noms_mats_auto:
                messagebox.showerror("Erreur", "Aucune matiere autorisee trouvee pour ce professeur dans ce fichier.")
                return

            self.combo_matiere.configure(values=noms_mats_auto)
            self.combo_matiere.set(noms_mats_auto[0])

            if len(noms_mats_auto) == 1:
                self.combo_matiere.configure(state="disabled")
                self.lbl_verrou.configure(text="Verrouille sur : " + noms_mats_auto[0], text_color=COULEUR_VERT)
            else:
                self.combo_matiere.configure(state="normal")
                self.lbl_verrou.configure(text=str(len(noms_mats_auto)) + " Matiere(s) autorisee(s)", text_color=COULEUR_VERT)

            self.lbl_info_classe.configure(
                text="Classe : " + str(c_nom) + "   |   Effectif : " + str(nb_el) + " eleves",
                font=ctk.CTkFont(size=14, weight="bold")
            )
            self.btn_exporter.configure(state="normal")
            self.afficher_grille()
        except Exception as e:
            messagebox.showerror("Erreur", "Impossible de lire le fichier : " + str(e))

    def changer_matiere(self, _):
        self.afficher_grille()

    def afficher_grille(self):
        for widget in self.grille_frame.winfo_children():
            widget.destroy()
        if not self.donnees_classe:
            return
        mat_nom_actuelle = self.combo_matiere.get()

        ctk.CTkLabel(self.grille_frame, text="N", font=ctk.CTkFont(weight="bold"), width=40).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkLabel(self.grille_frame, text="Matricule", font=ctk.CTkFont(weight="bold"), width=110).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkLabel(self.grille_frame, text="Nom et Prenom de l'Eleve", font=ctk.CTkFont(weight="bold"), width=300, anchor="w").grid(row=0, column=2, padx=10, pady=5)
        ctk.CTkLabel(self.grille_frame, text="SEQ 1 (/20)", font=ctk.CTkFont(weight="bold"), width=120).grid(row=0, column=3, padx=10, pady=5)
        ctk.CTkLabel(self.grille_frame, text="SEQ 2 (/20)", font=ctk.CTkFont(weight="bold"), width=120).grid(row=0, column=4, padx=10, pady=5)

        ctk.CTkLabel(self.grille_frame, text="Matiere : " + mat_nom_actuelle, text_color=COULEUR_VERT_FONCE, font=ctk.CTkFont(weight="bold")).grid(row=0, column=5, padx=10, pady=5, sticky="w")

        self.entries_notes = {}
        trim_str = self.combo_trimestre.get()
        if "1" in trim_str:
            trim_num = "1"
        elif "2" in trim_str:
            trim_num = "2"
        else:
            trim_num = "3"

        for idx, el in enumerate(self.donnees_classe["eleves"], start=1):
            el_id = str(el["id"])
            mat_code = el.get("matricule", "")
            nom_complet = str(el.get("nom", "")) + " " + str(el.get("prenom", ""))
            notes_existantes = el.get("notes", {}).get(trim_num, {}).get(mat_nom_actuelle, {})
            v1 = notes_existantes.get("seq1")
            v2 = notes_existantes.get("seq2")
            seq1_val = "" if v1 is None else str(v1)
            seq2_val = "" if v2 is None else str(v2)

            ctk.CTkLabel(self.grille_frame, text=str(idx), width=40).grid(row=idx, column=0, padx=5, pady=4)
            ctk.CTkLabel(self.grille_frame, text=mat_code, width=110).grid(row=idx, column=1, padx=5, pady=4)
            ctk.CTkLabel(self.grille_frame, text=nom_complet, width=300, anchor="w").grid(row=idx, column=2, padx=10, pady=4)

            e1 = ctk.CTkEntry(self.grille_frame, width=100, placeholder_text="0-20")
            e1.insert(0, seq1_val)
            e1.grid(row=idx, column=3, padx=10, pady=4)

            e2 = ctk.CTkEntry(self.grille_frame, width=100, placeholder_text="0-20")
            e2.insert(0, seq2_val)
            e2.grid(row=idx, column=4, padx=10, pady=4)

            self.entries_notes[el_id] = (e1, e2)

    def exporter_notes(self):
        if not self.donnees_classe:
            return
        mat_nom = self.combo_matiere.get()
        trim_str = self.combo_trimestre.get()
        if "1" in trim_str:
            trim_num = "1"
        elif "2" in trim_str:
            trim_num = "2"
        else:
            trim_num = "3"

        notes_a_sauver = {}
        for el_id, (e1, e2) in self.entries_notes.items():
            v1_str = e1.get().strip().replace(",", ".")
            v2_str = e2.get().strip().replace(",", ".")
            v1 = None
            v2 = None
            if v1_str != "":
                try:
                    v1 = float(v1_str)
                    if not (0 <= v1 <= 20):
                        raise ValueError()
                except ValueError:
                    messagebox.showerror("Erreur de Saisie", "Note SEQ1 invalide. Entrez un nombre entre 0 et 20.")
                    return
            if v2_str != "":
                try:
                    v2 = float(v2_str)
                    if not (0 <= v2 <= 20):
                        raise ValueError()
                except ValueError:
                    messagebox.showerror("Erreur de Saisie", "Note SEQ2 invalide. Entrez un nombre entre 0 et 20.")
                    return
            notes_a_sauver[el_id] = {"seq1": v1, "seq2": v2}

        for el in self.donnees_classe["eleves"]:
            el_id = str(el["id"])
            if "notes" not in el:
                el["notes"] = {}
            if trim_num not in el["notes"]:
                el["notes"][trim_num] = {}
            if el_id in notes_a_sauver:
                el["notes"][trim_num][mat_nom] = notes_a_sauver[el_id]

        c_nom_clean = "".join(c for c in str(self.donnees_classe["classe_nom"]) if c.isalnum() or c in "-_")
        mat_clean = "".join(c for c in str(mat_nom) if c.isalnum() or c in "-_")
        nom_suggere = "NOTES_" + c_nom_clean + "_" + mat_clean + "_Trim" + trim_num + ".notes"

        fichier_sauvegarder = filedialog.asksaveasfilename(
            title="Enregistrer le fichier de notes",
            initialfile=nom_suggere,
            defaultextension=".notes",
            filetypes=[("Fichiers Notes", "*.notes")]
        )
        if not fichier_sauvegarder:
            return
        try:
            with open(fichier_sauvegarder, "w", encoding="utf-8") as f:
                json.dump(self.donnees_classe, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Succes", "Notes enregistrees avec succes pour la matiere '" + mat_nom + "'.\n\nTransmettez ce fichier a l'administration :\n" + fichier_sauvegarder)
        except Exception as e:
            messagebox.showerror("Erreur", "Erreur lors de l'enregistrement : " + str(e))


if __name__ == "__main__":
    app = ProfApp()
    app.mainloop()