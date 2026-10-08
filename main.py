import sys
import os

# ✅ AJOUTE CES 4 LIGNES AU TOUT DÉBUT DU FICHIER
if getattr(sys, 'frozen', False):
    # Si on est dans un .exe
    os.path.dirname(sys.executable)
else:
    # Si on est en mode normal
    os.getcwd()

# Ajoute le dossier actuel au chemin de recherche de Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Maintenant, on peut importer ui_main sans erreur
from ui_main import MainWindow

if __name__ == "__main__":
    app = MainWindow()
    app.run()
