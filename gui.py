import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime, timedelta

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

        self.create_date_selector()
        self.create_data_type_selector()
        self.create_unit_selector()
        self.create_table()
        self.create_sum_label()
        self.create_buttons()
        self.bind_shortcuts()

    def create_date_selector(self):
        date_frame = tk.Frame(self)
        date_frame.pack(pady=10)
        # Etykieta daty
        date_label = tk.Label(
            date_frame,
            text="Data:",
            font=("Arial", 13, "bold"),
            fg="#0055aa"
        )
        date_label.pack(side=tk.LEFT)

        # Przycisk wstecz
        def prev_day():
            current = datetime.strptime(self.date_var.get(), "%Y-%m-%d")
            new_date = current - timedelta(days=1)
            self.date_var.set(new_date.strftime("%Y-%m-%d"))

        prev_btn = tk.Button(
            date_frame, text="◀", font=("Arial", 8, "bold"), width=2, command=prev_day
        )
        prev_btn.pack(side=tk.LEFT, padx=(8, 2))

        # Pole wyboru daty
        self.date_entry = DateEntry(
            date_frame,
            textvariable=self.date_var,
            date_pattern="yyyy-mm-dd",
            width=14,
            justify="center",
            font=("Arial", 13, "bold"),
            foreground="#0055aa",
            background="#e6f2ff",
            borderwidth=2,
            relief="solid"
        )
        self.date_entry.pack(side=tk.LEFT, padx=2)

        # Przycisk naprzód
        def next_day():
            current = datetime.strptime(self.date_var.get(), "%Y-%m-%d")
            new_date = current + timedelta(days=1)
            self.date_var.set(new_date.strftime("%Y-%m-%d"))

        next_btn = tk.Button(
           date_frame, text="▶", font=("Arial", 8, "bold"), width=2, command=next_day
        )
        next_btn.pack(side=tk.LEFT, padx=(2, 8))

    def create_data_type_selector(self):
        data_type_frame = tk.Frame(self)
        data_type_frame.pack(pady=0)
        tk.Label(data_type_frame, text="Typ danych:").pack(side=tk.LEFT)
        real_radio = tk.Radiobutton(
            data_type_frame, text="Rzeczywiste", variable=self.data_type, value="real"
        )
        pred_radio = tk.Radiobutton(
            data_type_frame, text="Prognoza", variable=self.data_type, value="predicted"
        )
        real_radio.pack(side=tk.LEFT, padx=5)
        pred_radio.pack(side=tk.LEFT, padx=5)

    def create_unit_selector(self):
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

    def create_table(self):
        data = {hour: {"Wartość": ""} for hour in range(24)}
        self.model = TableModel()
        self.model.importDict(data)
        self.model.columnalign = {"Wartość": "center"}
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

    def create_sum_label(self):
        self.sum_label = tk.Label(self, text="Suma: 0.000 kWh")
        self.sum_label.pack(pady=(0, 10))

    def create_buttons(self):
        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)
        clear_btn = tk.Button(button_frame, text="Clear Data", command=self.clear_data)
        clear_btn.pack(side=tk.LEFT, padx=10)
        copy_btn = tk.Button(
            button_frame, text="Copy to Clipboard", command=self.copy_to_clipboard
        )
        copy_btn.pack(side=tk.LEFT, padx=10)
        real_btn = tk.Button(
            button_frame, text="Pobierz dane", command=self.fill_table_with_data
        )
        real_btn.pack(side=tk.LEFT, padx=10)
        save_btn = tk.Button(
            button_frame, text="Zapisz do bazy", command=self.save_table_to_db
        )
        save_btn.pack(side=tk.LEFT, padx=10)

    def bind_shortcuts(self):
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
            self.update_sum_label()

        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się wkleić danych: {e}")

    def clear_data(self):
        for row_key in self.model.data.keys():
            self.model.setValueAt("", row_key, 0)
        self.table.redraw()
        self.update_sum_label()

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
            # Wyczyść tabelę, jeśli brak danych
            for i in range(24):
                self.model.setValueAt("", i, 0)
            self.table.redraw()
            self.update_sum_label()
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
                total += float(str(value).replace(",", "."))
            except Exception:
                pass
        self.sum_label.config(text=f"Suma: {total:.3f} {self.unit.get()}")

    def save_table_to_db(self):
        data_list = []
        selected_date = self.date_entry.get()
        col = "produced_energy" if self.energy_type == "produced" else "sold_energy"
        values = []
        for hour in range(24):
            value = self.model.getValueAt(hour, 0)
            try:
                value_float = float(str(value).replace(",", "."))
            except Exception:
                value_float = None
            values.append(value_float)
            data_list.append({"date": selected_date, "hour": hour, col: value_float})

        # WALIDACJA: podejrzanie małe wartości w kWh
        if self.unit.get() == "kWh":
            # Sprawdź, czy większość wartości jest < 20 (np. 22 z 24)
            small_values = [v for v in values if v is not None and v < 20]
            if len(small_values) >= 20:
                if not messagebox.askyesno(
                    "Ostrzeżenie",
                    "Większość wartości jest bardzo mała (wygląda na MWh, a nie kWh). Czy na pewno chcesz zapisać dane?",
                ):
                    return

        # Przelicz na kWh jeśli trzeba
        for row in data_list:
            if self.unit.get() == "MWh" and row[col] is not None:
                row[col] = row[col] * 1000

        try:
            self.db_manager.insert_real_energy_data(
                data_list, energy_type=self.energy_type
            )
            messagebox.showinfo("Sukces", "Dane zostały zapisane do bazy.")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się zapisać danych: {e}")


class TableWithTabs(tk.Tk):
    def __init__(self, db_manager):
        super().__init__()
        self.title("Tabela godzinowa z zakładkami")
        self.geometry("420x740")  # <-- zwiększono wysokość z 700 na 740
        self.resizable(False, False)

        self.db_manager = db_manager

        # --- Styl zakładek ---
        style = ttk.Style(self)
        style.theme_use('default')
        style.configure('TNotebook.Tab', font=('Arial', 11))
        style.map('TNotebook.Tab',
                  background=[('selected', '#cce6ff')],
                  foreground=[('selected', 'black'), ('!selected', 'gray')],
                  font=[('selected', ('Arial', 11, 'bold')), ('!selected', ('Arial', 11, 'normal'))]
        )

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
