import sys
import os
from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.button import MDRaisedButton, MDRectangleFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.scrollview import MDScrollView

# Import des modules existants
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from database.database import get_db_connection, init_db
from core.calculator import calculer_moyennes_classe

class EcranConnexion(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        layout = MDBoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # En-tête
        title = MDLabel(
            text="SAPIENTIA MOBILE",
            halign="center",
            font_style="H4",
            theme_text_color="Custom",
            text_color=(0.07, 0.24, 0.15, 1)  # Vert foncé #123F26
        )
        subtitle = MDLabel(
            text="Collège Bilingue Notre Dame de la Sagesse",
            halign="center",
            font_style="Subtitle1"
        )
        
        # Champs de saisie
        self.code_input = MDTextField(
            hint_text="Code PIN Enseignant / Admin",
            password=True,
            icon_right="key",
            pos_hint={'center_x': 0.5},
            size_hint_x=0.8
        )
        
        # Boutons d'accès
        btn_prof = MDRaisedButton(
            text="ESPACE ENSEIGNANT",
            pos_hint={'center_x': 0.5},
            size_hint_x=0.8,
            md_bg_color=(0.11, 0.41, 0.22, 1),
            on_release=self.connexion_prof
        )
        
        btn_admin = MDRectangleFlatButton(
            text="ESPACE ADMINISTRATION",
            pos_hint={'center_x': 0.5},
            size_hint_x=0.8,
            on_release=self.connexion_admin
        )

        layout.add_widget(title)
        layout.add_widget(subtitle)
        layout.add_widget(self.code_input)
        layout.add_widget(btn_prof)
        layout.add_widget(btn_admin)
        
        self.add_widget(layout)

    def connexion_prof(self, instance):
        pin = self.code_input.text.strip()
        if not pin:
            self.afficher_dialogue("Erreur", "Veuillez saisir votre code PIN.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nom_prof, matiere_nom, classe_nom FROM affectations_prof WHERE pin = ?", (pin,))
        res = cursor.fetchone()
        conn.close()
        
        if res:
            app = MDApp.get_running_app()
            app.prof_data = dict(res)
            self.manager.current = "prof_screen"
        else:
            self.afficher_dialogue("Échec", "Code PIN enseignant incorrect.")

    def connexion_admin(self, instance):
        pin = self.code_input.text.strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT valeur FROM parametres WHERE cle = 'admin_password'")
        pwd_row = cursor.fetchone()
        conn.close()
        
        admin_pwd = pwd_row['valeur'] if pwd_row else "admin123"
        if pin == admin_pwd:
            self.manager.current = "admin_screen"
        else:
            self.afficher_dialogue("Échec", "Mot de passe administrateur incorrect.")

    def afficher_dialogue(self, titre, me_text):
        dialog = MDDialog(title=titre, text=me_text, size_hint=(0.8, None))
        dialog.open()


class EcranProfesseur(MDScreen):
    def on_pre_enter(self, *args):
        app = MDApp.get_running_app()
        prof_info = getattr(app, 'prof_data', {})
        self.toolbar.title = f"Prof: {prof_info.get('nom_prof', '')} ({prof_info.get('classe_nom', '')})"
        self.charger_eleves(prof_info.get('classe_nom', ''))

    def __init__(self, **kw):
        super().__init__(**kw)
        layout = MDBoxLayout(orientation='vertical')
        
        self.toolbar = MDTopAppBar(
            title="Espace Enseignant",
            left_action_items=[["arrow-left", lambda x: self.retour()]],
            md_bg_color=(0.11, 0.41, 0.22, 1)
        )
        
        scroll = MDScrollView()
        self.liste_eleves = MDList()
        scroll.add_widget(self.liste_eleves)
        
        layout.add_widget(self.toolbar)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def charger_eleves(self, nom_classe):
        self.liste_eleves.clear_widgets()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.id, e.nom, e.prenom, e.matricule 
            FROM eleves e
            JOIN classes c ON e.classe_id = c.id
            WHERE c.nom = ?
            ORDER BY e.nom, e.prenom
        """, (nom_classe,))
        eleves = cursor.fetchall()
        conn.close()
        
        for el in eleves:
            nom_complet = f"{el['nom']} {el['prenom']}"
            item = OneLineListItem(
                text=f"{nom_complet} ({el['matricule']})",
                on_release=lambda x, eleve_id=el['id'], name=nom_complet: self.saisir_note(eleve_id, name)
            )
            self.liste_eleves.add_widget(item)

    def saisir_note(self, eleve_id, nom_complet):
        # Dialogue rapide pour saisir la note d'un élève
        content = MDBoxLayout(orientation='vertical', size_hint_y=None, height="80dp")
        note_field = MDTextField(hint_text="Note sur 20", input_filter="float")
        content.add_widget(note_field)
        
        def enregistrer(instance):
            valeur = note_field.text.strip()
            if valeur:
                try:
                    val = float(valeur)
                    if 0 <= val <= 20:
                        app = MDApp.get_running_app()
                        prof = app.prof_data
                        
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        # Récupérer l'ID de la matière
                        cursor.execute("SELECT id FROM matieres WHERE nom = ?", (prof['matiere_nom'],))
                        mat = cursor.fetchone()
                        if mat:
                            cursor.execute("""
                                INSERT INTO notes (eleve_id, matiere_id, trimestre, note)
                                VALUES (?, ?, 1, ?)
                                ON CONFLICT(eleve_id, matiere_id, trimestre) DO UPDATE SET note=excluded.note
                            """, (eleve_id, mat['id'], val))
                            conn.commit()
                        conn.close()
                        dialog.dismiss()
                except ValueError:
                    pass

        dialog = MDDialog(
            title=f"Note de {nom_complet}",
            type="custom",
            content_cls=content,
            buttons=[
                MDRaisedButton(text="ENREGISTRER", on_release=enregistrer)
            ]
        )
        dialog.open()

    def retour(self):
        self.manager.current = "login_screen"


class EcranAdmin(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        layout = MDBoxLayout(orientation='vertical')
        
        toolbar = MDTopAppBar(
            title="Administration Sapientia",
            left_action_items=[["arrow-left", lambda x: self.retour()]],
            md_bg_color=(0.07, 0.24, 0.15, 1)
        )
        
        lbl = MDLabel(
            text="Panneau Administrateur Mobile\n(Consultation & Validation)",
            halign="center"
        )
        
        layout.add_widget(toolbar)
        layout.add_widget(lbl)
        self.add_widget(layout)

    def retour(self):
        self.manager.current = "login_screen"


class SapientiaApp(MDApp):
    prof_data = {}

    def build(self):
        init_db()
        self.theme_cls.primary_palette = "Green"
        self.theme_cls.primary_hue = "800"
        
        sm = MDScreenManager()
        sm.add_widget(EcranConnexion(name="login_screen"))
        sm.add_widget(EcranProfesseur(name="prof_screen"))
        sm.add_widget(EcranAdmin(name="admin_screen"))
        return sm


if __name__ == "__main__":
    SapientiaApp().run()