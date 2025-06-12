import holidays
import pandas as pd
from sqlalchemy import Table, MetaData
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import insert


class DBManager:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)

    def get_latest_pv_production_date(self, type_value="real"):
        """
        Zwraca ostatnią datę z tabeli pv_production, gdzie type='real'.
        """
        query = text(
            """
            SELECT MAX(date) AS last_real_date
            FROM pv_production
            WHERE type = :type_value 
        """
        )
        with self.engine.connect() as conn:
            result = conn.execute(query, {"type_value": type_value}).fetchone()
        return result[0] if result else None

    def get_latest_weather_date(self, type_value="real"):
        """
        Zwraca ostatnią datę z tabeli weather, gdzie type='real'.
        """
        query = text(
            """
            SELECT MAX(date) AS last_real_date
            FROM weather
            WHERE type = :type_value 
        """
        )
        with self.engine.connect() as conn:
            result = conn.execute(query, {"type_value": type_value}).fetchone()
        return result[0] if result else None

    def is_weather_day_complete(self, last_date=None, type_value="real"):
        """
        Sprawdza, czy ostatni dzień z tabeli weather (type='real') ma pełne dane dla każdej godziny.
        Zwraca True, jeśli wszystkie godziny są obecne, w przeciwnym razie False.
        """
        if not last_date:
            return False

        query = text(
            """
            SELECT COUNT(*) AS hour_count
            FROM weather
            WHERE date = :date AND type = :type_value
        """
        )
        with self.engine.connect() as conn:
            result = conn.execute(
                query, {"date": last_date, "type_value": type_value}
            ).fetchone()

        return result[0] == 24

    def clear_and_reset_tables(self):
        # Usuwa wszystkie dane i resetuje liczniki id w obu tabelach
        with self.engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE pv_production RESTART IDENTITY;"))
            conn.execute(text("TRUNCATE TABLE sold_energy RESTART IDENTITY;"))
        print(
            "Tabele pv_production i sold_energy zostały wyczyszczone, liczniki id zresetowane."
        )

    def _read_and_prepare_excel_data(self, excel_path):
        df = pd.read_excel(excel_path)
        df.columns = df.columns.str.strip()
        df["date"] = pd.to_datetime(df["date"], dayfirst=True).dt.date
        return df

    def _filter_new_data(self, df, latest_date):
        if latest_date:
            return df[df["date"] > latest_date]
        return df

    def _prepare_pv_production_df(self, df, object_id, type_value):
        pv_cols = ["date", "hour", "produced_energy"]
        return (
            df[pv_cols]
            .dropna(subset=["produced_energy"])
            .assign(type=type_value, object_id=object_id)
        )

    def _prepare_sold_energy_df(self, df, object_id, type_value):
        sold_cols = ["date", "hour", "sold_energy"]
        return (
            df[sold_cols]
            .dropna(subset=["sold_energy"])
            .assign(type=type_value, object_id=object_id)
        )

    def _insert_ignore_duplicates(self, table_name, data_df, unique_cols):
        if data_df.empty:
            return
        meta = MetaData()
        table = Table(table_name, meta, autoload_with=self.engine)
        stmt = (
            insert(table)
            .values(data_df.to_dict(orient="records"))
            .on_conflict_do_nothing(index_elements=unique_cols)
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def import_data_from_excel(self, excel_path, object_id, type_value="real"):
        """
        Importuje dane z pliku Excel do tabel pv_production i sold_energy.
        Pomija duplikaty na podstawie (date, hour, type, object_id).
        """
        df = self._read_and_prepare_excel_data(excel_path)
        latest_date = self.get_latest_pv_production_date(type_value=type_value)
        print(f"Ostatnia data w bazie dla {type_value}: {latest_date}")
        df = self._filter_new_data(df, latest_date)
        pv_df = self._prepare_pv_production_df(df, object_id, type_value)
        sold_df = self._prepare_sold_energy_df(df, object_id, type_value)
        self._insert_ignore_duplicates(
            "pv_production", pv_df, ["date", "hour", "type", "object_id"]
        )
        self._insert_ignore_duplicates(
            "sold_energy", sold_df, ["date", "hour", "type", "object_id"]
        )
        print("Przykładowe dane pv_production:\n", pv_df.head())
        print("Przykładowe dane sold_energy:\n", sold_df.head())
        print(
            f"Wstawiono {len(pv_df)} do pv_production i {len(sold_df)} do sold_energy. (duplikaty pominięte)"
        )

    def get_pv_production_training_data(self):
        """
        Zwraca DataFrame z danymi do nauki modelu (łącząc dane pogodowe i produkcję).
        """
        query = text(
            """
            SELECT
                p.date,
                p.hour,
                w.temp,
                w.cloud,
                w.gti,
                p.produced_energy
            FROM pv_production p
            JOIN weather w
              ON p.date = w.date AND p.hour = w.hour AND w.type = 'real'
            WHERE p.produced_energy IS NOT NULL
        """
        )
        df = pd.read_sql(query, self.engine)
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.month
        df["date"] = df["date"].dt.date
        return df

    def get_sold_energy_training_data(self):
        """
        Zwraca DataFrame z danymi do nauki modelu dla energii oddanej (sold_energy),
        wyliczając cechy month, day_of_week, is_holiday.
        """
        query = text(
            """
            SELECT
                s.date,
                s.hour,
                p.produced_energy,
                s.sold_energy
            FROM sold_energy s
            JOIN pv_production p
              ON s.date = p.date AND s.hour = p.hour
            WHERE s.sold_energy IS NOT NULL
        """
        )
        df = pd.read_sql(query, self.engine)
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.month
        df["day_of_week"] = df["date"].dt.weekday  # 0=poniedziałek, 6=niedziela

        pl_holidays = holidays.Poland(years=df["date"].dt.year.unique())
        print(f"Znaleziono {len(pl_holidays)} świąt w latach: {df['date'].dt.year.unique()}")
        print(f"Święta: {pl_holidays}")
        # is_holiday: 1 jeśli święto lub niedziela, 0 w przeciwnym razie
        df["is_holiday"] = (
            df["date"].isin(pl_holidays) | (df["day_of_week"] == 6)
        ).astype(int)

        df["date"] = df["date"].dt.date  # jeśli chcesz mieć datę bez czasu
        return df

    def save_weather_data(self, df, type_value="real"):
        """
        Zapisuje dane pogodowe z DataFrame do tabeli weather w bazie danych.
        Zakłada, że df ma kolumny: date, hour, temp, cloud, gti (nazwy zgodne z bazą).
        Wstawia lub aktualizuje rekordy według klucza (date, hour, type).
        """
        # Upewnij się, że kolumny są odpowiednio nazwane
        df = df.rename(
            columns={
                "temperature_2m": "temp",
                "cloud_cover": "cloud",
                "global_tilted_irradiance": "gti",
                "global_tilted_irradiance_instant": "gti",
            }
        )
        df = df.copy()
        df["hour"] = pd.to_datetime(df["date"]).dt.hour
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["type"] = type_value
        cols_to_insert = ["date", "hour", "temp", "cloud", "gti", "type"]
        weather_df = df[cols_to_insert].dropna(subset=["temp", "cloud", "gti"])
        with self.engine.begin() as conn:
            for _, row in weather_df.iterrows():
                conn.execute(
                    text(
                        """
                        INSERT INTO weather (date, hour, temp, cloud, gti, type)
                        VALUES (:date, :hour, :temp, :cloud, :gti, :type)
                        ON CONFLICT (date, hour, type)
                        DO UPDATE SET
                            temp = EXCLUDED.temp,
                            cloud = EXCLUDED.cloud,
                            gti = EXCLUDED.gti
                        """
                    ),
                    row.to_dict(),
                )
        print(
            f"Wstawiono lub zaktualizowano {len(weather_df)} rekordów do tabeli weather."
        )


if __name__ == "__main__":
    db = DBManager(
        "postgresql+psycopg2://postgres:postgres@localhost:5432/energy_prediction"
    )
    # db.clear_and_reset_tables()
    # excel_path = r"C:\Users\Użytkownik1\Desktop\python_scripts\energy_production_planner\data\input\historical_data.xlsx"
    # db.import_from_excel_to_two_tables(excel_path, object_id=1, type_value="real")
    # print(db.get_training_data())
    print(db.get_sold_energy_training_data())
