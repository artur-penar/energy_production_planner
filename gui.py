import tkinter as tk
from tkinter import messagebox, filedialog
from tkintertable import TableCanvas, TableModel
from datetime import date
import pandas as pd
from tkcalendar import DateEntry


class TableWithDate(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tabela godzinowa (tkintertable)")
        self.geometry("400x600")
        self.resizable(False, False)

        # Data na górze okna - interaktywny wybór daty
        self.date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
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
        self.date_entry.pack(side=tk.LEFT)

        # Przygotowanie danych do tabeli
        data = {}
        for hour in range(24):
            data[hour] = {"Wartość": ""}

        self.model = TableModel()
        self.model.importDict(data)

        # Tabela
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

        # Przyciski pod tabelą
        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)

        clear_btn = tk.Button(button_frame, text="Clear Data", command=self.clear_data)
        clear_btn.pack(side=tk.LEFT, padx=10)

        copy_btn = tk.Button(
            button_frame, text="Copy to Clipboard", command=self.copy_to_clipboard
        )
        copy_btn.pack(side=tk.LEFT, padx=10)

        self.bind_all("<Control-v>", self.paste_from_clipboard)
        self.bind_all("<Control-V>", self.paste_from_clipboard)
        print(self.model.columnNames)

    def paste_from_clipboard(self, event=None):
        try:
            clipboard = self.clipboard_get()
            lines = clipboard.strip().split("\n")
            row_keys = list(self.model.data.keys())
            print("Row keys:", row_keys)
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
            print(f"Error pasting data: {e}")

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


if __name__ == "__main__":
    app = TableWithDate()
    app.mainloop()
