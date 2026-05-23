from typing import Any


class WeatherOracleSettings:
  """
  This class contains all the configuration variables for the oracle.
  """
  # ---- Ensemble ----------------------------------------

  ENSEMBLE_COUNT: int = 51
  DATA_COLLECTION_LOOKAHEAD_DAYS: int = 3
  DATA_COLLECTION_LOOKBACK_DAYS: int = 1

  ENSEMBLE_FORECAST_ENDPOINT: str = "https://ensemble-api.open-meteo.com/v1/ensemble"
  ENSEMBLE_FORECAST_QUERY_PARAMS: dict[str, Any] = {
    "hourly": ["temperature_2m"],
    "models": "ecmwf_ifs025",
    "timezone": "auto"
  }

  # ---- IEM ---------------------------------------------

  IEM_ENDPOINT: str = "https://mesonet.agron.iastate.edu/api/1/daily.json"

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

  # ---- Public API ---------------------------------------

  def get_network_endpoint(self, location_identifier: str) -> str:
    """
    This function returns the network endpoint for the given location identifier.

    Parameters
    --------------
    location_identifier (str): 
      The location identifier for which to get the network endpoint, ICAO for 
      international locations and IATA for US locations.

    Returns
    --------------
    str: 
      The network endpoint string for the given location identifier.
    """
    return f"https://mesonet.agron.iastate.edu/api/1/station/{location_identifier}.json"
