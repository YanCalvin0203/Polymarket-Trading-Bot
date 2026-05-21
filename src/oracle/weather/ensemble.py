import time 

from typing import Any
from datetime import timezone
from retry_requests import retry
from openmeteo_requests import Client
from openmeteo_sdk.WeatherApiResponse import WeatherApiResponse
from numpy import array
from pandas import DataFrame, Timestamp, Timedelta, date_range, to_datetime
from src.settings import settings
from src.models.weather import (
  WeatherHistoricalForecastModel,
  WeatherHistoricalMaxModel,
  WeatherForecastModel,
  WeatherManifestModel,
  LocationModel
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
      cities: dict[str, LocationModel],
      historical_range_days: int = 1
    ) -> dict[str, WeatherHistoricalMaxModel]:
    """
    This function retrieves the historical maximum temperatures for the given 
    manifests.

    Parameters
    --------------
    cities (dict[str, LocationModel]): 
      The weather locations for which to get the historical maximum temperatures.

    historical_range_days (int):
      The number of days prior to the location's resolution time to include in 
      the historical maximum temperature calculation. Defaults to 1 days.

    Returns
    --------------
    dict[str, WeatherHistoricalMaxModel]: 
      The retrieved historical maximum temperatures, keyed by ICAO code.
    """
    historical_max = {}
    for icao_code, location_model in cities.items():
      historical_max_model = self._get_single_historical_max(
        location=location_model,
        historical_range_days=historical_range_days
      )
      if historical_max_model is not None:
        historical_max[icao_code] = historical_max_model

    return historical_max
  
  def get_historical_forecasts(
    self,
    cities: dict[str, LocationModel],
    historical_range_days: int = 1
  ) -> dict[str, WeatherHistoricalForecastModel]:
    """
    This function retrieves the historical forecasts for the given locations.

    Parameters
    --------------
    cities (dict[str, LocationModel]): 
      The weather locations for which to get the historical forecasts.

    historical_range_days (int):
      The number of days prior to the location's resolution time to include in 
      the historical forecast calculation. Defaults to 1 days.

    Returns
    --------------
    dict[str, WeatherHistoricalForecastModel]: 
      The retrieved historical forecasts, keyed by ICAO code.
    """
    historical_forecasts = {}
    for icao_code, location_model in cities.items():
      historical_forecast_model = self._get_single_historical_forecast(
        location=location_model,
        historical_range_days=historical_range_days
      )
      if historical_forecast_model is not None:
        historical_forecasts[icao_code] = historical_forecast_model

    return historical_forecasts
  
  
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
        location=manifest.location,
        initial_params=settings.WEATHER_ORACLE_SETTINGS.ENSEMBLE_FORECAST_QUERY_PARAMS,
        start_date=manifest.resolution_time,
        end_date=manifest.resolution_time
      )
      response = self._request_ensemble_data(
        params=params, 
        endpoint=settings.WEATHER_ORACLE_SETTINGS.ENSEMBLE_FORECAST_ENDPOINT
      )
      if not response:
        return None
      
      forecast_mean, forecast_stdev = self._get_forecast_stats(
        response=response,
        location=manifest.location
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
    location: LocationModel,
    historical_range_days: int
  ) -> WeatherHistoricalMaxModel | None:
    """
    This function gets a single historical maximum temperature for a 
    given location.

    Parameters
    --------------
    location (LocationModel): 
      The weather location for which to get the historical maximum 
      temperature.

    historical_range_days (int):
      The number of days prior to the location's resolution time to include in 
      the historical maximum temperature calculation.

    Returns
    --------------
    WeatherHistoricalMaxModel | None: 
      The structured historical maximum temperature data, or None if the 
      request fails.
    """
    try:
      current_local_date = Timestamp.now(tz=location.timezone).normalize()
      start_date = current_local_date - Timedelta(days=historical_range_days)
      end_date = current_local_date - Timedelta(days=1)

      params = self._build_query_params(
        location=location,
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
        location=location
      )
      historical_max_model = WeatherHistoricalMaxModel(
        historical_max_data=historical_max_df,
        last_updated=Timestamp.now(tz=timezone.utc)
      )
      return historical_max_model

    except Exception as e:
      return None
    
  def _get_single_historical_forecast(
    self, 
    location: LocationModel,
    historical_range_days: int
  ) -> WeatherHistoricalForecastModel | None:
    """
    This function gets a single historical forecast for a given location.

    Parameters
    --------------
    location (LocationModel): 
      The weather location for which to get the historical forecast.

    historical_range_days (int):
      The number of days prior to the location's resolution time to include in 
      the historical forecast calculation.

    Returns
    --------------
    WeatherHistoricalForecastModel | None: 
      The structured historical forecast data, or None if the request fails.
    """
    try:
      current_local_date = Timestamp.now(tz=location.timezone).normalize()
      start_date = current_local_date - Timedelta(days=historical_range_days)
      end_date = current_local_date - Timedelta(days=1)

      params = self._build_query_params(
        location=location,
        initial_params=settings.WEATHER_ORACLE_SETTINGS.ENSEMBLE_HISTORICAL_FORECAST_QUERY_PARAMS,
        start_date=start_date,
        end_date=end_date
      )
      response = self._request_ensemble_data(
        params=params, 
        endpoint=settings.WEATHER_ORACLE_SETTINGS.ENSEMBLE_HISTORICAL_FORECAST_ENDPOINT
      )
      if not response:
        return None
      
      historical_forecast_df = self._get_historical_forecast_df(
        response=response,
        location=location
      )
      historical_forecast_model = WeatherHistoricalForecastModel(
        historical_forecast_data=historical_forecast_df,
        last_updated=Timestamp.now(tz=timezone.utc)
      )
      return historical_forecast_model

    except Exception as e:
      return None

  def _build_query_params(
    self, 
    location: LocationModel,
    initial_params: dict[str, Any],
    start_date: Timestamp,
    end_date: Timestamp
  ) -> dict[str, Any]:
    """
    This function builds the query parameters for the ensemble API request.

    Parameters
    --------------
    location (LocationModel): 
      The weather location for which to build the query parameters.

    initial_params (dict[str, Any]): 
      The initial query parameters.

    start_date (Timestamp | None):
      The start date for the forecast data.

    end_date (Timestamp | None):
      The end date for the forecast data.

    Returns
    --------------
    dict[str, Any]: 
      The query parameters for the ensemble API request.
    """
    params = initial_params.copy()
    params["latitude"] = location.latitude
    params["longitude"] = location.longitude
    params["temperature_unit"] = location.temperature_unit.api_value

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
    location: LocationModel
  ) -> tuple[float, float]:
    """
    This function calculates forecast statistics from the raw API response.

    Parameters
    --------------
    response (WeatherApiResponse): 
      The raw response data from the API.

    location (LocationModel): 
      The weather location for which to calculate statistics.

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
    timestamps = timestamps.tz_convert(location.timezone)

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
    location: LocationModel
  ) -> DataFrame:
    """
    This function processes the raw API response to extract the historical 
    maximum temperatures as a dataframe.

    Parameters
    --------------
    response (WeatherApiResponse): 
      The raw response data from the API.

    location (LocationModel): 
      The weather location for which to extract the historical maximum 
      temperatures.

    Returns
    --------------
    DataFrame: 
      A dataframe containing the historical maximum temperatures, indexed by 
      date.
    """
    daily = response.Daily()
    data = daily.Variables(0).ValuesAsNumpy()

    # Calculate the timestamps (localized) for the dataframe index
    timestamps = date_range(
      start=Timestamp(daily.Time(), unit="s", tz=timezone.utc),
      periods=len(data),
      freq=Timedelta(seconds=daily.Interval()),
    )   
    dates = timestamps.tz_convert(location.timezone).normalize()

    # Build the dataframe
    df = DataFrame(
      data=data, 
      index=dates, 
      columns=["temperature_2m_max"]
    )

    return df
  
  def _get_historical_forecast_df(
    self,
    response: WeatherApiResponse,
    location: LocationModel
  ) -> DataFrame:
    """
    This function processes the raw API response to extract the historical 
    forecasts as a dataframe.

    Parameters
    --------------
    response (WeatherApiResponse): 
      The raw response data from the API.

    location (LocationModel):
      The weather location for which to extract the historical forecasts.

    Returns
    --------------
    DataFrame: 
      A dataframe containing the historical forecasts, indexed by date.
    """
    hourly = response.Hourly()

    # Calculate the timestamps (localized) for the dataframe index
    timestamps = date_range(
      start=Timestamp(hourly.Time(), unit="s", tz=timezone.utc),
      end=Timestamp(hourly.TimeEnd(), unit="s", tz=timezone.utc),
      freq=Timedelta(seconds=hourly.Interval()),
      inclusive="left"
    )   
    timestamps = timestamps.tz_convert(location.timezone)

    # Retrieve the ensemble member historical forecasts and build the numpy array
    ensemble_count = settings.WEATHER_ORACLE_SETTINGS.ENSEMBLE_COUNT
    members = array([hourly.Variables(i).ValuesAsNumpy() for i in range(ensemble_count)])

    # Build the dataframe and calculate the forecast statistics
    df = DataFrame(
      data=members.T, 
      index=timestamps, 
      columns=[f"member_{i+1:02d}" for i in range(ensemble_count)]
    )

    # Scans vertically down the columns for each day to find each member's peak.
    daily_member_max_df: DataFrame = df.groupby(df.index.date).max()

    # Restore the index timezone typing to stay uniform across your app
    daily_member_max_df.index = to_datetime(daily_member_max_df.index).tz_localize(location.timezone)

    summary_df = DataFrame(index=daily_member_max_df.index)
    summary_df["ensemble_mean"] = daily_member_max_df.mean(axis=1)
    summary_df["ensemble_stdev"] = daily_member_max_df.std(axis=1)

    return summary_df
