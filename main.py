import pandas as pd
from db_manager import DBManager
from historical_weather_data_receiver import HistoricalWeatherDataReceiver

if __name__ == "__main__":
    db = DBManager(
        "postgresql+psycopg2://postgres:postgres@localhost:5432/energy_prediction"
    )
    receiver = HistoricalWeatherDataReceiver(
        latitude=49.6887,
        longitude=21.7706,
        start_date="2025-06-08",
        end_date="2025-06-11",
        output_file="data/weather/historical_weather.csv",
    )

    last_date = db.get_latest_weather_date("real")
    print(f"Ostatnia data w bazie: {last_date}")
    print(db.is_weather_day_complete(last_date, "real"))

    today = pd.Timestamp.now(tz="UTC").normalize().strftime("%Y-%m-%d")

    weather_data_receiver = HistoricalWeatherDataReceiver(
        latitude=49.6887,
        longitude=21.7706,
        start_date=last_date,
        end_date=today,
    )
    print(weather_data_receiver.filter_complete_days(weather_data_receiver.fetch_historical_data()))
