class WeatherCalibratorSettings:
  """
  This class contains all the configuration variables for the 
  weather calibrator.
  """
  DATA_CALIBRATION_INTERVAL_DAYS: int = 7
  DATA_CALIBRATION_TARGET_HOUR: int = 2
  DATA_CALIBRATION_LOOKBACK_DAYS: int = 90
