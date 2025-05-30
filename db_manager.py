from sqlalchemy import create_engine
import pandas as pd

class DBManager:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)

    def read_table(self, table_name):
        return pd.read_sql_table(table_name, self.engine)

    def write_table(self, df, table_name, if_exists='replace'):
        df.to_sql(table_name, self.engine, if_exists=if_exists, index=False)

db = DBManager("postgresql+psycopg2://postgres:postgres@localhost:5432/energy_prediction")
df = db.read_table("calendar")
print(df.head())  # Wyświetl pierwsze 5 wierszy tabeli
# Jeśli chcesz wyświetlić całą tabelę, użyj print(df)
# print(df)

