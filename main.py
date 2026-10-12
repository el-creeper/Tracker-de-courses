import sys
import os

# Définir le bon chemin de travail
if getattr(sys, 'frozen', False):
    # Si on est dans un .exe, on utilise getattr pour éviter l'erreur Pylance
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
else:
    # Si on est en mode normal
    base_path = os.path.dirname(os.path.abspath(__file__))

sys.path.append(base_path)

from ui_main import MainWindow

if __name__ == "__main__":
    app = MainWindow()
    app.run()