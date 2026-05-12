import time 

from typing import Any
from datetime import timezone
from retry_requests import retry
from openmeteo_requests import Client
from openmeteo_sdk.WeatherApiResponse import WeatherApiResponse
from numpy import array
from pandas import DataFrame, Timestamp, Timedelta, date_range
from src.core.settings import settings
from src.models.weather_model import (
  WeatherEventModel,
  WeatherForecastModel
)


class WeatherEnsemble:
  """
  This class implements the weather ensemble oracle to retrieve weather forecasts.
  """

  def __init__(self) -> None:
    """
    This function initializes the WeatherEnsemble class.
    """
    self._retry_session = retry(
      retries=settings.WEATHER_ORACLE_SETTINGS.RETRY_RETRIES,
      backoff_factor=settings.WEATHER_ORACLE_SETTINGS.RETRY_BACKOFF_FACTOR
    )
    self.client = Client(session=self._retry_session)


  # ---- Public API ----------------------------------

  def get_forecasts(self, events: dict[str, WeatherEventModel]) -> None:
    """
    This function retrieves the weather forecast and update the weather events.

    Parameters
    --------------
    events (dict[str, WeatherEventModel]): The weather events for which to get the forecasts.
    """
    for event in events.values():
      forecast_model = self._get_single_forecast(event=event)
      if forecast_model is not None:
        event.forecast = forecast_model


  # ---- Internal Helpers ----------------------------

  def _get_single_forecast(self, event: WeatherEventModel) -> WeatherForecastModel | None:
    """
    This function gets a single weather forecast for a given event.

    Parameters
    --------------
    event (WeatherEventModel): The weather event for which to get the forecast.

    Returns
    --------------
    WeatherForecastModel | None: The structured forecast data, or None if the request fails.
    """
    try:
      params = self._build_query_params(event=event)
      response = self._request_forecast_data(params=params)
      if not response:
        return None
      
      forecast_mean, forecast_stdev = self._get_forecast_stats(
        response=response,
        event=event
      )
      forecast_model = WeatherForecastModel(
        forecast_mean=forecast_mean,
        forecast_stdev=forecast_stdev,
        last_updated=Timestamp.now(tz=timezone.utc)
      )
      return forecast_model
    
    except Exception as e:
      return None
  
  def _build_query_params(self, event: WeatherEventModel) -> dict[str, Any]:
    """
    This function builds the query parameters for the ensemble API request.

    Parameters
    --------------
    event (WeatherEventModel): The weather event for which to build the query parameters.

    Returns
    --------------
    dict[str, Any]: The query parameters for the ensemble API request.
    """
    params = settings.WEATHER_ORACLE_SETTINGS.ENSEMBLE_QUERY_PARAMS.copy()
    params["latitude"] = event.location.latitude
    params["longitude"] = event.location.longitude
    params["start_date"] = event.resolution_time.strftime('%Y-%m-%d')
    params["end_date"] = event.resolution_time.strftime('%Y-%m-%d')
    params["temperature_unit"] = event.temperature_unit.api_value

    return params
  
  def _request_forecast_data(self, params: dict[str, Any]) -> WeatherApiResponse | None:
    """
    This function makes the API request to get the forecast data.

    Parameters
    --------------
    params (dict[str, Any]): The query parameters for the API request.

    Returns
    --------------
    WeatherApiResponse | None: The raw response data from the API, or None if the request fails.
    """
    try:
      response = self.client.weather_api(
        url=settings.WEATHER_ORACLE_SETTINGS.ENSEMBLE_ENDPOINT,
        params=params
      )
      
      time.sleep(settings.WEATHER_ORACLE_SETTINGS.REQUEST_DELAY)
      return response[0]

    except Exception as e:
      return None

  def _get_forecast_stats(self, response: WeatherApiResponse, event: WeatherEventModel) -> tuple[float, float]:
    """
    This function calculates forecast statistics from the raw API response.

    Parameters
    --------------
    response (WeatherApiResponse): The raw response data from the API.
    event (WeatherEventModel): The weather event for which to calculate statistics.

    Returns
    --------------
    tuple[float, float]: The mean and standard deviation of the forecast temperatures.
    """
    hourly = response.Hourly()

    # Calculate the timestamps (localized) for the dataframe index
    timestamps = date_range(
      start=Timestamp(hourly.Time(), unit="s", tz=timezone.utc),
      end=Timestamp(hourly.TimeEnd(), unit="s", tz=timezone.utc),
      freq=Timedelta(seconds=hourly.Interval()),
      inclusive="left"
    )   
    timestamps = timestamps.tz_convert(event.location.timezone)

    # Retrieve the ensemble member forecasts and build the numpy array
    ensemble_count = settings.WEATHER_ORACLE_SETTINGS.ENSEMBLE_COUNT
    members = array([hourly.Variables(i).ValuesAsNumpy() for i in range(ensemble_count)])

    # Build the dataframe and calculate the forecast statistics
    df = DataFrame(
      data=members.T, 
      index=timestamps, 
      columns=[f"member_{i+1:02d}" for i in range(ensemble_count)]
    )
    max_temp_df = df.max(axis=0)

    forecast_mean = float(max_temp_df.mean())
    forecast_stdev = float(max_temp_df.std())

    return forecast_mean, forecast_stdev
