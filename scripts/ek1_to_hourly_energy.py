import pandas as pd

# Ścieżka do pliku Excel
excel_path = r"C:\Users\Użytkownik1\Desktop\python_scripts\energy_production_planner\ek_2024_sold.xlsx"

# Wczytaj dane z Excela (tylko interesujące kolumny)
df = pd.read_excel(excel_path, usecols=["Data i czas", "MW"])

# Zamień przecinki na kropki i konwertuj na float
df['MW'] = df['MW'].astype(str).str.replace(',', '.').astype(float)

# Przekształć na datetime
df['datetime'] = pd.to_datetime(df['Data i czas'], format='%d-%m-%Y %H:%M')


# Przesuń każdy pomiar o 15 minut wstecz, aby interwał był przypisany do godziny rozpoczęcia
df['datetime'] = df['datetime'] - pd.Timedelta(minutes=15)


# Oblicz energię dla każdego pomiaru (kWh, interwał 15 min = 0.25h)
df['energy_kwh'] = df['MW'] * 0.25 * 1000


# Grupuj po godzinie i sumuj energię (kWh)
df['hour'] = df['datetime'].dt.floor('H')
hourly = df.groupby('hour')['energy_kwh'].sum().reset_index()

# Zapisz wynik do pliku Excel
output_path = r"C:\Users\Użytkownik1\Desktop\python_scripts\energy_production_planner\sold_energy_2024_hour.xlsx"
hourly.to_excel(output_path, index=False)
print(f"Wynik zapisano do: {output_path}")
print(hourly)
