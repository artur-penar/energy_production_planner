import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

class HistoricalWeatherDataReceiver:
    def __init__(self, latitude, longitude, start_date, end_date, output_file):
        self.latitude = latitude
        self.longitude = longitude
        self.start_date = start_date
        self.end_date = end_date
        self.output_file = output_file
        self.cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
        self.retry_session = retry(self.cache_session, retries=5, backoff_factor=0.2)
        self.openmeteo = openmeteo_requests.Client(session=self.retry_session)

    def fetch_and_save(self):
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "hourly": ["temperature_2m", "cloud_cover", "global_tilted_irradiance_instant"]
        }
        responses = self.openmeteo.weather_api(url, params=params)
        response = responses[0]
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()}{response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_cloud_cover = hourly.Variables(1).ValuesAsNumpy()
        hourly_global_tilted_irradiance_instant = hourly.Variables(2).ValuesAsNumpy()

        hourly_data = {"date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        )}
        hourly_data["temperature_2m"] = hourly_temperature_2m
        hourly_data["cloud_cover"] = hourly_cloud_cover
        hourly_data["global_tilted_irradiance_instant"] = hourly_global_tilted_irradiance_instant

        hourly_dataframe = pd.DataFrame(data=hourly_data)
        hourly_dataframe.to_csv(self.output_file, index=False)
        print(f"Data saved to {self.output_file}")

if __name__ == "__main__":
    receiver = HistoricalWeatherDataReceiver(
        latitude=49.6887,
        longitude=21.7706,
        start_date="2025-01-01",
        end_date="2025-05-24",
        output_file="data/weather/historical_weather.csv"
    )
    receiver.fetch_and_save()