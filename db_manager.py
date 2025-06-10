from sqlalchemy import create_engine, text
import pandas as pd
import holidays

class DBManager:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)

    def clear_and_reset_tables(self):
        # Usuwa wszystkie dane i resetuje liczniki id w obu tabelach
        with self.engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE pv_production RESTART IDENTITY;"))
            conn.execute(text("TRUNCATE TABLE sold_energy RESTART IDENTITY;"))
        print("Tabele pv_production i sold_energy zostały wyczyszczone, liczniki id zresetowane.")

    def import_from_excel_to_two_tables(self, excel_path, object_id, type_value="real"):
        # Wczytaj dane z Excela
        df = pd.read_excel(excel_path)
        df.columns = df.columns.str.strip()
        df['date'] = pd.to_datetime(df['date'], dayfirst=True).dt.date

        # Przygotuj dane pogodowe
        weather_cols = ['date', 'hour', 'temp', 'cloud', 'gti']
        weather_df = df[weather_cols].copy().dropna(subset=['temp', 'cloud', 'gti'])
        weather_df['type'] = type_value  # lub inna wybrana wartość

        # Przygotuj dane do pv_production
        pv_df = df[['date', 'hour', 'produced_energy']].copy()
        pv_df = pv_df.dropna(subset=['produced_energy'])
        pv_df['type'] = type_value
        pv_df['object_id'] = object_id

        # Przygotuj dane do sold_energy
        sold_df = df[['date', 'hour', 'sold_energy']].copy()
        sold_df = sold_df.dropna(subset=['sold_energy'])
        sold_df['type'] = type_value
        sold_df['object_id'] = object_id

        # Wstaw do tabeli weather z ON CONFLICT DO NOTHING
        with self.engine.begin() as conn:
            for _, row in weather_df.iterrows():
                conn.execute(text("""
                    INSERT INTO weather (date, hour, temp, cloud, gti, type)
                    VALUES (:date, :hour, :temp, :cloud, :gti, :type)
                    ON CONFLICT (date, hour, type) DO NOTHING
                """), row.to_dict())

        # Pozostałe tabele mogą być przez to_sql
        pv_df.to_sql("pv_production", self.engine, if_exists='append', index=False)
        sold_df.to_sql("sold_energy", self.engine, if_exists='append', index=False)

        print(f"Wstawiono {len(weather_df)} rekordów do weather, "
              f"{len(pv_df)} do pv_production i {len(sold_df)} do sold_energy.")

    def import_predicted_weather_from_api(self, forecast_receiver):
        """
        Pobiera dane pogodowe (prognozowane) za pomocą obiektu ForecastWeatherDataReceiver
        i zapisuje je do tabeli weather w bazie danych z kolumną 'type' = 'predicted'.
        Nadpisuje istniejące wpisy (ON CONFLICT DO UPDATE) w kolumnach temp, cloud, gti.
        """
        # 1. Pobierz DataFrame z API
        df = forecast_receiver.fetch_forecast_data()

        # 2. Dopasuj nazwy kolumn
        df = df.rename(columns={
            "temperature_2m": "temp",
            "cloud_cover": "cloud",
            "global_tilted_irradiance": "gti"
        })

        # 3. Dodaj kolumnę 'hour' i zredukuj kolumnę 'date' do dnia
        df['hour'] = df['date'].dt.hour
        df['date'] = df['date'].dt.date

        # 4. Oznacz dane jako predicted
        df['type'] = 'predicted'

        # 5. Przepisz kolumny do nowego DataFrame (lub bezpośrednio iteruj po df)
        cols_to_insert = ['date', 'hour', 'temp', 'cloud', 'gti', 'type']
        weather_df = df[cols_to_insert].dropna(subset=['temp', 'cloud', 'gti'])

        # 6. Użyj surowego zapytania INSERT ... ON CONFLICT DO UPDATE
        with self.engine.begin() as conn:
            for _, row in weather_df.iterrows():
                conn.execute(text("""
                    INSERT INTO weather (date, hour, temp, cloud, gti, type)
                    VALUES (:date, :hour, :temp, :cloud, :gti, :type)
                    ON CONFLICT (date, hour, type)
                    DO UPDATE SET
                        temp = EXCLUDED.temp,
                        cloud = EXCLUDED.cloud,
                        gti = EXCLUDED.gti
                """), row.to_dict())

        print(f"Wstawiono lub zaktualizowano {len(weather_df)} rekordów prognozy (type='predicted') w tabeli weather.")

    def get_training_data(self):
        """
        Zwraca DataFrame z danymi do nauki modelu (łącząc dane pogodowe i produkcję).
        """
        query = text("""
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
        """)
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
        query = text("""
            SELECT
                s.date,
                s.hour,
                p.produced_energy,
                s.sold_energy
            FROM sold_energy s
            JOIN pv_production p
              ON s.date = p.date AND s.hour = p.hour
            WHERE s.sold_energy IS NOT NULL
        """)
        df = pd.read_sql(query, self.engine)
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.month
        df["day_of_week"] = df["date"].dt.weekday  # 0=poniedziałek, 6=niedziela

        import holidays
        pl_holidays = holidays.Poland()
        df["is_holiday"] = df["date"].isin(pl_holidays).astype(int)

        df["date"] = df["date"].dt.date  # jeśli chcesz mieć datę bez czasu
        return df

if __name__ == "__main__":
    db = DBManager("postgresql+psycopg2://postgres:postgres@localhost:5432/energy_prediction")
    # db.clear_and_reset_tables()
    # excel_path = r"C:\Users\Użytkownik1\Desktop\python_scripts\energy_production_planner\data\input\historical_data.xlsx"
    # db.import_from_excel_to_two_tables(excel_path, object_id=1, type_value="real")
    # print(db.get_training_data())
    print(db.get_sold_energy_training_data())
