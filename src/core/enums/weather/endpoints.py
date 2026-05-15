from enum import Enum


class WeatherEndpoint(Enum):
  """
  This enum defines the endpoints for weather-related messages.
  """
  WEATHER_FORECAST_STATUS = "WeatherStateActor.on_forecast_status"
  WEATHER_OBSERVATION_STATUS = "WeatherStateActor.on_observation_status"

  WEATHER_FORECAST_REQUEST = "WeatherForecastIngestorActor.on_receive_forecast_request"
  WEATHER_OBSERVATION_REQUEST = "WeatherObservationIngestorActor.on_receive_observation_request"
  
  WEATHER_FORECAST_UPDATE = "WeatherStateActor.on_forecast_update"
  WEATHER_OBSERVATION_UPDATE = "WeatherStateActor.on_observation_update"
