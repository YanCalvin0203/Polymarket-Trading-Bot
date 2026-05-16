import time 

from typing import Any
from datetime import timezone, datetime
from retry_requests import retry
from openmeteo_requests import Client
from openmeteo_sdk.WeatherApiResponse import WeatherApiResponse
from numpy import array
from pandas import DataFrame, Timestamp, Timedelta, date_range
from src.settings import settings
from src.models.weather import (
  WeatherHistoricalMaxModel,
  WeatherForecastModel,
  WeatherManifestModel
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

  def get_forecasts(
    self, 
    manifests: dict[str, WeatherManifestModel]
  ) -> dict[str, WeatherForecastModel]:
    """
    This function retrieves the weather forecasts for the given manifests.

    Parameters
    --------------
    manifests (dict[str, WeatherManifestModel]): 
      The weather manifests for which to get the forecasts.

    Returns
    --------------
    dict[str, WeatherForecastModel]: 
      The retrieved weather forecasts, keyed by manifest ID.
    """
    forecasts = {}
    for manifest_id, manifest_model in manifests.items():
      forecast_model = self._get_single_forecast(manifest=manifest_model)
      if forecast_model is not None:
        forecasts[manifest_id] = forecast_model

    return forecasts
  
  def get_historical_max(
      self,
      manifests: dict[str, WeatherManifestModel]
    ) -> dict[str, WeatherHistoricalMaxModel]:
    """
    This function retrieves the historical maximum temperatures for the given 
    manifests.

    Parameters
    --------------
    manifests (dict[str, WeatherManifestModel]): 
      The weather manifests for which to get the historical maximum temperatures.

    Returns
    --------------
    dict[str, WeatherHistoricalMaxModel]: 
      The retrieved historical maximum temperatures, keyed by ICAO code.
    """
    cities = self._filter_unique_cities(manifests=manifests)

    historical_max = {}
    for icao_code, manifest_model in cities.items():
      historical_max_model = self._get_single_historical_max(
        manifest=manifest_model,
        historical_range_days=settings.WEATHER_ORACLE_SETTINGS.HISTORICAL_MAX_DAYS
      )
      if historical_max_model is not None:
        historical_max[icao_code] = historical_max_model

    return historical_max
  
  
  # ---- Internal Helpers ----------------------------

  def _get_single_forecast(
    self, 
    manifest: WeatherManifestModel
  ) -> WeatherForecastModel | None:
    """
    This function gets a single weather forecast for a given manifest.

    Parameters
    --------------
    manifest (WeatherManifestModel): 
      The weather manifest for which to get the forecast.

    Returns
    --------------
    WeatherForecastModel | None: 
      The structured forecast data, or None if the request fails.
    """
    try:
      params = self._build_query_params(
        manifest=manifest,
        initial_params=settings.WEATHER_ORACLE_SETTINGS.ENSEMBLE_FORECAST_QUERY_PARAMS
      )
      response = self._request_ensemble_data(
        params=params, 
        endpoint=settings.WEATHER_ORACLE_SETTINGS.ENSEMBLE_FORECAST_ENDPOINT
      )
      if not response:
        return None
      
      forecast_mean, forecast_stdev = self._get_forecast_stats(
        response=response,
        manifest=manifest
      )
      forecast_model = WeatherForecastModel(
        forecast_mean=forecast_mean,
        forecast_stdev=forecast_stdev,
        last_updated=Timestamp.now(tz=timezone.utc)
      )
      return forecast_model
    
    except Exception as e:
      return None
    
  def _get_single_historical_max(
    self,
    manifest: WeatherManifestModel,
    historical_range_days: int = 90
  ) -> WeatherHistoricalMaxModel | None:
    """
    This function gets a single historical maximum temperature for a 
    given manifest.

    Parameters
    --------------
    manifest (WeatherManifestModel): 
      The weather manifest for which to get the historical maximum 
      temperature.

    historical_range_days (int):
      The number of days prior to the manifest's resolution time to include in 
      the historical maximum temperature calculation. Defaults to 90 days.

    Returns
    --------------
    WeatherHistoricalMaxModel | None: 
      The structured historical maximum temperature data, or None if the 
      request fails.
    """
    try:
      start_date = manifest.resolution_time - Timedelta(days=historical_range_days)
      end_date = manifest.resolution_time

      params = self._build_query_params(
        manifest=manifest,
        initial_params=settings.WEATHER_ORACLE_SETTINGS.ENSEMBLE_ARCHIVE_QUERY_PARAMS,
        start_date=start_date,
        end_date=end_date
      )
      response = self._request_ensemble_data(
        params=params, 
        endpoint=settings.WEATHER_ORACLE_SETTINGS.ENSEMBLE_ARCHIVE_ENDPOINT
      )
      if not response:
        return None
      
      historical_max_df = self._get_historical_max_df(
        response=response,
        manifest=manifest
      )
      historical_max_model = WeatherHistoricalMaxModel(
        historical_max_data=historical_max_df,
        last_updated=Timestamp.now(tz=timezone.utc)
      )
      return historical_max_model

    except Exception as e:
      return None

  def _build_query_params(
    self, 
    manifest: WeatherManifestModel,
    initial_params: dict[str, Any],
    start_date: datetime | None = None,
    end_date: datetime | None = None
  ) -> dict[str, Any]:
    """
    This function builds the query parameters for the ensemble API request.

    Parameters
    --------------
    manifest (WeatherManifestModel): 
      The weather manifest for which to build the query parameters.

    initial_params (dict[str, Any]): 
      The initial query parameters.

    start_date (datetime | None):
      The start date for the forecast data. If None, defaults to the manifest's 
      resolution time.

    end_date (datetime | None):
      The end date for the forecast data. If None, defaults to the manifest's 
      resolution time.

    Returns
    --------------
    dict[str, Any]: 
      The query parameters for the ensemble API request.
    """
    params = initial_params.copy()
    params["latitude"] = manifest.location.latitude
    params["longitude"] = manifest.location.longitude
    params["temperature_unit"] = manifest.temperature_unit.api_value

    start_date = start_date or manifest.resolution_time
    end_date = end_date or manifest.resolution_time

    params["start_date"] = start_date.strftime('%Y-%m-%d')
    params["end_date"] = end_date.strftime('%Y-%m-%d')

    return params
  
  def _request_ensemble_data(
    self, 
    params: dict[str, Any],
    endpoint: str,
  ) -> WeatherApiResponse | None:
    """
    This function makes the API request to get the ensemble data.

    Parameters
    --------------
    params (dict[str, Any]): 
      The query parameters for the API request.

    endpoint (str): 
      The API endpoint to request.

    Returns
    --------------
    WeatherApiResponse | None: 
      The raw response data from the API, or None if the request fails.
    """
    try:
      response = self.client.weather_api(
        url=endpoint,
        params=params
      )
      
      time.sleep(settings.WEATHER_ORACLE_SETTINGS.REQUEST_DELAY)
      return response[0]

    except Exception as e:
      return None

  def _get_forecast_stats(
    self, 
    response: WeatherApiResponse, 
    manifest: WeatherManifestModel
  ) -> tuple[float, float]:
    """
    This function calculates forecast statistics from the raw API response.

    Parameters
    --------------
    response (WeatherApiResponse): 
      The raw response data from the API.

    manifest (WeatherManifestModel): 
      The weather manifest for which to calculate statistics.

    Returns
    --------------
    tuple[float, float]: 
      The mean and standard deviation of the forecast temperatures.
    """
    hourly = response.Hourly()

    # Calculate the timestamps (localized) for the dataframe index
    timestamps = date_range(
      start=Timestamp(hourly.Time(), unit="s", tz=timezone.utc),
      end=Timestamp(hourly.TimeEnd(), unit="s", tz=timezone.utc),
      freq=Timedelta(seconds=hourly.Interval()),
      inclusive="left"
    )   
    timestamps = timestamps.tz_convert(manifest.location.timezone)

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
  
  def _get_historical_max_df(
    self,
    response: WeatherApiResponse,
    manifest: WeatherManifestModel
  ) -> DataFrame:
    """
    This function processes the raw API response to extract the historical 
    maximum temperatures as a dataframe.

    Parameters
    --------------
    response (WeatherApiResponse): 
      The raw response data from the API.

    manifest (WeatherManifestModel): 
      The weather manifest for which to extract the historical maximum 
      temperatures.

    Returns
    --------------
    DataFrame: 
      A dataframe containing the historical maximum temperatures, indexed by 
      timestamp.
    """
    daily = response.Daily()
    data = daily.Variables(0).ValuesAsNumpy()

    # Calculate the timestamps (localized) for the dataframe index
    timestamps = date_range(
      start=Timestamp(daily.Time(), unit="s", tz=timezone.utc),
      periods=len(data),
      freq=Timedelta(seconds=daily.Interval()),
    )   
    dates = timestamps.tz_convert(manifest.location.timezone).normalize()

    # Build the dataframe
    df = DataFrame(
      data=data, 
      index=dates, 
      columns=["temperature_2m_max"]
    )

    return df

  def _filter_unique_cities(
    self, 
    manifests: dict[str, WeatherManifestModel]
  ) -> dict[str, WeatherManifestModel]:
    """
    This function filters the manifests to obtain the unique cities.

    Parameters
    --------------
    manifests (dict[str, WeatherManifestModel]): 
      The weather manifests for which to get the unique cities.

    Returns
    --------------
    dict[str, WeatherManifestModel]: 
      The dictionary of unique cities, keyed by ICAO code.
    """
    unique_cities = {}
    for manifest_model in manifests.values():
      city_name = manifest_model.location.icao_code
      if unique_cities.get(city_name, None) is not None:
        continue

      unique_cities[city_name] = manifest_model

    return unique_cities
  