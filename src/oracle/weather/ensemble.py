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
  WeatherDataCollectionForecastModel,
  WeatherDataCollectionActualMaxModel,
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
  
  def get_data_collection_forecasts(
    self,
    cities: dict[str, LocationModel],
    lookahead_days: int = 1
  ) -> dict[str, list[WeatherDataCollectionForecastModel]]:
    """
    This function retrieves the data collection forecasts for the given locations.

    Parameters
    --------------
    cities (dict[str, LocationModel]): 
      The weather locations for which to get the data collection forecasts.

    lookahead_days (int):
      The number of days into the future to include in the data collection forecast 
      calculation. Defaults to 1 days.

    Returns
    --------------
    dict[str, list[WeatherDataCollectionForecastModel]]: 
      The retrieved data collection forecasts, keyed by ICAO code.
    """
    data_collection_forecasts = {}
    for icao_code, location_model in cities.items():
      data_collection_forecast_list = self._get_single_data_collection_forecast(
        location=location_model,
        lookahead_days=lookahead_days
      )
      if len(data_collection_forecast_list) > 0:
        data_collection_forecasts[icao_code] = data_collection_forecast_list

    return data_collection_forecasts
  
  
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
    
  def _get_single_data_collection_forecast(
    self,
    location: LocationModel,
    lookahead_days: int
  ) -> list[WeatherDataCollectionForecastModel]:
    """
    This function gets the list of data collection forecast for a given location.

    Parameters
    --------------
    location (LocationModel): 
      The weather location for which to get the data collection forecast.

    lookahead_days (int):
      The number of days into the future to include in the data collection forecast 
      calculation.

    Returns
    --------------
    list[WeatherDataCollectionForecastModel]: 
      The list of structured forecast data collection for the location.
    """
    try:
      current_local_date = Timestamp.now(tz=location.timezone).normalize()
      start_date = current_local_date
      end_date = current_local_date + Timedelta(days=lookahead_days)

      params = self._build_query_params(
        location=location,
        initial_params=settings.WEATHER_ORACLE_SETTINGS.ENSEMBLE_FORECAST_QUERY_PARAMS,
        start_date=start_date,
        end_date=end_date
      )
      response = self._request_ensemble_data(
        params=params, 
        endpoint=settings.WEATHER_ORACLE_SETTINGS.ENSEMBLE_FORECAST_ENDPOINT
      )
      if not response:
        return []
      
      data_collection_forecast_df = self._get_data_collection_forecast_df(
        response=response,
        location=location
      )

      data_collection_forecast_list = []
      for target_date, row in data_collection_forecast_df.iterrows():
        lead_day = (target_date - current_local_date).days
        data_collection_forecast_model = WeatherDataCollectionForecastModel(
          lead_days=lead_day,
          ensemble_mean=row["ensemble_mean"],
          ensemble_stdev=row["ensemble_stdev"],
          resolution_date=target_date,
          created_at=Timestamp.now(tz=timezone.utc)
        )
        data_collection_forecast_list.append(data_collection_forecast_model)

      return data_collection_forecast_list

    except Exception as e:
      return []

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
  
  def _get_data_collection_forecast_df(
    self,
    response: WeatherApiResponse,
    location: LocationModel
  ) -> DataFrame:
    """
    This function processes the raw API response to extract the data collection 
    forecasts as a dataframe.

    Parameters
    --------------
    response (WeatherApiResponse): 
      The raw response data from the API.

    location (LocationModel):
      The weather location for which to extract the data collection forecasts.

    Returns
    --------------
    DataFrame: 
      A dataframe containing the data collection forecasts, indexed by date.
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

    # Restore the index timezone typing to stay uniform across the codebase
    daily_member_max_df.index = to_datetime(daily_member_max_df.index).tz_localize(location.timezone)

    summary_df = DataFrame(index=daily_member_max_df.index)
    summary_df["ensemble_mean"] = daily_member_max_df.mean(axis=1)
    summary_df["ensemble_stdev"] = daily_member_max_df.std(axis=1)

    return summary_df
