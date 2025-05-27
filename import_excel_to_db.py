import pandas as pd
from sqlalchemy import create_engine, Table, MetaData  # Import Table and MetaData
from sqlalchemy.sql import text  # Import funkcji text

# Wczytaj dane z Excela
excel_path = "data/archive/historical_production.xlsx"
df = pd.read_excel(excel_path)

# Dodaj kolumnę type
df["type"] = "real"

# Połącz się z bazą PostgreSQL
# UZUPEŁNIJ danymi do swojej bazy:
engine = create_engine("postgresql+psycopg2://postgres:postgres@localhost:5432/energy_prediction")

# Funkcja do wstawiania danych z obsługą ON CONFLICT za pomocą surowych zapytań SQL
def insert_with_raw_sql(df, table_name, engine, unique_columns):
    with engine.connect() as connection:
        for _, row in df.iterrows():
            columns = ', '.join(row.index)
            values = ', '.join([
                f"'{v}'" if isinstance(v, (str, pd.Timestamp)) else str(v) for v in row.values
            ])
            conflict_columns = ', '.join(unique_columns)

            query = text(f"""
                INSERT INTO {table_name} ({columns})
                VALUES ({values})
                ON CONFLICT ({conflict_columns}) DO NOTHING;
            """)
            connection.execute(query)

# Zapisz dane do tabeli pv_production
pv_cols = ["date", "hour", "produced_energy", "type"]  # Usuń `object_id` z listy kolumn
df_pv = df[pv_cols].copy()
df_pv.loc[:, "object_id"] = 1  # Dodaj id obiektu ręcznie
insert_with_raw_sql(df_pv, "pv_production", engine, ["date", "hour", "object_id"])

# Zapisz dane do tabeli sold_energy
sold_cols = ["date", "hour", "sold_energy", "type", "is_holiday"]  # Usuń `object_id` z listy kolumn
df_sold = df[sold_cols].copy()
df_sold.loc[:, "object_id"] = 1  # Dodaj id obiektu ręcznie
df_sold.loc[:, "is_holiday"] = df_sold["is_holiday"].astype(bool)  # Rzutowanie na BOOLEAN
insert_with_raw_sql(df_sold, "sold_energy", engine, ["date", "hour", "object_id"])

# Zapisz dane do tabeli weather
weather_cols = ["date", "hour", "temp", "cloud", "gti", "type"]
df_weather = df[weather_cols].copy()
insert_with_raw_sql(df_weather, "weather", engine, ["date", "hour"])

print("Dane zostały zaimportowane do bazy.")
