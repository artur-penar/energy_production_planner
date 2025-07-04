import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date

import pandas as pd
from tkcalendar import DateEntry
from tkintertable import TableCanvas, TableModel

from db_manager import DBManager


class TableTab(tk.Frame):
    def __init__(self, parent, db_manager, energy_type="produced", data_type="real"):
        super().__init__(parent)
        self.db_manager = db_manager
        self.energy_type = energy_type
        self.data_type = tk.StringVar(value=data_type)
        self.unit = tk.StringVar(value="kWh")

        self.date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        # Wiersz 1: Data
        date_frame = tk.Frame(self)
        date_frame.pack(pady=10)
        tk.Label(date_frame, text="Data:").pack(side=tk.LEFT)
        self.date_entry = DateEntry(
            date_frame,
            textvariable=self.date_var,
            date_pattern="yyyy-mm-dd",
            width=12,
            justify="center",
        )
        self.date_entry.pack(side=tk.LEFT, padx=5)

        # Wiersz 2: Typ danych (real/predicted)
        data_type_frame = tk.Frame(self)
        data_type_frame.pack(pady=0)
        tk.Label(data_type_frame, text="Typ danych:").pack(side=tk.LEFT)
        real_radio = tk.Radiobutton(
            data_type_frame,
            text="Rzeczywiste",
            variable=self.data_type,
            value="real"
        )
        pred_radio = tk.Radiobutton(
            data_type_frame,
            text="Prognoza",
            variable=self.data_type,
            value="predicted"
        )
        real_radio.pack(side=tk.LEFT, padx=5)
        pred_radio.pack(side=tk.LEFT, padx=5)

        # Wiersz 3: Jednostka (kWh/MWh)
        unit_frame = tk.Frame(self)
        unit_frame.pack(pady=0)
        tk.Label(unit_frame, text="Jednostka:").pack(side=tk.LEFT)
        kwh_radio = tk.Radiobutton(
            unit_frame,
            text="kWh",
            variable=self.unit,
            value="kWh",
            command=self.redraw_table_with_unit,
        )
        mwh_radio = tk.Radiobutton(
            unit_frame,
            text="MWh",
            variable=self.unit,
            value="MWh",
            command=self.redraw_table_with_unit,
        )
        kwh_radio.pack(side=tk.LEFT)
        mwh_radio.pack(side=tk.LEFT)

        # Przygotowanie danych do tabeli (24 godziny)
        data = {hour: {"Wartość": ""} for hour in range(24)}

        self.model = TableModel()
        self.model.importDict(data)
        self.model.columnalign = {"Wartość": "center"}

        # Ramka z tabelą
        table_frame = tk.Frame(self)
        table_frame.pack(pady=10, fill="both", expand=True)
        self.table = TableCanvas(
            table_frame,
            model=self.model,
            editable=True,
            read_only=False,
            rowselectedcolor="lightblue",
            cellwidth=100,
            width=350,
            height=450,
        )
        self.table.show()

        # Suma pod tabelą
        self.sum_label = tk.Label(self, text="Suma: 0.000 kWh")
        self.sum_label.pack(pady=(0, 10))

        # Przyciski
        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)
        clear_btn = tk.Button(
            button_frame,
            text="Clear Data",
            command=self.clear_data
        )
        clear_btn.pack(side=tk.LEFT, padx=10)
        copy_btn = tk.Button(
            button_frame,
            text="Copy to Clipboard",
            command=self.copy_to_clipboard
        )
        copy_btn.pack(side=tk.LEFT, padx=10)
        real_btn = tk.Button(
            button_frame,
            text="Pobierz dane",
            command=self.fill_table_with_data
        )
        real_btn.pack(side=tk.LEFT, padx=10)

        # Obsługa wklejania ze schowka
        self.table.bind("<Control-v>", self.paste_from_clipboard)
        self.table.bind("<Control-V>", self.paste_from_clipboard)

    def paste_from_clipboard(self, event=None):
        try:
            clipboard = self.clipboard_get()
            lines = clipboard.strip().split("\n")
            row_keys = list(self.model.data.keys())
            for i, line in enumerate(lines):
                if i >= len(row_keys):
                    break
                value = line.split("\t")[0].replace(",", ".").strip()
                if value:
                    try:
                        value_float = float(value)
                    except ValueError:
                        value_float = value
                    self.model.setValueAt(value_float, row_keys[i], 0)
            self.table.redraw()
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się wkleić danych: {e}")

    def clear_data(self):
        for row_key in self.model.data.keys():
            self.model.setValueAt("", row_key, 0)
        self.table.redraw()

    def copy_to_clipboard(self):
        try:
            values = []
            for row_key in self.model.data.keys():
                val = self.model.getValueAt(row_key, 0)
                if val is None:
                    val = ""
                values.append(str(val))
            clipboard_str = "\n".join(values)
            self.clipboard_clear()
            self.clipboard_append(clipboard_str)
            messagebox.showinfo("Sukces", "Dane zostały skopiowane do schowka.")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się skopiować danych: {e}")

    def fill_table_with_data(self):
        selected_date = self.date_entry.get()
        db = self.db_manager
        if db is None:
            messagebox.showerror("Błąd", "Brak połączenia z bazą danych.")
            return
        data_type = self.data_type.get()
        df = db.get_energy_for_date(
            selected_date, energy_type=self.energy_type, data_type=data_type
        )
        if df.empty:
            messagebox.showinfo("Brak danych", "Brak danych dla wybranego dnia.")
            return
        for i in range(24):
            col = "produced_energy" if self.energy_type == "produced" else "sold_energy"
            val = (
                df[df["hour"] == i][col]
                if col in df.columns
                else df[df["hour"] == i].iloc[:, -1]
            )
            value = val.values[0] if not val.empty else ""
            if isinstance(value, (float, int)):
                if self.unit.get() == "MWh":
                    value = value / 1000
                value = f"{value:.3f}"
            self.model.setValueAt(str(value), i, 0)
        self.table.redraw()
        self.update_sum_label()

    def redraw_table_with_unit(self):
        for i in range(24):
            value = self.model.getValueAt(i, 0)
            try:
                value_float = float(value.replace(",", "."))
            except Exception:
                value_float = value
            if isinstance(value_float, (float, int)):
                if self.unit.get() == "MWh":
                    value_float = value_float / 1000
                else:
                    value_float = (
                        value_float * 1000 if float(value) < 100 else value_float
                    )
                value_str = f"{value_float:.3f}"
            else:
                value_str = value
            self.model.setValueAt(value_str, i, 0)
        self.table.redraw()
        self.update_sum_label()  # Dodaj to!

    def update_sum_label(self):
        total = 0.0
        for i in range(24):
            value = self.model.getValueAt(i, 0)
            try:
                total += float(value.replace(",", "."))
            except Exception:
                pass
        self.sum_label.config(text=f"Suma: {total:.3f} {self.unit.get()}")


class TableWithTabs(tk.Tk):
    def __init__(self, db_manager):
        super().__init__()
        self.title("Tabela godzinowa z zakładkami")
        self.geometry("420x700")
        self.resizable(False, False)

        self.db_manager = db_manager

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        # Zakładka: En. Wytworzona (historyczne)
        tab1 = TableTab(notebook, db_manager, energy_type="produced", data_type="real")
        # Zakładka: En. Wprowadzona (historyczne)
        tab2 = TableTab(notebook, db_manager, energy_type="sold", data_type="real")
        notebook.add(tab1, text="En. Wytworzona")
        notebook.add(tab2, text="En. Wprowadzona")


# --- main ---
if __name__ == "__main__":
    DB_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/energy_prediction"

    db = DBManager(DB_URL)  # lub przekaz istniejący obiekt
    app = TableWithTabs(db_manager=db)
    app.mainloop()
