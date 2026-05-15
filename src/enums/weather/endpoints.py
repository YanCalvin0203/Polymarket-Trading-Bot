from enum import Enum
from src.utils.path_builder import make_path


class WeatherEndpoint(Enum):
  """
  This enum defines the endpoints for weather-related messages.
  """
  WEATHER_FORECAST_STATUS = make_path(
    module="WeatherStateActor",
    class_name="on_forecast_status"
  )
  WEATHER_OBSERVATION_STATUS = make_path(
    module="WeatherStateActor",
    class_name="on_observation_status"
  )

  WEATHER_FORECAST_REQUEST = make_path(
    module="WeatherForecastIngestorActor",
    class_name="on_receive_forecast_request"
  )
  WEATHER_OBSERVATION_REQUEST = make_path(
    module="WeatherObservationIngestorActor",
    class_name="on_receive_observation_request"
  )

  WEATHER_FORECAST_UPDATE = make_path(
    module="WeatherStateActor",
    class_name="on_forecast_update"
  )
  WEATHER_OBSERVATION_UPDATE = make_path(
    module="WeatherStateActor",
    class_name="on_observation_update"
  )
