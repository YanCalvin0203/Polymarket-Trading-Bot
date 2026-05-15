from typing import Any


class WeatherOracleSettings:
  """
  This class contains all the configuration variables for the oracle.
  """
  # ---- Ensemble ----------------------------------------

  ENSEMBLE_ENDPOINT: str = "https://ensemble-api.open-meteo.com/v1/ensemble"
  ENSEMBLE_QUERY_PARAMS: dict[str, Any] = {
    "hourly": ["temperature_2m"],
    "models": "ecmwf_ifs025",
    "timezone": "auto"
  }
  ENSEMBLE_COUNT: int = 51

  # ---- Observation -------------------------------------

  METAR_ENDPOINT: str = "https://aviationweather.gov/api/data/metar"
  METAR_QUERY_PARAMS: dict[str, Any] = {
    "format": "json"
  }

  # ---- HTTP --------------------------------------------

  RETRY_RETRIES: int = 3
  RETRY_BACKOFF_FACTOR: float = 0.2

  REQUEST_DELAY: float = 0.01
  REQUEST_TIMEOUT: int = 10
