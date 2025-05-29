# Skrypt do importu danych do tabeli calendar
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.sql import text

# Wczytaj dane z Excela (dostosuj ścieżkę jeśli potrzeba)
excel_path = "data/archive/historical_production.xlsx"
df = pd.read_excel(excel_path)

# Zamień kolumnę date na typ date (bez czasu)
df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

# Przygotuj dane do tabeli calendar
calendar_cols = ["date", "is_holiday"]
df_calendar = df[calendar_cols].drop_duplicates().copy()
df_calendar["is_holiday"] = df_calendar["is_holiday"].astype(bool)
df_calendar["date"] = pd.to_datetime(df_calendar["date"], errors="coerce").dt.date

# Dodaj kolumnę day_of_week jeśli nie istnieje
df_calendar["day_of_week"] = pd.to_datetime(df_calendar["date"], errors="coerce").dt.dayofweek

# Dodaj debug: sprawdź, gdzie występują NaN w date lub day_of_week
nan_rows = df_calendar[df_calendar[["date", "day_of_week"]].isnull().any(axis=1)]
if not nan_rows.empty:
    print("[DEBUG] Wiersze z NaN w date lub day_of_week:")
    for idx in nan_rows.index:
        print(f"Index: {idx}")
        print(df_calendar.loc[max(0, idx-2):idx+2])  # pokaż 2 wiersze przed i po

# Usuń wiersze z brakującą datą lub day_of_week
df_calendar = df_calendar.dropna(subset=["date", "day_of_week"])

# Połącz się z bazą PostgreSQL
engine = create_engine("postgresql+psycopg2://postgres:postgres@localhost:5432/energy_prediction")

# Funkcja do wstawiania danych do tabeli calendar
def insert_calendar(df, engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            for _, row in df.iterrows():
                query = text(f"""
                    INSERT INTO calendar (date, is_holiday, day_of_week)
                    VALUES ('{row['date']}', {row['is_holiday']}, {row['day_of_week']})
                    ON CONFLICT (date) DO NOTHING;
                """)
                print(f"[DEBUG] Query: {query}")
                connection.execute(query)
            transaction.commit()
            print("[INFO] Transaction committed for table calendar.")
        except Exception as e:
            transaction.rollback()
            print(f"[ERROR] Transaction rolled back for table calendar: {e}")
        finally:
            transaction.close()

# Wstaw dane do tabeli calendar
insert_calendar(df_calendar, engine)

print("Dane zostały zaimportowane do tabeli calendar.")

# --- Import danych do tabeli pv_production ---
# Przygotuj dane do tabeli pv_production
pv_cols = ["date", "hour", "produced_energy"]
df_pv = df[pv_cols].copy()
df_pv["type"] = "real"  # ustawiamy ręcznie
df_pv["object_id"] = 1  # lub inny sposób ustalania object_id jeśli masz wiele obiektów

# Usuń wiersze z brakującą datą lub godziną
pv_required = ["date", "hour", "produced_energy", "type", "object_id"]
df_pv = df_pv.dropna(subset=["date", "hour"])

# Funkcja do wstawiania danych do tabeli pv_production
def insert_pv_production(df, engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            for _, row in df.iterrows():
                query = text(f"""
                    INSERT INTO pv_production (date, hour, produced_energy, type, object_id)
                    VALUES ('{row['date']}', {row['hour']}, {row['produced_energy']}, '{row['type']}', {row['object_id']})
                    ON CONFLICT (date, hour, object_id, type) DO NOTHING;
                """)
                print(f"[DEBUG] Query: {query}")
                connection.execute(query)
            transaction.commit()
            print("[INFO] Transaction committed for table pv_production.")
        except Exception as e:
            transaction.rollback()
            print(f"[ERROR] Transaction rolled back for table pv_production: {e}")
        finally:
            transaction.close()

# Wstaw dane do tabeli pv_production
insert_pv_production(df_pv[pv_required], engine)

print("Dane zostały zaimportowane do tabeli pv_production.")

# --- Import danych do tabeli sold_energy ---
# Przygotuj dane do tabeli sold_energy
sold_cols = ["date", "hour", "sold_energy"]
df_sold = df[sold_cols].copy()
df_sold["type"] = "real"  # ustawiamy ręcznie
# Jeśli masz wiele obiektów, zmień object_id odpowiednio
df_sold["object_id"] = 1

# Usuń wiersze z brakującą datą lub godziną
df_sold = df_sold.dropna(subset=["date", "hour"])
sold_required = ["date", "hour", "sold_energy", "type", "object_id"]

# Funkcja do wstawiania danych do tabeli sold_energy
def insert_sold_energy(df, engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            for _, row in df.iterrows():
                query = text(f"""
                    INSERT INTO sold_energy (date, hour, sold_energy, type, object_id)
                    VALUES ('{row['date']}', {row['hour']}, {row['sold_energy']}, '{row['type']}', {row['object_id']})
                    ON CONFLICT (date, hour, object_id, type) DO NOTHING;
                """)
                print(f"[DEBUG] Query: {query}")
                connection.execute(query)
            transaction.commit()
            print("[INFO] Transaction committed for table sold_energy.")
        except Exception as e:
            transaction.rollback()
            print(f"[ERROR] Transaction rolled back for table sold_energy: {e}")
        finally:
            transaction.close()

# Wstaw dane do tabeli sold_energy
insert_sold_energy(df_sold[sold_required], engine)

print("Dane zostały zaimportowane do tabeli sold_energy.")

# --- Import danych do tabeli weather ---
# Przygotuj dane do tabeli weather
weather_cols = ["date", "hour", "temp", "cloud", "gti"]
df_weather = df[weather_cols].copy()
df_weather["type"] = "real"  # ustawiamy ręcznie

# Usuń wiersze z brakującą datą lub godziną
df_weather = df_weather.dropna(subset=["date", "hour"])
weather_required = ["date", "hour", "temp", "cloud", "gti", "type"]

# Funkcja do wstawiania danych do tabeli weather
def insert_weather(df, engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            for _, row in df.iterrows():
                query = text(f"""
                    INSERT INTO weather (date, hour, temp, cloud, gti, type)
                    VALUES ('{row['date']}', {row['hour']}, {row['temp']}, {row['cloud']}, {row['gti']}, '{row['type']}')
                    ON CONFLICT (date, hour, type) DO NOTHING;
                """)
                print(f"[DEBUG] Query: {query}")
                connection.execute(query)
            transaction.commit()
            print("[INFO] Transaction committed for table weather.")
        except Exception as e:
            transaction.rollback()
            print(f"[ERROR] Transaction rolled back for table weather: {e}")
        finally:
            transaction.close()

# Wstaw dane do tabeli weather
insert_weather(df_weather[weather_required], engine)

print("Dane zostały zaimportowane do tabeli weather.")
