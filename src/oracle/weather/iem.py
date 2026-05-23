import time
import requests

from typing import Any
from datetime import timezone
from pandas import Timestamp, Timedelta
from src.enums.weather import TemperatureUnit
from src.utils.temperature_converter import to_celsius
from src.settings import settings
from src.models.weather import (
  WeatherDataCollectionActualMaxModel,
  LocationModel
)


class WeatherIEM:
  """
  This class implements the weather IEM oracle to retrieve past
  weather data.
  """

  # ---- Public API ----------------------------------

  def get_data_collection_actual_max(
    self,
    cities: dict[str, LocationModel],
    lookback_days: int = 1
  ) -> dict[str, list[WeatherDataCollectionActualMaxModel]]:
    """
    This function retrieves the data collection actual max temperatures for the given 
    locations.

    Parameters
    --------------
    cities (dict[str, LocationModel]): 
      The weather locations for which to get the data collection actual max temperatures.

    lookback_days (int):
      The number of days into the past to include in the data collection actual max 
      temperature calculation. Defaults to 1 days.

    Returns
    --------------
    dict[str, list[WeatherDataCollectionActualMaxModel]]: 
      The retrieved data collection actual max temperatures, keyed by ICAO code.
    """
    data_collection_actual_max = {}
    for icao_code, location_model in cities.items():
      data_collection_actual_max_list = self._get_single_data_collection_actual_max(
        location=location_model,
        lookback_days=lookback_days
      )
      if len(data_collection_actual_max_list) > 0:
        data_collection_actual_max[icao_code] = data_collection_actual_max_list

    return data_collection_actual_max


  # ---- Internal Helpers ----------------------------

  def _get_single_data_collection_actual_max(
    self,
    location: LocationModel,
    lookback_days: int
  ) -> list[WeatherDataCollectionActualMaxModel]:
    """
    This function gets the list of data collection actual max temperatures for a given 
    location.

    Parameters
    --------------
    location (LocationModel): 
      The weather location for which to get the data collection actual max temperatures.

    lookback_days (int):
      The number of days into the past to include in the data collection actual max 
      temperature calculation.

    Returns
    --------------
    list[WeatherDataCollectionActualMaxModel]: 
      The list of structured actual max temperature data collection for the location.
    """
    try:
      current_local_date = Timestamp.now(tz=location.timezone).normalize()

      network_code = self._get_network_code(location_identifier=location.iata_code)
      location_code = location.iata_code
      
      if not network_code:
        network_code = self._get_network_code(location_identifier=location.icao_code)
        location_code = location.icao_code
      
      data_collection_actual_max_list = []
      for day in range(1, lookback_days + 1):
        date = current_local_date - Timedelta(days=day)
        params = self._build_query_params(
          location_identifier=location_code,
          network_code=network_code,
          date=date
        )
        max_temperature_response = self._request_iem_data(
          params=params, 
          endpoint=settings.WEATHER_ORACLE_SETTINGS.IEM_ENDPOINT
        )
        if not max_temperature_response:
          continue
      
        actual_max = max_temperature_response.get("max_tmpf", None)
        if actual_max is None:
          continue

        if location.temperature_unit.api_value == TemperatureUnit.CELSIUS.api_value:
          actual_max = to_celsius(actual_max)
        
        data_collection_actual_max_model = WeatherDataCollectionActualMaxModel(
          actual_max=actual_max,
          resolution_date=date,
          created_at=Timestamp.now(tz=timezone.utc)
        )
        data_collection_actual_max_list.append(data_collection_actual_max_model)

      return data_collection_actual_max_list

    except Exception as e:
      return []
    
  def _get_network_code(self, location_identifier: str) -> str:
    """
    This function retrieves the IEM network code for a given location.

    Parameters
    --------------
    location_identifier (str): 
      The location identifier for which to retrieve the IEM network code, ICAO for 
      international locations and IATA for US locations.

    Returns
    --------------
    str: 
      The IEM network code for the location, or an empty string if it cannot be 
      retrieved. 
    """
    network_code_response = self._request_iem_data(
      params={},
      endpoint=settings.WEATHER_ORACLE_SETTINGS.get_network_endpoint(
        location_identifier
      )
    )
    if not network_code_response:
      return ""
    
    network_code = network_code_response.get("network", None)
    if not network_code:
      return ""
    
    return network_code
 
  def _build_query_params(
    self, 
    location_identifier: str,
    network_code: str,
    date: Timestamp,
  ) -> dict[str, Any]:
    """
    This function builds the query parameters for the IEM API request.

    Parameters
    --------------
    location_identifier (str):
      The location identifier for the IEM API request, ICAO for international locations 
      and IATA code for US locations.

    network_code (str):
      The network code for the IEM station.

    date (Timestamp):
      The date for which to retrieve data.

    Returns
    --------------
    dict[str, Any]: 
      The query parameters for the IEM API request.
    """
    params = {
      "station": location_identifier,
      "network": network_code,
      "date": date.strftime('%Y-%m-%d'),
    }

    return params
  
  def _request_iem_data(
    self, 
    params: dict[str, Any],
    endpoint: str,
  ) -> dict | None:
    """
    This function makes the API request to get the IEM data.

    Parameters
    --------------
    params (dict[str, Any]): 
      The query parameters for the API request.

    endpoint (str): 
      The API endpoint to request.

    Returns
    --------------
    dict | None: 
      The raw response data from the API, or None if the request fails.
    """
    try:
      response = requests.get(
        url=endpoint,
        params=params,
        timeout=settings.WEATHER_ORACLE_SETTINGS.REQUEST_TIMEOUT
      )
      if response.status_code != 200:
        return None
      
      payload: dict = response.json()
      if payload is None:
        return None
      
      data = payload.get("data", [])
      if data is None:
        return None
      
      time.sleep(settings.WEATHER_ORACLE_SETTINGS.REQUEST_DELAY)
      return data[0]

    except Exception as e:
      return None
