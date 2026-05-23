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
  WEATHER_DATA_COLLECTION_STATUS = make_path(
    module="WeatherStateActor",
    class_name="on_data_collection_status"
  )
  WEATHER_MODEL_CALIBRATION_STATUS = make_path(
    module="WeatherStateActor",
    class_name="on_model_calibration_status"
  )
  WEATHER_PREDICTION_STATUS = make_path(
    module="WeatherStateActor",
    class_name="on_prediction_status"
  )

  WEATHER_FORECAST_REQUEST = make_path(
    module="WeatherForecastIngestorActor",
    class_name="on_receive_forecast_request"
  )
  WEATHER_OBSERVATION_REQUEST = make_path(
    module="WeatherObservationIngestorActor",
    class_name="on_receive_observation_request"
  )
  WEATHER_DATA_COLLECTION_REQUEST = make_path(
    module="WeatherDataCollectorActor",
    class_name="on_receive_data_collection_request"
  )
  WEATHER_MODEL_CALIBRATION_REQUEST = make_path(
    module="WeatherPredictorCalibratorActor",
    class_name="on_model_calibration_request"
  )
  WEATHER_PREDICTION_REQUEST = make_path(
    module="WeatherPredictorActor",
    class_name="on_receive_prediction_request"
  )

  WEATHER_FORECAST_UPDATE = make_path(
    module="WeatherStateActor",
    class_name="on_forecast_update"
  )
  WEATHER_OBSERVATION_UPDATE = make_path(
    module="WeatherStateActor",
    class_name="on_observation_update"
  )
  WEATHER_PREDICTION_UPDATE = make_path(
    module="WeatherStateActor",
    class_name="on_prediction_update"
  )
