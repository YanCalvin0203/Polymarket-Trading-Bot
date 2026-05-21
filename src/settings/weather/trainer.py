class WeatherTrainerSettings:
  """
  This class contains all the configuration variables for the 
  weather trainer.
  """
  DATA_TRAINING_INTERVAL_DAYS: int = 7
  DATA_TRAINING_TARGET_HOUR: int = 2
  DATA_TRAINING_LOOKBACK_DAYS: int = 90
