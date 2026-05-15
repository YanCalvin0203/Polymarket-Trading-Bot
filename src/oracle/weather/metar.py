import time
import requests

from typing import Any
from datetime import datetime, timezone
from src.core.settings import settings
from src.core.enums.weather import TemperatureUnit
from src.utils.temperature_converter import to_farenheit
from src.models.weather import (
  WeatherObservationModel,
  WeatherManifestModel
)


class WeatherMetar:
  """
  This class implements the weather metar oracle to retrieve weather observations.
  """

  # ---- Public API ----------------------------------

  def get_observations(
    self, 
    manifests: dict[str, WeatherManifestModel]
  ) -> dict[str, WeatherObservationModel]:
    """
    This function retrieves the weather observations for the given manifests.

    Parameters
    --------------
    manifests (dict[str, WeatherManifestModel]): The weather manifests for which 
      to get the observations.

    Returns
    --------------
    dict[str, WeatherObservationModel]: The retrieved weather observations, keyed by 
      manifest ID.
    """
    observations = {}
    for manifest_id, manifest_model in manifests.items():
      observation_model = self._get_single_observation(manifest=manifest_model)
      if observation_model is not None:
        observations[manifest_id] = observation_model

    return observations


  # ---- Internal Helpers ----------------------------

  def _get_single_observation(
    self, 
    manifest: WeatherManifestModel
  ) -> WeatherObservationModel | None:
    """
    This function gets a single weather observation for a given manifest.

    Parameters
    --------------
    manifest (WeatherManifestModel): The weather manifest for which to get 
      the observation.

    Returns
    --------------
    WeatherObservationModel | None: The structured observation data, or None if the 
      request fails.
    """
    try:
      params = self._build_query_params(manifest=manifest)
      response = self._request_observation_data(params=params)
      if not response:
        return None

      data: dict[str, Any] = response[0]
      current_temperature = self._get_current_temperature(
        data=data, 
        manifest=manifest
      )
      if current_temperature is None:
        return None
      
      previous_max_temperature = current_temperature
      if manifest.observation_max is not None:
        previous_max_temperature = manifest.observation_max

      observation_model = WeatherObservationModel(
        observation_current=current_temperature,
        observation_max=max(current_temperature, previous_max_temperature),
        last_updated=datetime.now(tz=timezone.utc)
      )
      return observation_model

    except Exception as e:
      return None

  def _build_query_params(self, manifest: WeatherManifestModel) -> dict[str, Any]:
    """
    This function builds the query parameters for the METAR API request.

    Parameters
    --------------
    manifest (WeatherManifestModel): The weather manifest for which to build the 
      query parameters.

    Returns
    --------------
    dict[str, Any]: The query parameters for the METAR API request.
    """
    params = settings.WEATHER_ORACLE_SETTINGS.METAR_QUERY_PARAMS.copy()
    params["ids"] = manifest.location.icao_code

    return params
  
  def _request_observation_data(self, params: dict[str, Any]) -> dict[str, Any] | None:
    """
    This function makes the API request to get the observation data.

    Parameters
    --------------
    params (dict[str, Any]): The query parameters for the API request.

    Returns
    --------------
    dict[str, Any] | None: The raw response data from the API, or None if the request fails.
    """
    try:
      response = requests.get(
        settings.WEATHER_ORACLE_SETTINGS.METAR_ENDPOINT,
        params=params,
        timeout=settings.WEATHER_ORACLE_SETTINGS.REQUEST_TIMEOUT,
      )
      
      time.sleep(settings.WEATHER_ORACLE_SETTINGS.REQUEST_DELAY)
      return response.json()

    except Exception as e:
      return None
  
  def _get_current_temperature(
    self, 
    data: dict[str, Any], 
    manifest: WeatherManifestModel
  ) -> float | None:
    """
    This function extracts the current temperature from the raw API response data
    and converts it to the correct unit.

    Parameters
    --------------
    data (dict[str, Any]): The raw response data from the API.
    manifest (WeatherManifestModel): The weather manifest for which to get the temperature.

    Returns
    --------------
    float | None: The current temperature, or None if it cannot be extracted.
    """
    current_temperature = data.get("temp", None)
    if current_temperature is None:
      return None
    
    # Convert the temperature unit if necessary (initial response at Celsius)
    if manifest.temperature_unit.api_value == TemperatureUnit.FAHRENHEIT.api_value:
      current_temperature = to_farenheit(current_temperature)

    return current_temperature
