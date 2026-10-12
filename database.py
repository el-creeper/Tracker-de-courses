import sqlite3
import os
import sys
import shutil

def get_db_path():
    # Déterminer le dossier où se trouve l'exécutable ou le script
    if getattr(sys, 'frozen', False):
        # Dossier de l'exécutable final
        application_path = os.path.dirname(sys.executable)
        # Utiliser getattr pour éviter l'erreur Pylance sur sys._MEIPASS
        bundle_path = getattr(sys, '_MEIPASS', application_path)
    else:
        # Mode développement
        application_path = os.path.dirname(os.path.abspath(__file__))
        bundle_path = application_path
    
    DATA_DIR = "data"
    data_path = os.path.join(application_path, DATA_DIR)
    db_file = os.path.join(data_path, "courses_data.db")
    
    # Créer le dossier data à côté de l'exécutable s'il n'existe pas
    os.makedirs(data_path, exist_ok=True)
    
    # Si la base de données n'existe pas encore à côté de l'exe, 
    # mais qu'elle a été embarquée par PyInstaller, on la copie.
    bundled_db = os.path.join(bundle_path, DATA_DIR, "courses_data.db")
    if not os.path.exists(db_file) and os.path.exists(bundled_db) and db_file != bundled_db:
        try:
            shutil.copy2(bundled_db, db_file)
        except Exception as e:
            print(f"Erreur lors de la copie de la BDD initiale : {e}")

    return db_file

class DatabaseManager:
    def __init__(self):
        self.db_path = get_db_path()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Crée les tables et met à jour le schéma si nécessaire"""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article TEXT NOT NULL,
                    categorie TEXT,
                    prix REAL,
                    magasin TEXT,
                    date_achat TEXT DEFAULT CURRENT_TIMESTAMP,
                    quantite REAL DEFAULT 1.0
                )
            ''')
            
            # Si la table existait AVANT que tu ajoutes "quantite", ça va planter.
            # On tente d'ajouter la colonne. Si elle existe déjà, ça lève une erreur qu'on ignore.
            try:
                self.cursor.execute("ALTER TABLE items ADD COLUMN quantite REAL DEFAULT 1.0")
            except sqlite3.OperationalError:
                pass # La colonne existe déjà, tout va bien.
            
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

    def add_item(self, article, categorie, prix, magasin, quantite=1.0):
        try:
            self.cursor.execute('''
                INSERT INTO items (article, categorie, prix, magasin, quantite) 
                VALUES (?, ?, ?, ?, ?)
            ''', (article, categorie, prix, magasin, quantite))

            self.cursor.execute('''
                INSERT INTO price_history (article, prix) VALUES (?, ?)
            ''', (article, prix))

            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erreur ajout : {e}")
            self.conn.rollback()
            return False
        
    def rename_article_global(self, old_name, new_name):
        try:
            self.cursor.execute("UPDATE items SET article = ? WHERE article = ?", (new_name, old_name))
            self.cursor.execute("UPDATE price_history SET article = ? WHERE article = ?", (new_name, old_name))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erreur renomination : {e}")
            self.conn.rollback()
            return False

    def get_summary_by_category(self):
        self.cursor.execute('''
            SELECT categorie, SUM(prix), SUM(quantite) 
            FROM items GROUP BY categorie
        ''')
        return self.cursor.fetchall()
    
    def get_summary_by_article(self):
        self.cursor.execute('''
            SELECT article, SUM(quantite) 
            FROM items GROUP BY article
        ''')
        return self.cursor.fetchall()

    def get_total_budget(self):
        try:
            self.cursor.execute("SELECT SUM(prix) FROM items")
            result = self.cursor.fetchone()[0]
            return 0.0 if result is None else float(result)
        except Exception as e:
            print(f"Erreur budget : {e}")
            return 0.0

    def get_all_items(self):
        try:
            self.cursor.execute("SELECT * FROM items ORDER BY id DESC")
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erreur lecture items : {e}")
            return []

    def get_price_history(self, article_name):
        try:
            self.cursor.execute('''
                SELECT prix, date_achat FROM price_history 
                WHERE article = ? ORDER BY date_achat ASC
            ''', (article_name,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erreur historique : {e}")
            return []

    def delete_item(self, item_id):
        try:
            self.cursor.execute("SELECT article FROM items WHERE id = ?", (item_id,))
            result = self.cursor.fetchone()
            
            if result:
                article_name = result[0]
                self.cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
                self.cursor.execute("DELETE FROM price_history WHERE article = ?", (article_name,))
                self.conn.commit()
                return True
            return False
        except Exception as e:
            print(f"Erreur suppression : {e}")
            self.conn.rollback()
            return False

    def close(self):
        if self.conn:
            self.conn.close()