from sqlalchemy import create_engine, text
import pandas as pd

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

        # Wstaw do tabel weather, pv_production, sold_energy
        weather_df.to_sql("weather", self.engine, if_exists='append', index=False)
        pv_df.to_sql("pv_production", self.engine, if_exists='append', index=False)
        sold_df.to_sql("sold_energy", self.engine, if_exists='append', index=False)

        print(f"Wstawiono {len(weather_df)} rekordów do weather, "
              f"{len(pv_df)} do pv_production i {len(sold_df)} do sold_energy.")

    def import_predicted_weather_from_api(self, forecast_receiver):
        """
        Pobiera dane pogodowe (prognozowane) za pomocą obiektu ForecastWeatherDataReceiver
        i zapisuje je do tabeli weather w bazie danych z kolumną 'type' = 'predicted'.
        """
        # 1. Pobierz DataFrame z API
        df = forecast_receiver.fetch_forecast_data()

        # 2. Dopasuj nazwy kolumn z ForecastWeatherDataReceiver do tabeli weather
        #    (np. temperature_2m -> temp, cloud_cover -> cloud, global_tilted_irradiance -> gti)
        df = df.rename(columns={
            "temperature_2m": "temp",
            "cloud_cover": "cloud",
            "global_tilted_irradiance": "gti"
        })

        # 3. Dodaj kolumnę 'hour' z daty (o ile potrzebujesz jej do klucza unikalnego w bazie)
        df['hour'] = df['date'].dt.hour

        # 4. Data w kolumnie 'date' – tylko część dzienna bez godzin
        df['date'] = df['date'].dt.date

        # 5. Oznacz dane jako predicted 
        df['type'] = 'predicted'

        # 6. Wstaw do tabeli weather
        #    Zwróć uwagę, że kolumny w DF muszą odpowiadać kolumnom w tabeli weather (date, hour, temp, cloud, gti, type)
        cols_to_insert = ['date', 'hour', 'temp', 'cloud', 'gti', 'type']
        weather_df = df[cols_to_insert].dropna(subset=['temp', 'cloud', 'gti'])

        weather_df.to_sql("weather", self.engine, if_exists='append', index=False)

        print(f"Wstawiono {len(weather_df)} rekordów prognozy (type='predicted') do tabeli weather.")

if __name__ == "__main__":
    db = DBManager("postgresql+psycopg2://postgres:postgres@localhost:5432/energy_prediction")
    db.clear_and_reset_tables()
    excel_path = r"C:\Users\Użytkownik1\Desktop\python_scripts\energy_production_planner\data\input\historical_data.xlsx"
    db.import_from_excel_to_two_tables(excel_path, object_id=1, type_value="real")
