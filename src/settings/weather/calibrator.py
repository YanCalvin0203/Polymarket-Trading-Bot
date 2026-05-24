class WeatherCalibratorSettings:
  """
  This class contains all the configuration variables for the 
  weather calibrator.
  """
  CALIBRATION_INTERVAL_DAYS: int = 6
  CALIBRATION_TARGET_DAY: int = 6
  CALIBRATION_TARGET_HOUR: int = 2
  CALIBRATION_LOOKBACK_DAYS: int = 90

  CALIBRATION_MIN_SAMPLES: int = 30

  # ---- EMOS Params -----------------------------

  INIT_A: float = 0.0
  INIT_B: float = 1.0
  INIT_C_FAHRENHEIT: float = 4.0
  INIT_C_CELSIUS: float = 1.2345
  INIT_D: float = 1.0

  BOUNDS_A: tuple = (None, None)
  BOUNDS_B: tuple = (0.1, 3.0)
  BOUNDS_C_FAHRENHEIT: tuple = (INIT_C_FAHRENHEIT, None)
  BOUNDS_C_CELSIUS: tuple = (INIT_C_CELSIUS, None)
  BOUNDS_D: tuple = (0.05, None)
