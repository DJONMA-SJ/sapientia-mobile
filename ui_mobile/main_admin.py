import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
from tkinter import messagebox
from database.database import get_connection, init_db

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("green")

COULEUR_VERT_FONCE = "#14532D"
COULEUR_VERT = "#1E6B3A"
COULEUR_FOND = "#F4F1E6"
MOT_DE_PASSE_DEFAUT = "admin123"


def trouver_logo():
    base = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    for rel in [os.path.join("assets", "logo.png"), os.path.join("Assets", "logo.png"),
                os.path.join("assets", "logo.jpg"), os.path.join("logo.png")]:
        p = os.path.join(base, rel)
        if os.path.exists(p):
            return p
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        p2 = os.path.join(sys._MEIPASS, "assets", "logo.png")
        if os.path.exists(p2):
            return p2
    return None


def verifier_mdp(mdp_saisi):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT valeur FROM parametres WHERE cle='admin_password'")
        row = cur.fetchone()
        if not row or not row[0]:
            cur.execute(
                "INSERT INTO parametres (cle, valeur) VALUES ('admin_password', ?) "
                "ON CONFLICT(cle) DO UPDATE SET valeur=excluded.valeur",
                (MOT_DE_PASSE_DEFAUT,)
            )
            conn.commit()
            return mdp_saisi == MOT_DE_PASSE_DEFAUT
        return mdp_saisi == row[0]
    finally:
        conn.close()


class LoginApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("BULLETIN PRO - Connexion Admin")
        self.geometry("440x430")
        self.resizable(False, False)
        self.configure(fg_color=COULEUR_FOND)
        self.authentifie = False
        self.tentatives = 0

        try:
            from PIL import Image
            logo_path = trouver_logo()
            if logo_path:
                img = Image.open(logo_path).convert("RGBA")
                img.thumbnail((110, 110))
                canvas = Image.new("RGBA", (110, 110), (244, 241, 230, 255))
                x = (110 - img.size[0]) // 2
                y = (110 - img.size[1]) // 2
                canvas.paste(img, (x, y), img)
                self._logo_img = ctk.CTkImage(light_image=canvas, dark_image=canvas, size=(110, 110))
                ctk.CTkLabel(self, image=self._logo_img, text="").pack(pady=(25, 5))
        except Exception:
            pass

        ctk.CTkLabel(self, text="BULLETIN PRO", font=ctk.CTkFont(size=24, weight="bold"), text_color=COULEUR_VERT_FONCE).pack()
        ctk.CTkLabel(self, text="College Notre Dame de la Sagesse", text_color="#5A5A5A").pack(pady=(0, 12))

        self.ent_mdp = ctk.CTkEntry(self, placeholder_text="Mot de passe", show="*", width=260, height=42, justify="center", font=ctk.CTkFont(size=15))
        self.ent_mdp.pack(pady=5)
        self.ent_mdp.bind("<Return>", lambda e: self.tenter())
        self.ent_mdp.focus()

        ctk.CTkButton(self, text="Se connecter", command=self.tenter, height=42, width=260, fg_color=COULEUR_VERT_FONCE, hover_color=COULEUR_VERT, font=ctk.CTkFont(size=14, weight="bold")).pack(pady=12)
        self.lbl_info = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12))
        self.lbl_info.pack()

    def tenter(self):
        if verifier_mdp(self.ent_mdp.get()):
            self.authentifie = True
            self.destroy()
        else:
            self.tentatives += 1
            restants = 3 - self.tentatives
            if restants <= 0:
                messagebox.showerror("Acces refuse", "Trop de tentatives. Fermeture.")
                self.destroy()
            else:
                self.lbl_info.configure(text="Mot de passe incorrect (" + str(restants) + " essai(s) restants)", text_color="red")
                self.ent_mdp.delete(0, "end")


if __name__ == "__main__":
    init_db()
    login = LoginApp()
    login.mainloop()
    if login.authentifie:
        from ui.admin_app import AdminApp
        app = AdminApp()
        app.mainloop()