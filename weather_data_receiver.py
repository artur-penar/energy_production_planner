import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from db_manager import (
    DBManager,
)  # Zakładam, że masz plik db_manager.py z klasą DBManager


class ForecastWeatherDataReceiver:
    API_URL = "https://api.open-meteo.com/v1/forecast"
    DEFAULT_HOURLY = ["temperature_2m", "cloud_cover", "global_tilted_irradiance"]

    def __init__(self, latitude, longitude, output_file, past_days=1, forecast_days=1):
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = "Europe/Warsaw"  # Możesz zmienić na inny strefę czasową
        self.output_file = output_file
        self.past_days = past_days
        self.forecast_days = forecast_days
        self.cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
        self.retry_session = retry(self.cache_session, retries=5, backoff_factor=0.2)
        self.openmeteo = openmeteo_requests.Client(session=self.retry_session)

    def get_api_params(self):
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone,
            "hourly": self.DEFAULT_HOURLY,
            "past_days": self.past_days,
            "forecast_days": self.forecast_days,
        }

    def print_api_metadata(self, response):
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()}{response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

    def fetch_forecast_data(self):
        """Pobiera prognozę pogodową z API i zwraca DataFrame."""
        params = self.get_api_params()
        responses = self.openmeteo.weather_api(self.API_URL, params=params)
        response = responses[0]

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
            )
        }
        hourly_data["temperature_2m"] = hourly_temperature_2m
        hourly_data["cloud_cover"] = hourly_cloud_cover
        hourly_data["global_tilted_irradiance"] = hourly_global_tilted_irradiance

        df = pd.DataFrame(data=hourly_data)
        if pd.api.types.is_datetime64_any_dtype(df["date"]):
            df["date"] = df["date"].dt.tz_localize(None)

        df = self.shift_hour_dst_only(df)
        return df

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

    def save_to_excel(self, df, excel_path):
        df.to_excel(excel_path, index=False)
        print(f"Data saved to {excel_path}")

    def display(self, df, n=5):
        print(df.head(n))

    def shift_hour_dst_only(self, df, date_col="date"):
        """
        Bezpieczna konwersja czasów do lokalnej strefy z obsługą DST/ambiguous,
        bez wywoływania .dst() na NaT. Zwraca DataFrame z znormalizowaną kolumną date.
        """
        df = df.copy()
        # upewnij się że to datetime
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        # jeśli są tylko naive timestamps traktujemy je jako UTC (jeśli dane przyszły z API z utc)
        try:
            series_tz = getattr(df[date_col].dt, "tz", None)
        except Exception:
            series_tz = None

        if series_tz is None:
            # lokalizujemy do UTC (bezpieczne), by móc konwertować do strefy docelowej
            df[date_col] = df[date_col].dt.tz_localize("UTC")

        # spróbuj scentralizowanej konwersji; jeśli zadziała -> OK
        try:
            df[date_col] = df[date_col].dt.tz_convert(self.timezone)
        except Exception:
            # fallback: per-row, bez wywoływania .dst() na NaT, obsługa ambiguous/nonexistent
            def convert_safe(ts):
                if pd.isna(ts):
                    return pd.NaT
                try:
                    # jeśli ts jest tz-aware, konwertuj
                    if ts.tzinfo is not None:
                        return ts.tz_convert(self.timezone)
                    # jeśli naive (nie powinno się zdarzyć po lokalizacji), spróbuj zlokalizować do target tz
                    return ts.tz_localize(self.timezone, ambiguous="infer", nonexistent="shift_forward")
                except Exception:
                    # ostateczny fallback: zwróć oryginalny ts (bez zmiany strefy)
                    return ts

            df[date_col] = df[date_col].apply(convert_safe)

        # usuń info o strefie (jeśli chcesz naive lokalne daty)
        try:
            df[date_col] = df[date_col].dt.tz_localize(None)
        except Exception:
            # jeśli nie da się usunąć strefy, zostaw jak jest — ważne, żeby nie było NaT przy .dst()
            pass

        return df

    def run(self):
        df = self.fetch_forecast_data()
        self.save_to_excel(df, self.output_file)


if __name__ == "__main__":
    receiver = ForecastWeatherDataReceiver(
        latitude=49.6887,
        longitude=21.7706,
        output_file="data/weather/forecast_weather.xlsx",  # Możesz pominąć eksport do pliku, to tylko placeholder
        past_days=1,
        forecast_days=4,
    )
    receiver.run()
