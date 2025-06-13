import logging
import pandas as pd
from db_manager import DBManager
from historical_weather_data_receiver import HistoricalWeatherDataReceiver
from weather_data_receiver import ForecastWeatherDataReceiver
from energy_production_predictor import EnergyProductionPredictor
from sold_energy_predictor import SoldEnergyPredictor

logging.basicConfig(level=logging.INFO)

DB_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/energy_prediction"
LATITUDE = 49.6887
LONGITUDE = 21.7706
HISTORICAL_FILE = "data/weather/historical_weather.xlsx"
FORECAST_FILE = "data/weather/forecast_weather.xlsx"


def save_weather(receiver, fetch_method, db, data_type):
    try:
        data = receiver.filter_complete_days(fetch_method())
        if not data.empty:
            db.save_weather_data(data, data_type)
            logging.info(f"{data_type.capitalize()} weather data saved to database.")
        else:
            logging.info(f"No {data_type} weather data to save.")
        return data
    except Exception as e:
        logging.error(f"Error saving {data_type} weather data: {e}")


def train_predictor(predictor, training_data):
    predictor.load_data(training_data)
    predictor.train_model()


if __name__ == "__main__":
    db = DBManager(DB_URL)
    last_date = db.get_latest_weather_date("real")
    today = pd.Timestamp.now(tz="UTC").normalize().strftime("%Y-%m-%d")

    historical_receiver = HistoricalWeatherDataReceiver(
        latitude=LATITUDE,
        longitude=LONGITUDE,
        output_file=HISTORICAL_FILE,
        start_date=last_date,
        end_date=today,
    )

    forecast_receiver = ForecastWeatherDataReceiver(
        latitude=LATITUDE,
        longitude=LONGITUDE,
        output_file=FORECAST_FILE,
        past_days=0,
        forecast_days=4,
    )

    historical_weather = historical_receiver.fetch_historical_data()
    print("Historical Weather Data:")
    print(historical_weather)

    save_weather(
        historical_receiver, historical_receiver.fetch_historical_data, db, "real"
    )

    save_weather(
        forecast_receiver, forecast_receiver.fetch_forecast_data, db, "predicted"
    )

    energy_predictor = EnergyProductionPredictor(
        input_path="data/input/production_to_predict.xlsx",
        output_pred_path="data/input/pv_predicted.xlsx",
        output_pivot_path="data/output/pv_pivot.xlsx",
    )

    sold_energy_predictor = SoldEnergyPredictor(
        input_path="data/input/pv_predicted.xlsx",
        output_pred_path="data/output/sold_predicted.xlsx",
        output_pivot_path="data/output/sold_pivot.xlsx",
    )

    excel_path = r"C:\Users\Użytkownik1\Desktop\python_scripts\energy_production_planner\data\input\production_to_predict.xlsx"
    db.import_data_from_excel(excel_path, object_id=1, type_value="real")

    energy_production_training_data = db.get_pv_production_training_data()
    train_predictor(energy_predictor, energy_production_training_data)

    sold_energy_training_data = db.get_sold_energy_training_data()
    train_predictor(sold_energy_predictor, sold_energy_training_data)

    db.clear_predicted_rows()
    db.insert_empty_predicted_rows(object_id=1)

    pv_prediction_data = db.get_pv_production_prediction_data()
    energy_predictor.load_data(pv_prediction_data)
    energy_predictor.predict_missing()
    db.update_predicted_produced_energy(energy_predictor.df)

    # Poprawiony workflow dla predykcji sold_energy
    sold_prediction_data = db.get_sold_energy_prediction_data()
    sold_energy_predictor.load_data(sold_prediction_data)
    sold_energy_predictor.predict_missing()
    db.update_predicted_sold_energy(sold_energy_predictor.df)

