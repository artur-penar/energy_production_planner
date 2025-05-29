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
