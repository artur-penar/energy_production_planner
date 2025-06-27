import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkintertable import TableCanvas, TableModel
from datetime import date
import pandas as pd
from tkcalendar import DateEntry


class TableTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))

        # Date selection
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

        # Prepare table data for 24 hours
        data = {hour: {"Wartość": ""} for hour in range(24)}

        self.model = TableModel()
        self.model.importDict(data)
        self.model.columnalign = {"Wartość": "center"}

        # Table frame
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

        # Buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)
        clear_btn = tk.Button(button_frame, text="Clear Data", command=self.clear_data)
        clear_btn.pack(side=tk.LEFT, padx=10)
        copy_btn = tk.Button(
            button_frame, text="Copy to Clipboard", command=self.copy_to_clipboard
        )
        copy_btn.pack(side=tk.LEFT, padx=10)

        # Clipboard paste bindings
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
                val = self.model.getValueAt(row_key, "Wartość")
                if val is None:
                    val = ""
                values.append(str(val))
            clipboard_str = "\n".join(values)
            self.clipboard_clear()
            self.clipboard_append(clipboard_str)
            messagebox.showinfo("Sukces", "Dane zostały skopiowane do schowka.")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się skopiować danych: {e}")


class TableWithTabs(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tabela godzinowa z zakładkami")
        self.geometry("420x700")
        self.resizable(False, False)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        # Dodaj dwie zakładki (możesz dodać więcej)
        tab1 = TableTab(notebook)
        tab2 = TableTab(notebook)
        notebook.add(tab1, text="En. Wytworzona")
        notebook.add(tab2, text="En. Wprowadzona")


if __name__ == "__main__":
    app = TableWithTabs()
    app.mainloop()
