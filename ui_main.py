import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sys
import os
from datetime import datetime
from database import DatabaseManager
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🛒 Suivi de Courses")
        self.root.geometry("850x650")
        
        # Appliquer un thème plus moderne
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
            
        style.configure("Treeview", rowheight=25, font=('Segoe UI', 10))
        style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))

        try:
            self.db = DatabaseManager()
            self.setup_ui()
        except Exception as e:
            messagebox.showerror("Erreur Fatale", f"Impossible d'initialiser la base de données.\n{str(e)}")
            self.root.destroy()

    def setup_ui(self):
        # --- Cadre d'entrée de données ---
        input_frame = ttk.LabelFrame(self.root, text="➕ Ajouter un article", padding=15)
        input_frame.pack(fill="x", padx=15, pady=10)

        # Ligne 1
        ttk.Label(input_frame, text="Article :").grid(row=0, column=0, sticky="w", pady=5)
        self.entry_article = ttk.Entry(input_frame, width=25)
        self.entry_article.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(input_frame, text="Catégorie :").grid(row=0, column=2, sticky="w", pady=5)
        self.entry_cat = ttk.Entry(input_frame, width=20)
        self.entry_cat.grid(row=0, column=3, padx=10, pady=5)

        ttk.Label(input_frame, text="Prix (€) :").grid(row=0, column=4, sticky="w", pady=5)
        self.entry_prix = ttk.Entry(input_frame, width=10)
        self.entry_prix.grid(row=0, column=5, padx=10, pady=5)

        # Ligne 2
        ttk.Label(input_frame, text="Quantité :").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_quantite = ttk.Entry(input_frame, width=10)
        self.entry_quantite.insert(0, "1")
        self.entry_quantite.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        ttk.Label(input_frame, text="Magasin :").grid(row=1, column=2, sticky="w", pady=5)
        self.entry_mag = ttk.Entry(input_frame, width=20)
        self.entry_mag.grid(row=1, column=3, padx=10, pady=5)

        btn_add = ttk.Button(input_frame, text="✔️ Ajouter", command=self.add_course)
        btn_add.grid(row=1, column=4, columnspan=2, padx=10, pady=5, sticky="we")

        # --- Cadre d'affichage du Budget ---
        stats_frame = ttk.Frame(self.root, padding=5)
        stats_frame.pack(fill="x", padx=15)

        self.lbl_budget_total = ttk.Label(stats_frame, text="Total : 0.00 €", font=("Segoe UI", 14, "bold"), foreground="#2C3E50")
        self.lbl_budget_total.pack(side="left")

        # --- Cadre de la liste des courses ---
        list_frame = ttk.LabelFrame(self.root, text="📋 Historique", padding=10)
        list_frame.pack(fill="both", expand=True, padx=15, pady=5)

        columns = ("Article", "Catégorie", "Prix", "Qté", "Magasin", "Date")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        widths = {"Article": 150, "Catégorie": 100, "Prix": 80, "Qté": 60, "Magasin": 120, "Date": 150}
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths[col], anchor="center")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self.on_item_double_click)

        # --- Barre de Boutons en bas ---
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill="x", pady=5)

        ttk.Button(btn_frame, text="❌ Supprimer", command=self.delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✏️ Modif. Catégorie", command=self.edit_category).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 Renommer Global", command=self.rename_global).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="📊 Bilan Catégorie", command=self.show_bilan_cat).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="📦 Bilan Article", command=self.show_bilan_art).pack(side=tk.RIGHT, padx=5)

        self.refresh_list()

    def add_course(self):
        article = self.entry_article.get().strip()
        cat = self.entry_cat.get().strip()
        magasin = self.entry_mag.get().strip()
        
        try:
            prix = float(self.entry_prix.get().replace(',', '.'))
            quantite = float(self.entry_quantite.get().replace(',', '.'))
        except ValueError:
            messagebox.showerror("Erreur", "Le prix et la quantité doivent être des nombres valides.")
            return

        if not article or prix <= 0:
            messagebox.showwarning("Attention", "Le nom de l'article et un prix positif sont requis.")
            return

        if self.db.add_item(article, cat, prix, magasin, quantite):
            self.refresh_list()
            self.entry_article.delete(0, tk.END)
            self.entry_cat.delete(0, tk.END)
            self.entry_prix.delete(0, tk.END)
            self.entry_mag.delete(0, tk.END)
            self.entry_quantite.delete(0, tk.END)
            self.entry_quantite.insert(0, "1")
        else:
            messagebox.showerror("Erreur", "Impossible d'ajouter l'article.")

    def delete_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Aucun choix", "Sélectionnez un article à supprimer dans la liste.")
            return
        
        # Grâce au paramètre iid=row[0], on récupère directement l'ID de la BDD !
        item_id = int(selection[0])
        
        if messagebox.askyesno("Confirmation", "Êtes-vous sûr de vouloir supprimer cet article ?"):
            if self.db.delete_item(item_id):
                self.refresh_list()
            else:
                messagebox.showerror("Erreur", "Échec de la suppression.")

    def update_budget_display(self):
        total = self.db.get_total_budget()
        items = self.db.get_all_items()
        count = len(items)
        self.lbl_budget_total.config(text=f"Total : {total:.2f} €  ({count} articles enregistrés)")
        
    def edit_category(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Aucun choix", "Sélectionnez un article pour modifier sa catégorie.")
            return
        
        item_id = int(selection[0])
        item_data = self.tree.item(selection[0])["values"]
        article_name = item_data[0]
        current_cat = item_data[1]
        
        new_cat = simpledialog.askstring("Catégorie", f"Nouvelle catégorie pour '{article_name}' :", initialvalue=current_cat)
        
        if new_cat is not None and new_cat.strip() != "":
            try:
                self.db.cursor.execute("UPDATE items SET categorie = ? WHERE id = ?", (new_cat.strip(), item_id))
                self.db.conn.commit()
                self.refresh_list()
            except Exception as e:
                self.db.conn.rollback()
                messagebox.showerror("Erreur", f"Échec de la mise à jour : {e}")

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        items = self.db.get_all_items()
        for row in items:
            # row = (id, article, categorie, prix, magasin, date, quantite)
            # Utiliser row[0] (l'ID en base) comme IID dans l'arbre pour faciliter les manips
            self.tree.insert("", "end", iid=str(row[0]), 
                             values=(row[1], row[2], f"{row[3]:.2f} €", row[6], row[4], row[5]))

        self.update_budget_display()

    def run(self):
        self.root.mainloop()
        
    def on_item_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return

        item_data = self.tree.item(selection[0])["values"]
        article_name = item_data[0]
        history = self.db.get_price_history(article_name)

        if not history or len(history) < 2:
            messagebox.showinfo("Info", f"Pas assez d'historique de prix pour tracer un graphique pour : {article_name}")
            return

        hist_window = tk.Toplevel(self.root)
        hist_window.title(f"📈 Évolution : {article_name}")
        hist_window.geometry("600x500")

        prices = []
        dates = []
        for p, d in history:
            prices.append(p)
            try:
                dates.append(datetime.strptime(d, "%Y-%m-%d %H:%M:%S"))
            except ValueError:
                dates.append(d) # Fallback si le format date varie

        fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
        ax.plot(dates, prices, marker='o', linestyle='-', color='#2980B9', linewidth=2)
        
        ax.set_title(f"Évolution du prix : {article_name}")
        ax.set_ylabel("Prix (€)")
        ax.grid(True, linestyle='--', alpha=0.7)
        fig.autofmt_xdate(rotation=45)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=hist_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Gestion propre de la mémoire de matplotlib à la fermeture
        def on_close():
            plt.close(fig)
            hist_window.destroy()

        hist_window.protocol("WM_DELETE_WINDOW", on_close)
        ttk.Button(hist_window, text="Fermer", command=on_close).pack(pady=10)
        
    def rename_global(self):
        old_name = self.entry_article.get().strip()
        if not old_name:
            messagebox.showwarning("Attention", "Tapez d'abord le nom de l'article actuel dans le champ de saisie 'Article' en haut.")
            return
        
        new_name = simpledialog.askstring("Renommer globalement", f"Remplacer TOUTES les occurrences de '{old_name}' par :")
        if new_name and new_name.strip():
            if self.db.rename_article_global(old_name, new_name.strip()):
                messagebox.showinfo("Succès", f"L'article a été renommé en '{new_name}'")
                self.refresh_list()
                self.entry_article.delete(0, tk.END)

    def show_bilan_cat(self):
        data = self.db.get_summary_by_category()
        self.show_stats_window("Bilan par Catégorie", data, ["Catégorie", "Total Prix (€)", "Total Qté"])

    def show_bilan_art(self):
        data = self.db.get_summary_by_article()
        self.show_stats_window("Bilan par Article", data, ["Article", "Total Qté"])

    def show_stats_window(self, title, data, headers):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("450x350")
        
        tree = ttk.Treeview(win, columns=headers, show="headings")
        for h in headers:
            tree.heading(h, text=h)
            tree.column(h, anchor="center")
        tree.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        for row in data:
            formatted_row = [f"{v:.2f}" if isinstance(v, float) else v for v in row]
            tree.insert("", "end", values=formatted_row)

if __name__ == "__main__":
    app = MainWindow()
    app.run()