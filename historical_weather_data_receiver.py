import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry


class HistoricalWeatherDataReceiver:
    def __init__(self, latitude, longitude, start_date, end_date, output_file=None):
        self.latitude = latitude
        self.longitude = longitude
        self.start_date = start_date
        self.end_date = end_date
        self.output_file = output_file
        self.cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
        self.retry_session = retry(self.cache_session, retries=5, backoff_factor=0.2)
        self.openmeteo = openmeteo_requests.Client(session=self.retry_session)

    def print_api_metadata(self, response):
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()}{response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

    def fetch_historical_data(self):
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "hourly": [
                "temperature_2m",
                "cloud_cover",
                "global_tilted_irradiance_instant",
            ],
        }
        responses = self.openmeteo.weather_api(url, params=params)
        response = responses[0]
        self.print_api_metadata(response)

        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_cloud_cover = hourly.Variables(1).ValuesAsNumpy()
        hourly_global_tilted_irradiance = hourly.Variables(2).ValuesAsNumpy()

        hourly_data = {
            "date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left",
            ),
            "temperature_2m": hourly_temperature_2m,
            "cloud_cover": hourly_cloud_cover,
            "global_tilted_irradiance": hourly_global_tilted_irradiance,  # Ujednolicona nazwa
        }
        df = pd.DataFrame(data=hourly_data)
        if pd.api.types.is_datetime64_any_dtype(df["date"]):
            df["date"] = df["date"].dt.tz_localize(None)
        return df

    def save_to_excel(self, df, excel_path):
        df.to_excel(excel_path, index=False)
        print(f"Data saved to {excel_path}")

    def display(self, df, n=5):
        print(df.head(n))

    def filter_complete_days(self, df):
        """
        Zwraca DataFrame zawierający tylko te daty, które mają kompletne dane pogodowe (24 godziny: 0-23) i brak NaN.
        """
        df["date_only"] = pd.to_datetime(df["date"]).dt.date

        def is_complete_and_no_nan(x):
            return (
                set(x["date"].dt.hour) == set(range(24)) and not x.isnull().any().any()
            )

        complete_days = df.groupby("date_only").filter(is_complete_and_no_nan)
        return complete_days.drop(columns=["date_only"])

    def run(self):
        df = self.fetch_historical_data()
        df = self.filter_complete_days(df)  # Filtruj tylko pełne dni
        self.save_to_excel(df, self.output_file)


if __name__ == "__main__":
    receiver = HistoricalWeatherDataReceiver(
        latitude=49.6887,
        longitude=21.7706,
        start_date="2025-06-08",
        end_date="2025-06-11",
        output_file="data/weather/historical_weather.xlsx",
    )
    receiver.run()
