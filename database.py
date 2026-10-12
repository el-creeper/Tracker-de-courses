import sqlite3
import os
import sys
import shutil

def get_db_path():
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
        bundle_path = getattr(sys, '_MEIPASS', application_path)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
        bundle_path = application_path
    
    DATA_DIR = "data"
    data_path = os.path.join(application_path, DATA_DIR)
    db_file = os.path.join(data_path, "courses_data.db")
    
    os.makedirs(data_path, exist_ok=True)
    
    bundled_db = os.path.join(bundle_path, DATA_DIR, "courses_data.db")
    if not os.path.exists(db_file) and os.path.exists(bundled_db) and db_file != bundled_db:
        try:
            shutil.copy2(bundled_db, db_file)
        except Exception as e:
            print(f"Erreur lors de la copie de la BDD : {e}")

    return db_file

class DatabaseManager:
    def __init__(self):
        self.db_path = get_db_path()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
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
            
            self.cursor.execute("PRAGMA table_info(items)")
            columns = [col[1] for col in self.cursor.fetchall()]
            if 'quantite' not in columns:
                self.cursor.execute("ALTER TABLE items ADD COLUMN quantite REAL DEFAULT 1.0")
            
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
            self.conn.rollback()
            return False

    def update_quantity(self, item_id, new_quantity):
        try:
            self.cursor.execute("UPDATE items SET quantite = ? WHERE id = ?", (new_quantity, item_id))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            return False
        
    def rename_article_global(self, old_name, new_name):
        try:
            self.cursor.execute("UPDATE items SET article = ? WHERE article = ?", (new_name, old_name))
            self.cursor.execute("UPDATE price_history SET article = ? WHERE article = ?", (new_name, old_name))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            return False

    def get_summary_by_category(self):
        self.cursor.execute('''
            SELECT categorie, SUM(prix * quantite), SUM(quantite) 
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
            self.cursor.execute("SELECT SUM(prix * quantite) FROM items")
            result = self.cursor.fetchone()[0]
            return 0.0 if result is None else float(result)
        except Exception:
            return 0.0

    def get_all_items(self):
        try:
            self.cursor.execute("SELECT * FROM items ORDER BY date_achat DESC, id DESC")
            return self.cursor.fetchall()
        except Exception:
            return []

    def get_price_history(self, article_name):
        try:
            self.cursor.execute('''
                SELECT prix, date_achat FROM price_history 
                WHERE article = ? ORDER BY date_achat ASC
            ''', (article_name,))
            return self.cursor.fetchall()
        except Exception:
            return []

    def get_categories(self):
        try:
            self.cursor.execute("SELECT DISTINCT categorie FROM items WHERE categorie IS NOT NULL AND categorie != '' ORDER BY categorie")
            return [row[0] for row in self.cursor.fetchall()]
        except Exception:
            return []

    def get_advanced_stats(self, period="Mois", category="Toutes"):
        format_map = {
            "Jour": "%Y-%m-%d",
            "Semaine": "%Y-S%W",
            "Mois": "%Y-%m"
        }
        date_format = format_map.get(period, "%Y-%m")
        
        query = f"SELECT strftime('{date_format}', date_achat) as period, SUM(prix * quantite) FROM items"
        params = []
        
        if category and category != "Toutes":
            query += " WHERE categorie = ?"
            params.append(category)
            
        query += " GROUP BY period ORDER BY period ASC"
        
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erreur stats : {e}")
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
        except Exception:
            self.conn.rollback()
            return False

    # --- NOUVELLES MÉTHODES POUR AUTOCOMPLÉTION ET COMPARATEUR ---

    def get_unique_articles(self):
        """Récupère la liste de tous les articles uniques pour l'autocomplétion"""
        try:
            self.cursor.execute("SELECT DISTINCT article FROM items WHERE article IS NOT NULL AND article != '' ORDER BY article")
            return [row[0] for row in self.cursor.fetchall()]
        except Exception:
            return []

    def get_article_defaults(self, article_name):
        """Récupère la catégorie, le dernier prix et le dernier magasin utilisés pour un article"""
        try:
            self.cursor.execute('''
                SELECT categorie, prix, magasin 
                FROM items 
                WHERE article = ? 
                ORDER BY date_achat DESC LIMIT 1
            ''', (article_name,))
            return self.cursor.fetchone()
        except Exception:
            return None

    def get_store_comparison(self, article_name):
        """Récupère le prix moyen d'un article en fonction du magasin"""
        try:
            self.cursor.execute('''
                SELECT magasin, AVG(prix) 
                FROM items 
                WHERE article = ? AND magasin IS NOT NULL AND magasin != ''
                GROUP BY magasin
                ORDER BY AVG(prix) ASC
            ''', (article_name,))
            return self.cursor.fetchall()
        except Exception:
            return []

    def close(self):
        if self.conn:
            self.conn.close()