from db_manager import DBManager
from historical_weather_data_receiver import HistoricalWeatherDataReceiver
from weather_data_receiver import WeatherDataReceiver

if __name__ == "__main__":
    db = DBManager("postgresql+psycopg2://postgres:postgres@localhost:5432/energy_prediction")
    receiver = HistoricalWeatherDataReceiver(
        latitude=49.6887,
        longitude=21.7706,
        start_date="2025-06-08",
        end_date="2025-06-11",
        output_file="data/weather/historical_weather.csv"
    )
    updater = WeatherDataReceiver(db, receiver)
    updater.update_real_weather()