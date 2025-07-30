import tkinter as tk
from tkinter import ttk
from db_manager import DBManager
from table_tab import TableTab
from compare_tab import CompareTab

class TableWithTabs(tk.Tk):
    def __init__(self, db_manager):
        super().__init__()
        self.title("Tabela godzinowa z zakładkami")
        self.geometry("420x740")  # <-- zwiększono wysokość z 700 na 740
        self.resizable(False, False)

        self.db_manager = db_manager

        # --- Styl zakładek ---
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TNotebook.Tab", font=("Arial", 11))
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#cce6ff")],
            foreground=[("selected", "black"), ("!selected", "gray")],
            font=[
                ("selected", ("Arial", 11, "bold")),
                ("!selected", ("Arial", 11, "normal")),
            ],
        )

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        # Zakładka: En. Wytworzona (historyczne)
        tab1 = TableTab(notebook, db_manager, energy_type="produced", data_type="real")
        # Zakładka: En. Wprowadzona (historyczne)
        tab2 = TableTab(notebook, db_manager, energy_type="sold", data_type="real")
        tab3 = CompareTab(notebook, db_manager)
        notebook.add(tab1, text="En. Wytworzona")
        notebook.add(tab2, text="En. Wprowadzona")
        notebook.add(tab3, text="Porównaj")


# --- main ---
if __name__ == "__main__":
    DB_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/energy_prediction"

    db = DBManager(DB_URL)  # lub przekaz istniejący obiekt
    app = TableWithTabs(db_manager=db)
    app.mainloop()
