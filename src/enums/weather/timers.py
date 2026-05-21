from enum import Enum


class WeatherTimer(Enum):
  """
  This enum defines the timers for weather-related events.
  """
  WEATHER_DATA_COLLECTION_TIMER  = "weather_data_collection_timer"
  WEATHER_MODEL_TRAINING_TIMER = "weather_model_training_timer"
