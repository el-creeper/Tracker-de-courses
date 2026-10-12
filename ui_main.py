import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sys
import os
from datetime import datetime, timedelta
from database import DatabaseManager
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🛒 Suivi de Courses")
        self.root.geometry("950x680")
        
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
            
        style.configure("Treeview", rowheight=25, font=('Segoe UI', 10))
        style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))

        try:
            self.db = DatabaseManager()
            self.setup_ui()
        except Exception as e:
            messagebox.showerror("Erreur Fatale", f"Impossible d'initialiser la BDD.\n{str(e)}")
            self.root.destroy()

    def setup_ui(self):
        input_frame = ttk.LabelFrame(self.root, text="➕ Ajouter un article", padding=15)
        input_frame.pack(fill="x", padx=15, pady=10)

        # Remplacement de l'Entry par une Combobox pour l'autocomplétion
        ttk.Label(input_frame, text="Article :").grid(row=0, column=0, sticky="w", pady=5)
        self.entry_article = ttk.Combobox(input_frame, width=23)
        self.entry_article.grid(row=0, column=1, padx=10, pady=5)
        self.entry_article.bind("<<ComboboxSelected>>", self.autofill_article_details)
        self.entry_article.bind("<FocusOut>", self.autofill_article_details)

        ttk.Label(input_frame, text="Catégorie :").grid(row=0, column=2, sticky="w", pady=5)
        self.entry_cat = ttk.Entry(input_frame, width=20)
        self.entry_cat.grid(row=0, column=3, padx=10, pady=5)

        ttk.Label(input_frame, text="Prix U. (€) :").grid(row=0, column=4, sticky="w", pady=5)
        self.entry_prix = ttk.Entry(input_frame, width=10)
        self.entry_prix.grid(row=0, column=5, padx=10, pady=5)

        ttk.Label(input_frame, text="Quantité :").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_quantite = ttk.Entry(input_frame, width=10)
        self.entry_quantite.insert(0, "1")
        self.entry_quantite.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        ttk.Label(input_frame, text="Magasin :").grid(row=1, column=2, sticky="w", pady=5)
        self.entry_mag = ttk.Entry(input_frame, width=20)
        self.entry_mag.grid(row=1, column=3, padx=10, pady=5)

        btn_add = ttk.Button(input_frame, text="✔️ Ajouter", command=self.add_course)
        btn_add.grid(row=1, column=4, columnspan=2, padx=10, pady=5, sticky="we")

        stats_frame = ttk.Frame(self.root, padding=5)
        stats_frame.pack(fill="x", padx=15)

        self.lbl_budget_total = ttk.Label(stats_frame, text="Total : 0.00 €", font=("Segoe UI", 14, "bold"), foreground="#2C3E50")
        self.lbl_budget_total.pack(side="left")

        list_frame = ttk.LabelFrame(self.root, text="📋 Historique (Ctrl+C pour copier, Clic sur les colonnes pour trier)", padding=10)
        list_frame.pack(fill="both", expand=True, padx=15, pady=5)

        columns = ("Article", "Catégorie", "Prix U.", "Qté", "Total (€)", "Magasin", "Date")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        widths = {"Article": 150, "Catégorie": 100, "Prix U.": 70, "Qté": 50, "Total (€)": 80, "Magasin": 110, "Date": 140}
        for col in columns:
            # Ajout du tri au clic sur l'en-tête
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_treeview(_col, False))
            self.tree.column(col, width=widths[col], anchor="center")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.tree.bind("<Double-1>", self.on_item_double_click)
        self.tree.bind("<Control-c>", self.copy_selection)
        self.tree.bind("<Command-c>", self.copy_selection)

        btn_frame1 = ttk.Frame(self.root, padding=5)
        btn_frame1.pack(fill="x", padx=10)
        
        ttk.Button(btn_frame1, text="❌ Supprimer", command=self.delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame1, text="✏️ Modif. Catégorie", command=self.edit_category).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame1, text="🔢 Modif. Qté", command=self.edit_quantity).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame1, text="🔄 Renommer Global", command=self.rename_global).pack(side=tk.LEFT, padx=5)
        
        btn_frame2 = ttk.Frame(self.root, padding=5)
        btn_frame2.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(btn_frame2, text="📊 Bilan Catégorie", command=self.show_bilan_cat).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame2, text="📦 Bilan Article", command=self.show_bilan_art).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame2, text="📈 Stats Dépenses", command=self.show_advanced_stats).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame2, text="🏪 Comparateur Magasins", command=self.show_store_comparator).pack(side=tk.RIGHT, padx=5)

        self.refresh_list()

    def update_article_autocomplete(self):
        """Met à jour la liste des articles connus pour l'autocomplétion"""
        self.entry_article['values'] = self.db.get_unique_articles()

    def autofill_article_details(self, event=None):
        """Remplit automatiquement Catégorie, Prix et Magasin si l'article est connu"""
        article = self.entry_article.get().strip()
        if not article: return
        
        defaults = self.db.get_article_defaults(article)
        if defaults:
            cat, prix, mag = defaults
            # Ne remplit que si le champ est vide (pour ne pas écraser une nouvelle saisie)
            if not self.entry_cat.get() and cat:
                self.entry_cat.insert(0, cat)
            if not self.entry_prix.get() and prix:
                self.entry_prix.insert(0, f"{prix:.2f}")
            if not self.entry_mag.get() and mag:
                self.entry_mag.insert(0, mag)

    def sort_treeview(self, col, reverse):
        """Trie les colonnes du Treeview dynamiquement"""
        # On force la conversion en str() ici pour rassurer Pylance
        l = [(str(self.tree.set(k, col)), k) for k in self.tree.get_children('')]
        
        try:
            # Tri numérique pour les colonnes de prix et quantité
            if col in ("Prix U.", "Total (€)"):
                l.sort(key=lambda t: float(t[0].replace(' €', '')), reverse=reverse)
            elif col == "Qté":
                l.sort(key=lambda t: float(t[0]), reverse=reverse)
            else:
                # Tri alphabétique / Date
                l.sort(reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)

        # Réorganiser les éléments
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        # Inverser le tri au prochain clic
        self.tree.heading(col, command=lambda: self.sort_treeview(col, not reverse))

    def copy_selection(self, event):
        selection = self.tree.selection()
        if not selection: return
        copied_data = [str(self.tree.item(item)["values"][0]) for item in selection]
        final_text = "\n".join(copied_data)
        self.root.clipboard_clear()
        self.root.clipboard_append(final_text)
        self.root.update()
        original_title = self.root.title()
        self.root.title("✅ Article(s) copié(s) !")
        self.root.after(1500, lambda: self.root.title(original_title))

    def add_course(self):
        article = self.entry_article.get().strip()
        cat = self.entry_cat.get().strip()
        magasin = self.entry_mag.get().strip()
        
        try:
            prix_u = float(self.entry_prix.get().replace(',', '.'))
            quantite = float(self.entry_quantite.get().replace(',', '.'))
        except ValueError:
            messagebox.showerror("Erreur", "Le prix unitaire et la quantité doivent être des nombres.")
            return

        if not article or prix_u <= 0 or quantite <= 0:
            messagebox.showwarning("Attention", "Article, prix positif et quantité requises.")
            return

        if self.db.add_item(article, cat, prix_u, magasin, quantite):
            self.refresh_list()
            self.entry_article.set('')
            self.entry_cat.delete(0, tk.END)
            self.entry_prix.delete(0, tk.END)
            self.entry_mag.delete(0, tk.END)
            self.entry_quantite.delete(0, tk.END)
            self.entry_quantite.insert(0, "1")
            self.entry_article.focus_set()

    def edit_quantity(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Aucun choix", "Sélectionnez un article pour modifier sa quantité.")
            return
        
        item_id = int(selection[0])
        item_data = self.tree.item(selection[0])["values"]
        article_name = item_data[0]
        current_qty = item_data[3]
        
        new_qty_str = simpledialog.askstring("Modifier Quantité", f"Nouvelle quantité pour '{article_name}' :", initialvalue=str(current_qty))
        
        if new_qty_str and new_qty_str.strip():
            try:
                new_qty = float(new_qty_str.replace(',', '.'))
                if new_qty > 0:
                    if self.db.update_quantity(item_id, new_qty):
                        self.refresh_list()
                    else:
                        messagebox.showerror("Erreur", "Échec de la mise à jour.")
                else:
                    messagebox.showwarning("Attention", "La quantité doit être supérieure à 0.")
            except ValueError:
                messagebox.showerror("Erreur", "Veuillez entrer un nombre valide.")

    def edit_category(self):
        selection = self.tree.selection()
        if not selection:
            return
        item_id = int(selection[0])
        item_data = self.tree.item(selection[0])["values"]
        
        new_cat = simpledialog.askstring("Catégorie", f"Nouvelle catégorie pour '{item_data[0]}' :", initialvalue=item_data[1])
        if new_cat is not None and new_cat.strip() != "":
            try:
                self.db.cursor.execute("UPDATE items SET categorie = ? WHERE id = ?", (new_cat.strip(), item_id))
                self.db.conn.commit()
                self.refresh_list()
            except Exception as e:
                self.db.conn.rollback()

    def delete_selected(self):
        selection = self.tree.selection()
        if not selection: return
        item_id = int(selection[0])
        if messagebox.askyesno("Confirmation", "Supprimer cet article ?"):
            if self.db.delete_item(item_id):
                self.refresh_list()

    def update_budget_display(self):
        total = self.db.get_total_budget()
        items = self.db.get_all_items()
        self.lbl_budget_total.config(text=f"Total payé : {total:.2f} €  ({len(items)} lignes)")

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        items = self.db.get_all_items()
        for row in items:
            prix_u = float(row[3])
            qte = float(row[6])
            prix_total = prix_u * qte
            self.tree.insert("", "end", iid=str(row[0]), 
                             values=(row[1], row[2], f"{prix_u:.2f} €", qte, f"{prix_total:.2f} €", row[4], row[5]))

        self.update_budget_display()
        self.update_article_autocomplete()

    def run(self):
        self.root.mainloop()

    def show_store_comparator(self):
        """Nouvelle fenêtre : Comparateur de magasins pour un article donné"""
        win = tk.Toplevel(self.root)
        win.title("🏪 Comparateur de Magasins")
        win.geometry("650x500")

        filter_frame = ttk.Frame(win, padding=10)
        filter_frame.pack(fill="x")

        ttk.Label(filter_frame, text="Choisir l'article :").pack(side=tk.LEFT, padx=5)
        article_var = tk.StringVar()
        article_cb = ttk.Combobox(filter_frame, textvariable=article_var, values=self.db.get_unique_articles(), state="readonly", width=30)
        article_cb.pack(side=tk.LEFT, padx=5)

        graph_frame = ttk.Frame(win)
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        def update_comparison_graph(*args):
            for widget in graph_frame.winfo_children():
                widget.destroy()

            article = article_var.get()
            if not article: return

            data = self.db.get_store_comparison(article)
            if not data:
                ttk.Label(graph_frame, text="Pas assez de données (ou magasins non renseignés).", font=("Segoe UI", 12)).pack(pady=50)
                return

            stores = [row[0] for row in data]
            prices = [float(row[1]) for row in data]

            fig = Figure(figsize=(6, 4), dpi=100)
            ax = fig.add_subplot(111)
            bars = ax.bar(stores, prices, color='#E67E22', edgecolor='black', alpha=0.8)
            
            ax.set_ylabel("Prix moyen (€)")
            ax.set_title(f"Comparaison des prix : {article}")
            ax.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Afficher le prix au-dessus de chaque barre
            for bar in bars:
                yval = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, yval + (max(prices)*0.02), f"{yval:.2f}€", ha='center', va='bottom', fontweight='bold')

            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        article_cb.bind("<<ComboboxSelected>>", update_comparison_graph)
        
        def on_close():
            plt.close('all')
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", on_close)

    def show_advanced_stats(self):
        win = tk.Toplevel(self.root)
        win.title("📈 Statistiques Avancées")
        win.geometry("750x550")
        
        filter_frame = ttk.Frame(win, padding=10)
        filter_frame.pack(fill="x")
        
        ttk.Label(filter_frame, text="Période :").pack(side=tk.LEFT, padx=5)
        period_var = tk.StringVar(value="Mois")
        period_cb = ttk.Combobox(filter_frame, textvariable=period_var, values=["Jour", "Semaine", "Mois"], state="readonly", width=10)
        period_cb.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(filter_frame, text="Catégorie :").pack(side=tk.LEFT, padx=(15, 5))
        cat_var = tk.StringVar(value="Toutes")
        categories = ["Toutes"] + self.db.get_categories()
        cat_cb = ttk.Combobox(filter_frame, textvariable=cat_var, values=categories, state="readonly", width=20)
        cat_cb.pack(side=tk.LEFT, padx=5)
        
        graph_frame = ttk.Frame(win)
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        def update_graph(*args):
            for widget in graph_frame.winfo_children():
                widget.destroy()
                
            period = period_var.get()
            category = cat_var.get()
            data = self.db.get_advanced_stats(period, category)
            
            data_dict = {str(row[0]): float(row[1] or 0.0) for row in data if row[0]}
            
            if not data_dict:
                ttk.Label(graph_frame, text="Aucune dépense valide pour ces critères.", font=("Segoe UI", 12)).pack(pady=50)
                return
            
            periods_list = sorted(data_dict.keys())
            start_period = periods_list[0]
            end_period = periods_list[-1]
            
            cleaned_periods = []
            cleaned_totals = []

            # Combler les dates intermédiaires vides
            try:
                if period == "Jour":
                    start_date = datetime.strptime(start_period, "%Y-%m-%d")
                    end_date = datetime.strptime(end_period, "%Y-%m-%d")
                    current = start_date
                    while current <= end_date:
                        p_str = current.strftime("%Y-%m-%d")
                        cleaned_periods.append(p_str)
                        cleaned_totals.append(data_dict.get(p_str, 0.0))
                        current += timedelta(days=1)
                        
                elif period == "Mois":
                    start_y, start_m = map(int, start_period.split('-'))
                    end_y, end_m = map(int, end_period.split('-'))
                    curr_y, curr_m = start_y, start_m
                    while (curr_y < end_y) or (curr_y == end_y and curr_m <= end_m):
                        p_str = f"{curr_y}-{curr_m:02d}"
                        cleaned_periods.append(p_str)
                        cleaned_totals.append(data_dict.get(p_str, 0.0))
                        curr_m += 1
                        if curr_m > 12:
                            curr_m = 1
                            curr_y += 1
                            
                elif period == "Semaine":
                    start_y, start_w = int(start_period[:4]), int(start_period[-2:])
                    end_y, end_w = int(end_period[:4]), int(end_period[-2:])
                    # Trouver le premier jour de la semaine
                    start_date = datetime.strptime(f"{start_y}-W{start_w:02d}-1", "%Y-W%W-%w")
                    end_date = datetime.strptime(f"{end_y}-W{end_w:02d}-1", "%Y-W%W-%w")
                    
                    current = start_date
                    while current <= end_date:
                        p_str = current.strftime("%Y-S%W")
                        cleaned_periods.append(p_str)
                        cleaned_totals.append(data_dict.get(p_str, 0.0))
                        current += timedelta(days=7)
            except Exception as e:
                # Fallback au cas où une date est corrompue dans SQLite
                cleaned_periods = periods_list
                cleaned_totals = [data_dict[p] for p in periods_list]

            fig = Figure(figsize=(7, 4), dpi=100)
            ax = fig.add_subplot(111)
            ax.bar(cleaned_periods, cleaned_totals, color='#27AE60', edgecolor='black', alpha=0.8)
            
            ax.set_ylabel("Dépenses (€)")
            ax.set_title(f"Dépenses par {period.lower()} ({category})")
            ax.grid(axis='y', linestyle='--', alpha=0.7)
            
            ax.tick_params(axis='x', rotation=45)
            for tick in ax.get_xticklabels():
                tick.set_horizontalalignment('right')
                
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(graph_frame, text=f"Total sur la sélection : {sum(cleaned_totals):.2f} €", font=("Segoe UI", 11, "bold")).pack(pady=5)

        period_cb.bind("<<ComboboxSelected>>", update_graph)
        cat_cb.bind("<<ComboboxSelected>>", update_graph)
        update_graph() 
        
        def on_close():
            plt.close('all')
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", on_close)

    def on_item_double_click(self, event):
        selection = self.tree.selection()
        if not selection: return
        article_name = self.tree.item(selection[0])["values"][0]
        history = self.db.get_price_history(article_name)

        if not history or len(history) < 2:
            messagebox.showinfo("Info", f"Pas assez d'historique pour : {article_name}")
            return

        hist_window = tk.Toplevel(self.root)
        hist_window.title(f"Évolution : {article_name}")
        hist_window.geometry("600x400")

        prices = [p for p, d in history]
        dates = [d for p, d in history]

        fig = Figure(figsize=(5, 3), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(dates, prices, marker='o', linestyle='-', color='#2980B9')
        ax.set_title(f"Évolution du prix unitaire : {article_name}")
        ax.set_ylabel("Prix (€)")
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.tick_params(axis='x', rotation=45)
        for tick in ax.get_xticklabels():
            tick.set_horizontalalignment('right')
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=hist_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        def on_close():
            plt.close(fig)
            hist_window.destroy()
        hist_window.protocol("WM_DELETE_WINDOW", on_close)
        
    def rename_global(self):
        old_name = self.entry_article.get().strip()
        if not old_name:
            messagebox.showwarning("Attention", "Tapez d'abord le nom actuel dans le champ 'Article'.")
            return
        
        new_name = simpledialog.askstring("Renommer globalement", f"Remplacer '{old_name}' par :")
        if new_name and new_name.strip():
            if self.db.rename_article_global(old_name, new_name.strip()):
                self.refresh_list()
                self.entry_article.set('')

    def show_bilan_cat(self):
        self.show_stats_window("Bilan par Catégorie", self.db.get_summary_by_category(), ["Catégorie", "Total Prix (€)", "Total Qté"])

    def show_bilan_art(self):
        self.show_stats_window("Bilan par Article", self.db.get_summary_by_article(), ["Article", "Total Qté"])

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