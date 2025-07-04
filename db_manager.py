import logging
import datetime
import holidays
import pandas as pd
from sqlalchemy import Table, MetaData
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import insert

GET_LATEST_PV_PRODUCTION_DATE = """
SELECT MAX(date) AS last_real_date
FROM pv_production
WHERE type = :type_value"""


class DBManager:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.logger = logging.getLogger(__name__)

    def get_latest_pv_production_date(self, type_value="real"):
        """Zwraca ostatnią datę z tabeli pv_production, gdzie type='real'."""

        query = text(GET_LATEST_PV_PRODUCTION_DATE)
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
        self.logger.info(
            "Tabele pv_production i sold_energy zostały wyczyszczone i zresetowane."
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
        self.logger.info(f"Ostatnia data w bazie dla {type_value}: {latest_date}")

        df = self._filter_new_data(df, latest_date)
        pv_df = self._prepare_pv_production_df(df, object_id, type_value)
        sold_df = self._prepare_sold_energy_df(df, object_id, type_value)
        self._insert_ignore_duplicates(
            "pv_production", pv_df, ["date", "hour", "type", "object_id"]
        )
        self._insert_ignore_duplicates(
            "sold_energy", sold_df, ["date", "hour", "type", "object_id"]
        )
        self.logger.info(
            f"Import danych historycznych z pliku excel.\nWstawiono {len(pv_df)} do pv_production i {len(sold_df)} do sold_energy (duplikaty pominięte)"
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
              ON p.date = w.date AND p.hour = w.hour AND w.type = 'real' AND p.type = 'real'
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
              ON s.date = p.date AND s.hour = p.hour AND p.type = 'real' and s.type = 'real'
            WHERE s.sold_energy IS NOT NULL
        """
        )
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
        self.logger.info(
            f"Wstawiono lub zaktualizowano {len(weather_df)} typu {type_value} rekordów do tabeli weather.\nOd {get_oldest_date(weather_df)} do {get_latest_date(weather_df)}."
        )

    def get_pv_production_prediction_data(self):
        """
        Pobiera dane z bazy do predykcji (rekordy z pv_production, gdzie produced_energy jest NULL),
        łącząc z danymi pogodowymi.
        """
        query = text(
            """
            SELECT
                p.date,
                p.hour,
                w.temp,
                w.cloud,
                w.gti,
                p.produced_energy,
                p.type,
                p.object_id
            FROM pv_production p
            JOIN weather w
              ON p.date = w.date AND p.hour = w.hour AND w.type = 'predicted'
            WHERE p.produced_energy IS NULL
            """
        )
        df = pd.read_sql(query, self.engine)
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.month
        df["date"] = df["date"].dt.date
        return df

    def update_predicted_produced_energy(self, df):
        """
        Aktualizuje kolumnę produced_energy w pv_production na podstawie DataFrame (po predykcji).
        """
        with self.engine.begin() as conn:
            for _, row in df.iterrows():
                if pd.notna(row["produced_energy"]):
                    conn.execute(
                        text(
                            """
                            UPDATE pv_production
                            SET produced_energy = :produced_energy
                            WHERE date = :date AND hour = :hour AND type = :type AND object_id = :object_id
                            """
                        ),
                        {
                            "produced_energy": row["produced_energy"],
                            "date": row["date"],
                            "hour": row["hour"],
                            "type": row["type"],
                            "object_id": row["object_id"],
                        },
                    )
            self.logger.info(
                f"Zaktualizowano {len(df)} rekordów w tabeli pv_production."
            )

    def update_predicted_sold_energy(self, df):
        """
        Aktualizuje kolumnę sold_energy w tabeli sold_energy na podstawie DataFrame (po predykcji).
        """
        with self.engine.begin() as conn:
            for _, row in df.iterrows():
                if pd.notna(row["sold_energy"]):
                    conn.execute(
                        text(
                            """
                            UPDATE sold_energy
                            SET sold_energy = :sold_energy
                            WHERE date = :date AND hour = :hour AND type = :type AND object_id = :object_id
                            """
                        ),
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
        Usuwa rekordy typu 'predicted' z obu tabel: pv_production i sold_energy od podanej daty (włącznie).
        Jeśli from_date nie jest podane, domyślnie czyści od dzisiaj.
        """

        if from_date is None:
            from_date = datetime.date.today()
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "DELETE FROM pv_production WHERE type = 'predicted' AND date >= :from_date"
                ),
                {"from_date": from_date},
            )
            conn.execute(
                text(
                    "DELETE FROM sold_energy WHERE type = 'predicted' AND date >= :from_date"
                ),
                {"from_date": from_date},
            )

        self.logger.info(
            f"Usunięto rekordy typu 'predicted' z pv_production i sold_energy od daty {from_date}."
        )

    def insert_empty_predicted_rows(self, object_id=1):
        """
        Wstawia puste rekordy (NULL) typu 'predicted' do obu tabel: pv_production i sold_energy
        dla wszystkich dat/godzin z weather typu 'predicted'.
        """
        query = text(
            """
            SELECT DISTINCT date, hour
            FROM weather
            WHERE type = 'predicted'
            """
        )
        df = pd.read_sql(query, self.engine)
        df["type"] = "predicted"
        df["object_id"] = object_id
        # pv_production
        df_pv = df.copy()
        df_pv["produced_energy"] = None
        self._insert_ignore_duplicates(
            "pv_production",
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
            f"Wstawiono puste rekordy typu 'predicted' do pv_production i sold_energy dla {len(df)} dat/godzin. Od {df['date'].min()} do {df['date'].max()}."
        )

    def get_sold_energy_prediction_data(self):
        """
        Pobiera dane z bazy do predykcji (rekordy z sold_energy, gdzie sold_energy jest NULL),
        łącząc z danymi produkcji PV oraz wylicza cechy wymagane do predykcji.
        """
        query = text(
            """
            SELECT
                s.date,
                s.hour,
                p.produced_energy,
                s.sold_energy,
                s.type,
                s.object_id
            FROM sold_energy s
            JOIN pv_production p
              ON s.date = p.date AND s.hour = p.hour AND s.type = 'predicted' AND p.type = 'predicted'
            WHERE s.sold_energy IS NULL
            """
        )
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

    def get_energy_for_date(self, date, energy_type="produced", data_type="real", object_id=1):
        """
        Zwraca DataFrame z danymi produkcji lub sprzedaży energii (historyczne lub prognozy) dla konkretnego dnia.
        energy_type: "produced" (wyprodukowana) lub "sold" (wprowadzona/sprzedana)
        data_type: "real" (historyczne) lub "predicted" (prognozy)
        """
        if energy_type == "produced":
            table = "pv_production"
            value_col = "produced_energy"
            weather_join = True
        elif energy_type == "sold":
            table = "sold_energy"
            value_col = "sold_energy"
            weather_join = False  # zakładamy, że nie łączysz z weather dla sold_energy
        else:
            raise ValueError("energy_type must be 'produced' or 'sold'")

        if weather_join:
            query = text(f"""
                SELECT
                    p.date,
                    p.hour,
                    w.temp,
                    w.cloud,
                    w.gti,
                    p.{value_col}
                FROM {table} p
                JOIN weather w
                  ON p.date = w.date AND p.hour = w.hour AND w.type = :data_type AND p.type = :data_type
                WHERE p.{value_col} IS NOT NULL
                  AND p.date = :date
                  AND p.object_id = :object_id
                ORDER BY p.hour
            """)
        else:
            query = text(f"""
                SELECT
                    s.date,
                    s.hour,
                    s.{value_col}
                FROM {table} s
                WHERE s.{value_col} IS NOT NULL
                  AND s.date = :date
                  AND s.type = :data_type
                  AND s.object_id = :object_id
                ORDER BY s.hour
            """)

        df = pd.read_sql(query, self.engine, params={"date": date, "data_type": data_type, "object_id": object_id})
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df["month"] = df["date"].dt.month
            df["date"] = df["date"].dt.date
        return df
