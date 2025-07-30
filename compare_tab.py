import tkinter as tk
from tkinter import messagebox
from tkcalendar import DateEntry
from tkintertable import TableCanvas, TableModel
from datetime import date, datetime, timedelta


# Szkielet klasy CompareTab do dalszego rozwoju
class CompareTab(tk.Frame):
    def __init__(self, parent, db_manager, energy_type="produced", data_type="real"):
        super().__init__(parent)
        self.db_manager = db_manager
        self.energy_type = tk.StringVar(value=energy_type)
        self.data_type = tk.StringVar(value=data_type)
        self.unit = tk.StringVar(value="kWh")
        self.date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))

        self.create_date_selector()
        self.create_data_type_selector()
        self.create_unit_selector()
        self.create_compare_table()
        self.create_sum_label()
        self.create_buttons()

    def create_date_selector(self):
        date_frame = tk.Frame(self)
        date_frame.pack(pady=10)
        # Etykieta daty
        date_label = tk.Label(
            date_frame, text="Data:", font=("Arial", 13, "bold"), fg="#0055aa"
        )
        date_label.pack(side=tk.LEFT)

        # Przycisk wstecz
        def prev_day():
            current = datetime.strptime(self.date_var.get(), "%Y-%m-%d")
            new_date = current - timedelta(days=1)
            self.date_var.set(new_date.strftime("%Y-%m-%d"))
            self._clear_table_data()  # czyści tabelę

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
            relief="solid",
        )
        self.date_entry.pack(side=tk.LEFT, padx=2)

        # Przycisk naprzód
        def next_day():
            current = datetime.strptime(self.date_var.get(), "%Y-%m-%d")
            new_date = current + timedelta(days=1)
            self.date_var.set(new_date.strftime("%Y-%m-%d"))
            self._clear_table_data()  # czyści tabelę

        next_btn = tk.Button(
            date_frame, text="▶", font=("Arial", 8, "bold"), width=2, command=next_day
        )
        next_btn.pack(side=tk.LEFT, padx=(2, 8))

    def create_data_type_selector(self):
        data_type_frame = tk.Frame(self)
        data_type_frame.pack(pady=0)
        tk.Label(data_type_frame, text="Rodzaj energii:").pack(side=tk.LEFT)
        real_radio = tk.Radiobutton(
            data_type_frame, text="Wyprodukowana", variable=self.energy_type, value="produced"
        )
        pred_radio = tk.Radiobutton(
            data_type_frame, text="Oddana", variable=self.energy_type, value="sold"
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

    def create_compare_table(self):
        data = {hour: {"Rzeczywiste": "", "Prognoza": ""} for hour in range(24)}
        self.model = TableModel()
        self.model.importDict(data)
        self.model.columnalign = {"Rzeczywiste": "center", "Prognoza": "center"}
        table_frame = tk.Frame(self)
        table_frame.pack(pady=10, fill="both", expand=True)
        self.table = TableCanvas(
            table_frame,
            model=self.model,
            editable=False,
            read_only=True,
            rowselectedcolor="lightblue",
            cellwidth=100,
            width=400,
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

    def clear_data(self):
        for col in range(2):  # Zakładając, że mamy dwie kolumny: rzeczywiste i prognozowane
            for row_key in self.model.data.keys():
                self.model.setValueAt("", row_key, col)
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

    def _clear_table_data(self):
    
        for col in range(2):  # Zakładając, że mamy dwie kolumny: rzeczywiste i prognozowane
            for i in range(24):
                self.model.setValueAt("", i, col)
        self.table.redraw()
        self.update_sum_label()

    def _insert_data_to_table(self, df, data_type=None):
        energy_type = self.energy_type.get() if hasattr(self.energy_type, 'get') else self.energy_type
        db_col = "produced_energy" if energy_type == "produced" else "sold_energy"
        col_idx = 0 if data_type == "real" else 1
        for i in range(24):
            val = (
                df[df["hour"] == i][db_col]
                if db_col in df.columns
                else df[df["hour"] == i].iloc[:, -1]
            )
            value = val.values[0] if not val.empty else ""
            if isinstance(value, (float, int)):
                if self.unit.get() == "MWh":
                    value = value / 1000
                value = f"{value:.3f}"
            self.model.setValueAt(str(value), i, col_idx)

    def _get_data_for_date(self, selected_date, data_type=None):
        db = self.db_manager
        if db is None:
            messagebox.showerror("Błąd", "Brak połączenia z bazą danych.")
            return None
        energy_type = self.energy_type.get() if hasattr(self.energy_type, 'get') else self.energy_type
        df = db.get_energy_for_date(
            selected_date, energy_type=energy_type, data_type=data_type
        )
        return df

    def fill_table_with_data(self):
        real_df = self._get_data_for_date(self.date_entry.get(), "real")
        predicted_df = self._get_data_for_date(self.date_entry.get(), "predicted")
        if real_df.empty:
            # Wyczyść tabelę, jeśli brak danych
            self._clear_table_data()
            messagebox.showinfo("Brak danych", "Brak danych dla wybranego dnia.")
            return

        self._insert_data_to_table(real_df, data_type="real")
        self._insert_data_to_table(predicted_df, data_type="predicted")
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

