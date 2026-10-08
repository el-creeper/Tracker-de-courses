import sqlite3
import os
import sys

# Fonction pour trouver le bon chemin de l'exécutable
def get_db_path():
    if getattr(sys, 'frozen', False):
        # On est dans un .exe -> on cherche par rapport au fichier exe
        application_path = os.path.dirname(sys.executable)
    else:
        # Développement local -> dossier actuel
        application_path = os.getcwd()
    
    DATA_DIR = "data"
    DB_FILE = f"{os.path.join(application_path, DATA_DIR)}/courses_data.db"
    
    # Créer le dossier data si n'existe pas
    if not os.path.exists(os.path.join(application_path, DATA_DIR)):
        try:
            os.makedirs(os.path.join(application_path, DATA_DIR))
        except PermissionError as e:
            print(f"Erreur création dossier : {e}")
    
    return DB_FILE

DB_FILE = get_db_path()

class DatabaseManager:
    def __init__(self):
        self.db_file = DB_FILE
        
        # Création du dossier data si besoin (pour le développement local)
        if not os.path.exists(os.path.dirname(DB_FILE)):
            try:
                os.makedirs(os.path.dirname(DB_FILE))
            except PermissionError as e:
                print(f"Impossible de créer le dossier data : {e}")

        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.cursor = self.conn.cursor()  # ✅ Le curseur est ici
        
        # Création des tables si elles n'existent pas
        self._create_tables()

    def _create_tables(self):
        """Crée les tables si elles n'existent pas"""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article TEXT NOT NULL,
                    categorie TEXT,
                    prix REAL,
                    magasin TEXT,
                    date_achat TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article TEXT,
                    prix REAL,
                    date_achat TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()
        except Exception as e:
            print(f"Erreur création tables : {e}")

    def add_item(self, article, categorie, prix, magasin):
        """Ajoute un article et son historique"""
        try:
            # Insertion dans la table principale
            self.cursor.execute('''
                INSERT INTO items (article, categorie, prix, magasin) 
                VALUES (?, ?, ?, ?)
            ''', (article, categorie, prix, magasin))

            # Insertion dans l'historique pour les fluctuations
            self.cursor.execute('''
                INSERT INTO price_history (article, prix) VALUES (?, ?)
            ''', (article, prix))

            self.conn.commit()  # ⚠️ IMPORTANT : Sauvegarde immédiate
            return True
        except Exception as e:
            print(f"Erreur ajout item : {e}")
            self.conn.rollback()
            return False

    def get_total_budget(self):
        """Récupère le total dépensé"""
        try:
            self.cursor.execute("SELECT SUM(prix) FROM items")
            result = self.cursor.fetchone()[0]
            return 0.0 if result is None else float(result)
        except Exception as e:
            print(f"Erreur budget : {e}")
            return 0.0

    def get_all_items(self):
        """Récupère TOUS les articles pour l'affichage"""
        try:
            self.cursor.execute("SELECT * FROM items ORDER BY id DESC")
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erreur lecture items : {e}")
            return []

    def close(self):
        """Ferme proprement la connexion"""
        if self.conn:
            self.conn.close()


def delete_item(self, item_id):
    """Supprime un article par son ID"""
    try:
        # Supprimer depuis la table items
        self.cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
        
        # Récupérer l'article pour aussi le supprimer de price_history
        self.cursor.execute("SELECT article FROM items WHERE id = ?", (item_id,))
        result = self.cursor.fetchone()
        
        if result:
            article_name = result[0]
            # Supprimer depuis price_history
            self.cursor.execute("DELETE FROM price_history WHERE article = ?", (article_name,))
            
            self.conn.commit()
            return True
        else:
            self.conn.rollback()
            return False
            
    except Exception as e:
        print(f"Erreur suppression : {e}")
        self.conn.rollback()
        return False

def get_item_by_id(self, item_id):
    """Récupère un article par son ID"""
    try:
        self.cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
        return self.cursor.fetchone()
    except Exception as e:
        print(f"Erreur lecture : {e}")
        return None
