import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# Import absolu pour PyInstaller
from database import DatabaseManager

class MainWindow:
    def __init__(self):
        try:
            self.root = tk.Tk()
            self.root.title("Suivi de Courses")
            self.root.geometry("800x600")
            
            # Initialisation de la BDD
            self.db = DatabaseManager()
            
            # Vérifier si la DB est accessible (pas besoin de cursor ici)
            db_path = getattr(self.db, "db_path", None)
            get_db_path = getattr(self.db, "get_db_path", None)
            if db_path is None and callable(get_db_path):
                db_path = get_db_path()

            if db_path is not None:
                if isinstance(db_path, (str, os.PathLike)):
                    db_path_str = os.fspath(db_path)
                else:
                    db_path_str = None

                if db_path_str and not os.path.exists(db_path_str):
                    messagebox.showwarning("Info", "La base de données sera créée au premier lancement.")

           
            
            self.setup_ui()
        except Exception as e:
            print(f"Erreur d'initialisation : {e}")
            messagebox.showerror("Erreur", f"L'application ne peut pas démarrer.\nDétails : {str(e)}")

    def setup_ui(self):
        # --- Cadre d'entrée de données ---
        input_frame = ttk.LabelFrame(self.root, text="Ajouter une course", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(input_frame, text="Article :").grid(row=0, column=0, sticky="w")
        self.entry_article = ttk.Entry(input_frame, width=20)
        self.entry_article.grid(row=0, column=1, padx=5)

        ttk.Label(input_frame, text="Catégorie :").grid(row=0, column=2, sticky="w")
        self.entry_cat = ttk.Entry(input_frame, width=15)
        self.entry_cat.grid(row=0, column=3, padx=5)

        ttk.Label(input_frame, text="Prix (€) :").grid(row=0, column=4, sticky="w")
        self.entry_prix = ttk.Entry(input_frame, width=10)
        self.entry_prix.grid(row=0, column=5, padx=5)

        ttk.Label(input_frame, text="Magasin :").grid(row=0, column=6, sticky="w")
        self.entry_mag = ttk.Entry(input_frame, width=20)
        self.entry_mag.grid(row=0, column=7, padx=5)

        btn_add = ttk.Button(input_frame, text="Ajouter", command=self.add_course)
        btn_add.grid(row=0, column=8, padx=10)

        # --- Cadre d'affichage du Budget ---
        stats_frame = ttk.LabelFrame(self.root, text="Budget & Statistiques", padding=10)
        stats_frame.pack(fill="x", padx=10, pady=5)

        self.lbl_budget_total = ttk.Label(stats_frame, text="Total : 0.00 €", font=("Arial", 12, "bold"))
        self.lbl_budget_total.grid(row=0, column=0, sticky="w")

        # --- Cadre de la liste des courses ---
        list_frame = ttk.LabelFrame(self.root, text="Dernières Courses", padding=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("Article", "Catégorie", "Prix", "Magasin", "Date")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Bouton Supprimer (Ajouté ici) ---
        btn_delete = ttk.Button(list_frame, text="Supprimer Sélectionnée", command=self.delete_selected)
        btn_delete.pack(pady=5)
        
        btn_refresh = ttk.Button(list_frame, text="🔄 Rafraîchir la page", command=self.refresh_list)
        btn_refresh.pack(pady=5)
        
        btn_edit_cat = ttk.Button(list_frame, text="✏️ Modifier Catégorie", command=self.edit_category)
        btn_edit_cat.pack(pady=5)
        
        self.refresh_list()

    def add_course(self):
        article = self.entry_article.get()
        cat = self.entry_cat.get()
        try:
            prix = float(self.entry_prix.get())
        except ValueError:
            messagebox.showerror("Erreur", "Le prix doit être un nombre.")
            return
        
        magasin = self.entry_mag.get()

        if not article or prix <= 0:
            messagebox.showwarning("Attention", "Article et Prix requis.")
            return

        # Ajout à la base de données
        if self.db.add_item(article, cat, prix, magasin):
            self.update_budget_display()
            self.refresh_list()  # ⚠️ IMPORTANT : Rafraîchir la liste
            
            # Reset champs
            self.entry_article.delete(0, tk.END)
            self.entry_cat.delete(0, tk.END)
            self.entry_prix.delete(0, tk.END)
            self.entry_mag.delete(0, tk.END)
            
            messagebox.showinfo("Succès", "Article ajouté !")
        else:
            messagebox.showerror("Erreur", "Impossible d'ajouter l'article.")

    def delete_selected(self):
        """Supprime l'article sélectionné dans la liste"""
        selection = self.tree.selection()
        
        if not selection:
            messagebox.showwarning("Aucun choix", "Sélectionnez un article à supprimer.")
            return
        
        # ✅ CORRECTION 2 : Récupérer les données de la ligne sélectionnée correctement
        selected_item_values = self.tree.item(selection[0])["values"]
        
        if len(selected_item_values) < 5:
            messagebox.showerror("Erreur", "Données invalides pour suppression.")
            return
        
        # Les valeurs sont : (Article, Catégorie, Prix, Magasin, Date)
        article_name = selected_item_values[0]
        
        # Trouver l'ID de cet article dans la base de données
        items = self.db.get_all_items()
        item_id_to_delete = None
        
        for row in items:
            # row contient : id, article, categorie, prix, magasin, date
            if row[1] == article_name:  # On compare par l'article (colonne 1)
                item_id_to_delete = row[0]  # L'ID est la première colonne
                break
        
        if not item_id_to_delete:
            messagebox.showerror("Erreur", "Impossible de trouver l'article à supprimer.")
            return

        try:
            # Supprimer depuis la table items
            self.db.cursor.execute("DELETE FROM items WHERE id = ?", (item_id_to_delete,))
            
            # Supprimer aussi depuis price_history pour garder la cohérence
            self.db.cursor.execute("DELETE FROM price_history WHERE article = ?", (article_name,))
            
            self.db.conn.commit()
            
            messagebox.showinfo("Succès", "Article supprimé !")
            
            # Rafraîchir l'affichage et le budget
            self.update_budget_display()
            self.refresh_list()
        except Exception as e:
            print(f"Erreur suppression : {e}")
            self.db.conn.rollback()
            messagebox.showerror("Erreur", f"Impossible de supprimer l'article.\nDétails : {str(e)}")

    def update_budget_display(self):
        total = self.db.get_total_budget()
        
        # On récupère le compteur via la DB, pas via self.cursor qui n'existe pas ici
        count = 0
        try:
            items = self.db.get_all_items()
            count = len(items)
        except Exception as e:
            print(f"Erreur comptage : {e}")
        
        self.lbl_budget_total.config(text=f"Total : {total:.2f} € ({count} articles)")
        
    def edit_category(self):
        """Modifie les catégories des articles sélectionnés"""
        selection = self.tree.selection()
        
        if not selection:
            messagebox.showwarning("Aucun choix", "Sélectionnez un ou plusieurs articles à modifier.")
            return
        
        # Récupérer les noms des articles sélectionnés
        items_to_edit = []
        for item in selection:
            values = self.tree.item(item)["values"]
            if len(values) >= 2:
                items_to_edit.append(values[0]) # On ne garde que le nom de l'article
        
        # Créer une fenêtre de dialogue
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Modifier les Catégories")
        edit_window.geometry("450x350")
        
        # Frame pour la liste
        list_frame_edit = ttk.LabelFrame(edit_window, text="Articles sélectionnés", padding=10)
        list_frame_edit.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview pour afficher les articles à modifier
        columns_edit = ("Article", "Catégorie Actuelle")
        tree_edit = ttk.Treeview(list_frame_edit, columns=columns_edit, show="headings", height=6)
        
        for col in columns_edit:
            tree_edit.heading(col, text=col)
            tree_edit.column(col, width=200)
        
        tree_edit.pack(side="left", fill="both", expand=True)
        
        scrollbar_edit = ttk.Scrollbar(list_frame_edit, orient="vertical", command=tree_edit.yview)
        tree_edit.configure(yscrollcommand=scrollbar_edit.set)
        scrollbar_edit.pack(side="right", fill="y")
        
        # Remplir la liste
        for name in items_to_edit:
            # On cherche la catégorie actuelle dans la DB pour l'afficher
            self.db.cursor.execute("SELECT categorie FROM items WHERE article = ?", (name,))
            res = self.db.cursor.fetchone()
            current_cat = res[0] if res else "Inconnue"
            tree_edit.insert("", "end", values=(name, current_cat))

        # Frame pour la saisie
        frame_input = ttk.Frame(edit_window, padding=10)
        frame_input.pack(fill="x")

        ttk.Label(frame_input, text="Nouvelle Catégorie :").grid(row=0, column=0, sticky="w")
        entry_new_cat = ttk.Entry(frame_input, width=30)
        entry_new_cat.grid(row=0, column=1, padx=5, pady=5)
        
        # Bouton pour valider la modification de la ligne sélectionnée
        def update_selected_item():
            selected_row = tree_edit.selection()
            if not selected_row:
                messagebox.showwarning("Attention", "Sélectionnez une ligne dans la liste.")
                return
            
            article_name = tree_edit.item(selected_row[0])["values"][0]
            new_cat = entry_new_cat.get().strip()
            
            if not new_cat:
                messagebox.showwarning("Attention", "La catégorie ne peut pas être vide.")
                return
            
            try:
                # Mise à jour dans la BDD
                self.db.cursor.execute('''
                    UPDATE items SET categorie = ? WHERE article = ?
                ''', (new_cat, article_name))
                
                # Mise à jour de l'historique (optionnel, mais propre)
                self.db.cursor.execute('''
                    UPDATE price_history SET article = ? WHERE article = ?
                ''', (article_name, new_cat))
                
                self.db.conn.commit()
                
                # Mise à jour visuelle
                tree_edit.item(selected_row[0], values=(article_name, new_cat))
                entry_new_cat.delete(0, tk.END)
                messagebox.showinfo("Succès", f"Catégorie mise à jour pour : {article_name}")
                self.refresh_list()
            except Exception as e:
                self.db.conn.rollback()
                messagebox.showerror("Erreur", f"Échec : {str(e)}")

        btn_save = ttk.Button(frame_input, text="Enregistrer la sélection", command=update_selected_item)
        btn_save.grid(row=0, column=2, padx=5)

        btn_cancel = ttk.Button(edit_window, text="Annuler", command=edit_window.destroy)
        btn_cancel.pack(pady=5)


    def refresh_list(self):
        """Rafraîchit la liste des courses et met à jour le budget"""
        # Effacer la liste actuelle
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Récupérer les dernières entrées
        items = self.db.get_all_items()
        
        for row in items:
            # row contient : id, article, categorie, prix, magasin, date
            self.tree.insert("", "end", values=(row[1], row[2], f"{row[3]:.2f}", row[4], row[5]))

        self.update_budget_display()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MainWindow()
    app.run()
