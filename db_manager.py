import pandas as pd
import logging
import datetime
import holidays
import sql_queries
import pandas as pd
from sqlalchemy import Table, MetaData
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import insert
import numpy as np


class DBManager:

    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.logger = logging.getLogger(__name__)

    def get_latest_energy_production_date(self, type_value="real"):
        query = text(sql_queries.GET_LATEST_ENERGY_PRODUCTION_DATE)
        with self.engine.connect() as conn:
            result = conn.execute(query, {"type_value": type_value}).fetchone()
        return result[0] if result else None

    def get_latest_weather_date(self, type_value="real"):
        query = text(sql_queries.GET_LATEST_WEATHER_DATE)
        with self.engine.connect() as conn:
            result = conn.execute(query, {"type_value": type_value}).fetchone()
        return result[0] if result else None

    def is_weather_day_complete(self, last_date=None, type_value="real"):
        if not last_date:
            return False
        query = text(sql_queries.IS_WEATHER_DAY_COMPLETE)
        with self.engine.connect() as conn:
            result = conn.execute(
                query, {"date": last_date, "type_value": type_value}
            ).fetchone()
        return result[0] == 24

    def clear_and_reset_tables(self):
        # Usuwa wszystkie dane i resetuje liczniki id w obu tabelach
        with self.engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE energy_production RESTART IDENTITY;"))
            conn.execute(text("TRUNCATE TABLE sold_energy RESTART IDENTITY;"))
        self.logger.info(
            "Tabele produced_energy i sold_energy zostały wyczyszczone i zresetowane."
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

    def _prepare_produced_energy_df(self, df, object_id, type_value):
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
        Importuje dane z pliku Excel do tabel produced_energy i sold_energy.
        Pomija duplikaty na podstawie (date, hour, type, object_id).
        """
        df = self._read_and_prepare_excel_data(excel_path)
        latest_date = self.get_latest_energy_production_date(type_value=type_value)
        self.logger.info(f"Ostatnia data w bazie dla {type_value}: {latest_date}")

        df = self._filter_new_data(df, latest_date)
        pv_df = self._prepare_produced_energy_df(df, object_id, type_value)
        sold_df = self._prepare_sold_energy_df(df, object_id, type_value)
        self._insert_ignore_duplicates(
            "produced_energy", pv_df, ["date", "hour", "type", "object_id"]
        )
        self._insert_ignore_duplicates(
            "sold_energy", sold_df, ["date", "hour", "type", "object_id"]
        )
        self.logger.info(
            f"Import danych historycznych z pliku excel.\nWstawiono {len(pv_df)} do produced_energy i {len(sold_df)} do sold_energy (duplikaty pominięte)"
        )

    def get_produced_energy_training_data(self):
        """
        Zwraca DataFrame z danymi do nauki modelu (łącząc dane pogodowe i produkcję).
        """
        query = text(sql_queries.GET_PRODUCED_ENERGY_TRAINING_DATA)
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
        query = text(sql_queries.GET_SOLD_ENERGY_TRAINING_DATA)
        df = pd.read_sql(query, self.engine)
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.month
        df["day_of_week"] = df["date"].dt.weekday  # 0=poniedziałek, 6=niedziela

        pl_holidays = holidays.Poland(years=df["date"].dt.year.unique())
        self.logger.info(
            f"Znaleziono {len(pl_holidays)} świąt w latach: {df['date'].dt.year.unique()}"
        )
        # is_holiday: 1 jeśli święto lub niedziela, 0 w przeciwnym razie
        pl_holidays_dates = pd.to_datetime(list(pl_holidays)).date
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["is_holiday"] = (
            df["date"].isin(pl_holidays_dates) | (df["day_of_week"] == 6)
        ).astype(int)

        # Upewnij się, że kolumna date jest typu datetime przed użyciem .dt.date
        if not pd.api.types.is_datetime64_any_dtype(df["date"]):
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
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

        def get_oldest_date(weather_df):
            if not weather_df.empty:
                return weather_df["date"].min()
            return None

        def get_latest_date(weather_df):
            if not weather_df.empty:
                return weather_df["date"].max()
            return None

        with self.engine.begin() as conn:
            for _, row in weather_df.iterrows():
                conn.execute(
                    text(sql_queries.INSERT_OR_UPDATE_WEATHER),
                    row.to_dict(),
                )
        self.logger.info(
            f"Wstawiono lub zaktualizowano {len(weather_df)} typu {type_value} rekordów do tabeli weather.\nOd {get_oldest_date(weather_df)} do {get_latest_date(weather_df)}."
        )

    def get_produced_energy_prediction_data(self):
        """
        Pobiera dane z bazy do predykcji (rekordy z produced_energy, gdzie produced_energy jest NULL),
        łącząc z danymi pogodowymi.
        """
        query = text(sql_queries.GET_PRODUCED_ENERGY_PREDICTION_DATA)
        df = pd.read_sql(query, self.engine)
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.month
        df["date"] = df["date"].dt.date
        return df

    def update_predicted_produced_energy(self, df):
        """
        Aktualizuje kolumnę produced_energy w produced_energy na podstawie DataFrame (po predykcji).
        """
        with self.engine.begin() as conn:
            for _, row in df.iterrows():
                if pd.notna(row["produced_energy"]):
                    conn.execute(
                        text(sql_queries.UPDATE_PRODUCED_ENERGY),
                        {
                            "produced_energy": row["produced_energy"],
                            "date": row["date"],
                            "hour": row["hour"],
                            "type": row["type"],
                            "object_id": row["object_id"],
                        },
                    )
            self.logger.info(
                f"Zaktualizowano {len(df)} rekordów w tabeli produced_energy."
            )

    def update_predicted_sold_energy(self, df):
        """
        Aktualizuje kolumnę sold_energy w tabeli sold_energy na podstawie DataFrame (po predykcji).
        """
        with self.engine.begin() as conn:
            for _, row in df.iterrows():
                if pd.notna(row["sold_energy"]):
                    conn.execute(
                        text(sql_queries.UPDATE_SOLD_ENERGY),
                        {
                            "sold_energy": row["sold_energy"],
                            "date": row["date"],
                            "hour": row["hour"],
                            "type": row["type"],
                            "object_id": row["object_id"],
                        },
                    )
            self.logger.info(f"Zaktualizowano {len(df)} rekordów w tabeli sold_energy.")

    def clear_predicted_rows(self, from_date=None):
        """
        Usuwa rekordy typu 'predicted' z obu tabel: produced_energy i sold_energy od podanej daty (włącznie).
        Jeśli from_date nie jest podane, domyślnie czyści od dzisiaj.
        """

        if from_date is None:
            from_date = datetime.date.today()
        with self.engine.begin() as conn:
            conn.execute(
                text(sql_queries.DELETE_PRODUCED_ENERGY_PREDICTION),
                {"from_date": from_date},
            )
            conn.execute(
                text(sql_queries.DELETE_SOLD_ENERGY_PREDICTION),
                {"from_date": from_date},
            )

        self.logger.info(
            f"Usunięto rekordy typu 'predicted' z produced_energy i sold_energy od daty {from_date}."
        )

    def insert_empty_predicted_rows(self, object_id=1):
        """
        Wstawia puste rekordy (NULL) typu 'predicted' do obu tabel: produced_energy i sold_energy
        dla wszystkich dat/godzin z weather typu 'predicted'.
        """
        query = text(sql_queries.SELECT_DISTINCT_PREDICTED_WEATHER)
        df = pd.read_sql(query, self.engine)
        df["type"] = "predicted"
        df["object_id"] = object_id
        # produced_energy
        df_pv = df.copy()
        df_pv["produced_energy"] = None
        self._insert_ignore_duplicates(
            "produced_energy",
            df_pv[["date", "hour", "produced_energy", "type", "object_id"]],
            ["date", "hour", "type", "object_id"],
        )
        # sold_energy
        df_sold = df.copy()
        df_sold["sold_energy"] = None
        self._insert_ignore_duplicates(
            "sold_energy",
            df_sold[["date", "hour", "sold_energy", "type", "object_id"]],
            ["date", "hour", "type", "object_id"],
        )
        self.logger.info(
            f"Wstawiono puste rekordy typu 'predicted' do produced_energy i sold_energy dla {len(df)} dat/godzin. Od {df['date'].min()} do {df['date'].max()}."
        )

    def get_sold_energy_prediction_data(self):
        """
        Pobiera dane z bazy do predykcji (rekordy z sold_energy, gdzie sold_energy jest NULL),
        łącząc z danymi produkcji PV oraz wylicza cechy wymagane do predykcji.
        """
        query = text(sql_queries.GET_SOLD_ENERGY_PREDICTION_DATA)
        df = pd.read_sql(query, self.engine)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df["month"] = df["date"].dt.month
            df["day_of_week"] = df["date"].dt.weekday

            pl_holidays = holidays.Poland(years=df["date"].dt.year.unique())
            df["is_holiday"] = (
                df["date"].dt.date.isin(pl_holidays) | (df["day_of_week"] == 6)
            ).astype(int)
            df["date"] = df["date"].dt.date
        return df

    def get_energy_for_date(
        self, date, energy_type="produced", data_type="real", object_id=1
    ):
        """
        Zwraca DataFrame z danymi produkcji lub sprzedaży energii (historyczne lub prognozy) dla konkretnego dnia.
        energy_type: "produced" (wyprodukowana) lub "sold" (wprowadzona/sprzedana)
        data_type: "real" (historyczne) lub "predicted" (prognozy)
        """
        if energy_type == "produced":
            query = text(sql_queries.GET_PRODUCED_ENERGY_FOR_DATE)
        elif energy_type == "sold":
            query = text(sql_queries.GET_SOLD_ENERGY_FOR_DATE)
        else:
            raise ValueError("energy_type must be 'produced' or 'sold'")
        df = pd.read_sql(
            query,
            self.engine,
            params={"date": date, "data_type": data_type, "object_id": object_id},
        )
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df["month"] = df["date"].dt.month
            df["date"] = df["date"].dt.date
        return df

    def insert_real_energy_data(self, data_list, energy_type="sold", object_id=1):
        """
        Wprowadza dane rzeczywiste z GUI do bazy.
        data_list: [{"date": ..., "hour": ..., "sold_energy": ...}, ...] lub [{"date": ..., "hour": ..., "produced_energy": ...}, ...]
        energy_type: "sold" lub "produced"
        """
        df = pd.DataFrame(data_list)
        df["type"] = "real"
        df["object_id"] = object_id

        if energy_type == "sold":
            sold_df = df[["date", "hour", "sold_energy", "type", "object_id"]].dropna(
                subset=["sold_energy"]
            )
            self._insert_ignore_duplicates(
                "sold_energy", sold_df, ["date", "hour", "type", "object_id"]
            )
        elif energy_type == "produced":
            pv_df = df[["date", "hour", "produced_energy", "type", "object_id"]].dropna(
                subset=["produced_energy"]
            )
            self._insert_ignore_duplicates(
                "produced_energy", pv_df, ["date", "hour", "type", "object_id"]
            )

    def import_data_from_csv(self, csv_path, object_id, type_value="real"):
        """
        Importuje dane produkcji energii z pliku CSV (Timestamp;Value) do bazy dla wybranego object_id.
        """
        df = pd.read_csv(csv_path, sep=";", decimal=",")
        # Rozbij Timestamp na date i hour
        df["date"] = pd.to_datetime(df["Timestamp"]).dt.date.astype(str)
        df["hour"] = pd.to_datetime(df["Timestamp"]).dt.hour
        df["produced_energy"] = df["Value"]
        df["produced_energy"] = df["produced_energy"].astype(str).str.replace(",", ".")
        # Zamień 'Bad' i inne nieprawidłowe na NaN, ale NIE usuwaj tych wierszy
        df["produced_energy"] = pd.to_numeric(df["produced_energy"], errors="coerce")
        # Przygotuj DataFrame w formacie zgodnym z bazą
        pv_df = df[["date", "hour", "produced_energy"]].copy()
        pv_df["type"] = type_value
        pv_df["object_id"] = object_id
        # Wstaw dane do bazy (analogicznie jak w import_data_from_excel)
        self._insert_ignore_duplicates(
            "produced_energy", pv_df, ["date", "hour", "type", "object_id"]
        )
        return len(pv_df)

    def import_weather_from_csv(self, csv_path, type_value="real"):
        df = pd.read_csv(csv_path, sep=";", decimal=",")
        # Jeśli kolumna 'date' zawiera godzinę, wyodrębnij godzinę do osobnej kolumny
        df["hour"] = pd.to_datetime(df["date"]).dt.hour
        self.save_weather_data(df, type_value=type_value)

    def import_sold_energy_from_csv(self, csv_path, type_value="real", object_id=None):
        df = pd.read_csv(csv_path, sep=';', decimal=',', dtype=str)
        df.columns = df.columns.str.strip().str.replace('"', '')
        # Konwersja daty
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        # Wyodrębnij godzinę
        df['hour'] = df['date'].dt.hour
        # Zamień datę na samą datę (bez czasu)
        df['date'] = df['date'].dt.date
        # Konwersja energii
        df['sold_energy'] = df['sold_energy'].astype(str).str.replace(',', '.').astype(float)
        # Dodaj kolumny wymagane przez bazę
        df['type'] = type_value
        df['object_id'] = object_id
        # Usuń wiersze z brakującą datą, godziną lub energią
        df = df.dropna(subset=['date', 'hour', 'sold_energy'])
        # Wstaw do bazy
        self._insert_ignore_duplicates(
            "sold_energy",
            df[["date", "hour", "sold_energy", "type", "object_id"]],
            ["date", "hour", "type", "object_id"]
        )
 


if __name__ == "__main__":
    DB_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/energy_prediction"
    db_manager = DBManager(DB_URL)
    sold_energy_path = r"C:\Users\Użytkownik1\Desktop\python_scripts\energy_production_planner\sold_energy_2024_hour.csv"
    # db_manager.import_data_from_csv(file_path, object_id=2)
    db_manager.import_sold_energy_from_csv(sold_energy_path, type_value="real", object_id=2)
