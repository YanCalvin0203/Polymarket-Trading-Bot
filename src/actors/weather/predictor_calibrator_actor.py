from scipy.stats import norm
from scipy.optimize import minimize
from datetime import datetime, timezone
from numpy import array, ndarray, any, sqrt, sum
from pandas import DataFrame, Timedelta, Timestamp
from nautilus_trader.config import ActorConfig
from nautilus_trader.common.actor import Actor
from nautilus_trader.common.enums import LogColor
from nautilus_trader.common.events import TimeEvent
from src.enums.common import Status
from src.enums.weather import WeatherTimer, WeatherEndpoint
from src.database.weather_adapter import WeatherPostgresAdapter
from src.settings import settings
from src.models.weather import (
  LocationModel, 
  WeatherCalibrationParams
)


class WeatherPredictorCalibratorActorConfig(ActorConfig):
  """
  This class contains all the configurations for the WeatherPredictorCalibrator actor.
  """
  pass


class WeatherPredictorCalibratorActor(Actor):
  """
  This class implements the WeatherPredictorCalibratorActor, which is responsible for 
  calibrating the EMOS prediction model using the collected weather data.
  """
  
  def __init__(self, config: WeatherPredictorCalibratorActorConfig) -> None:
    """
    This function initializes the WeatherPredictorCalibratorActor class.

    Parameters:
    ----------------
    config (WeatherPredictorCalibratorActorConfig): 
      The configuration for the WeatherPredictorCalibratorActor.
    """
    super().__init__(config)
    self.cities = {}
    self.database_adapter = WeatherPostgresAdapter()


  # ---- Lifecycle Methods ----------------------------------

  def on_start(self) -> None:
    """
    This function is called when the actor is started.
    """
    self.log.info(
      message="Registering endpoints...", 
      color=LogColor.NORMAL
    )

    self.msgbus.register(
      endpoint=WeatherEndpoint.WEATHER_MODEL_CALIBRATION_REQUEST.value,
      handler=self._on_receive_model_calibration_request
    )

    self.log.info(
      message="All endpoints registered successfully", 
      color=LogColor.GREEN
    )
    self.log.info(
      message="Setting timers...", 
      color=LogColor.NORMAL
    )

    self.clock.set_timer(
      name=WeatherTimer.WEATHER_MODEL_CALIBRATION_TIMER.value,
      start_time=self._calculate_start_time(),
      interval=Timedelta(days=settings.WEATHER_CALIBRATOR_SETTINGS.DATA_CALIBRATION_INTERVAL_DAYS),
      callback=self._on_model_calibration_timer,
      fire_immediately=True
    )

    self.log.info(
      message="All timers set successfully", 
      color=LogColor.GREEN
    )

    # Notify WeatherStateActor that this ingestor is ready to receive requests
    self.msgbus.send(
      endpoint=WeatherEndpoint.WEATHER_MODEL_CALIBRATION_STATUS.value,
      msg=Status.READY
    )

  def on_stop(self) -> None:
    """
    This function is called when the actor is stopped.
    """
    self.log.info(
      message="Deregistering endpoints...", 
      color=LogColor.NORMAL
    )

    self.msgbus.deregister(
      endpoint=WeatherEndpoint.WEATHER_MODEL_CALIBRATION_REQUEST.value,
      handler=self._on_receive_model_calibration_request
    )

    self.log.info(
      message="All endpoints deregistered successfully", 
      color=LogColor.GREEN
    )
    self.log.info(
      message="Cancelling timers...", 
      color=LogColor.NORMAL
    )

    self.clock.cancel_timer(
      name=WeatherTimer.WEATHER_MODEL_CALIBRATION_TIMER.value
    )

    self.log.info(
      message="All timers cancelled successfully", 
      color=LogColor.GREEN
    )


  # ---- Message Handlers ----------------------------------

  def _on_receive_model_calibration_request(self, cities: dict[str, LocationModel]) -> None:
    """
    This function is called when a weather model calibration request is received.

    Parameters:
    ----------------
    cities (dict[str, LocationModel]): 
      The dictionary of cities for which to calibrate the model.
    """
    self.log.debug(
      message=f"Received {len(cities)} unique cities for model calibration",
      color=LogColor.CYAN
    )

    self.cities = cities

  def _on_model_calibration_timer(self, event: TimeEvent) -> None:
    """
    This function is called when the weather model calibration timer 
    expires.

    Parameters:
    ----------------
    event (TimeEvent):
      The timer event.
    """
    self.log.info(
      message=f"Retrieving weather calibration data for {len(self.cities)} cities from database...",
      color=LogColor.NORMAL
    )

    # Retrieve the calibration data for each city from the database
    calibration_data = {}
    for icao_code in self.cities.keys():
      try:
        city_calibration_data = self.database_adapter.load_weather_data(
          icao_code=icao_code,
          lookback_days=settings.WEATHER_CALIBRATOR_SETTINGS.DATA_CALIBRATION_LOOKBACK_DAYS
        )
        calibration_data[icao_code] = city_calibration_data

      except Exception as e:
        self.log.error(
          message=f"Error loading weather data for {icao_code} from database: {str(e)}",
          color=LogColor.RED
        )
        continue

    self.log.info(
      message=f"Calibrating weather model for {len(calibration_data)} cities...",
      color=LogColor.NORMAL
    )

    # Calibrate the model params for each city
    calibrated_params = {}
    for icao_code, city_calibration_data in calibration_data.items():
      try:
        params = self._calibrate_model_for_city(
          icao_code=icao_code,
          calibration_data=city_calibration_data
        )
        calibrated_params[icao_code] = params

      except Exception as e:
        self.log.error(
          message=f"Error calibrating weather model for {icao_code}: {str(e)}",
          color=LogColor.RED
        )
        continue

    # Save the calibrated model params for each city into the database
    for param in calibrated_params.values():
      try:
        self.database_adapter.save_model_parameters(
          params=param
        )

      except Exception as e:
        self.log.error(
          message=f"Error saving calibrated model parameters for {param.icao_code} into the database: {str(e)}",
          color=LogColor.RED
        )
        continue

    self.log.info(
      message=f"Saved model params for {len(calibrated_params)} cities into the database",
      color=LogColor.GREEN
    )


  # ---- Helper Handlers -----------------------------------

  def _calculate_start_time(self) -> datetime:
    """
    This function calculates the start time for the model calibration timer.

    Returns:
    ----------------
    datetime:
      The start time for the model calibration in UTC.
    """
    target_hour = settings.WEATHER_CALIBRATOR_SETTINGS.DATA_CALIBRATION_TARGET_HOUR
    target_day = settings.WEATHER_CALIBRATOR_SETTINGS.DATA_CALIBRATION_INTERVAL_DAYS

    current_time_local = Timestamp.now(tz="Asia/Kuala_Lumpur")
    start_time_local = current_time_local.normalize() + Timedelta(hours=6, minutes=5)

    if current_time_local >= start_time_local:
      start_time_local += Timedelta(days=target_day)

    start_time_utc = start_time_local.tz_convert(timezone.utc).to_pydatetime().replace(tzinfo=None)
    return start_time_utc
  
  def _emos_gaussian_neg_log_likelihood(
    self, 
    params: ndarray, 
    ens_means: ndarray, 
    ens_stdevs: ndarray, 
    actuals: ndarray
  ) -> float:
    """
    Calculates the Negative Log-Likelihood for a Gaussian EMOS model.

    Parameters
    ----------------
    params (ndarray):
      The EMOS parameters [a, b, c, d] where:
        a: additive bias correction
        b: multiplicative bias correction on the ensemble mean
        c: intercept for variance (must be > 0)
        d: multiplicative factor for ensemble variance (must be > 0)

    ens_means (ndarray):
      The array of ensemble mean forecasts.

    ens_stdevs (ndarray):
      The array of ensemble standard deviations.

    actuals (ndarray):
      The array of actual observed values.

    Returns
    ----------------
    float:
      The negative log-likelihood of the observed data under the EMOS model with 
      the given parameters
    """
    a, b, c, d = params
    
    # EMOS Linear Mean Transformation
    mu = a + b * ens_means
    
    # EMOS Variance Transformation
    ens_variance = ens_stdevs ** 2
    variance = c + d * ens_variance
    
    # Structural safety check to prevent taking log of zero or negative variance
    if any(variance <= 0):
      return 1e10

    # Calculate Gaussian Negative Log-Likelihood
    sigma = sqrt(variance)
    log_likelihood = norm.logpdf(actuals, loc=mu, scale=sigma)
    
    return float(-sum(log_likelihood))
  
  def _calibrate_model_for_city(
    self, 
    icao_code: str,
    calibration_data: DataFrame
  ) -> WeatherCalibrationParams:
    """
    This function calibrates the EMOS model for a specific city using the provided calibration data.

    Parameters
    ----------------    
    icao_code (str):
      The ICAO code of the city for which the model is being calibrated.

    calibration_data (DataFrame):
      The DataFrame containing the calibration data for the city.

    Returns
    ----------------
    WeatherCalibrationParams:
      The calibrated EMOS model parameters for the city.
    """
    init_a, init_b, init_c, init_d = 0.0, 1.0, 0.01, 1.0

    # Extract raw arrays and compute stddev from variance
    ensemble_mean = calibration_data["ensemble_mean"].values
    ensemble_stdev = calibration_data["ensemble_stdev"].values
    historical_max = calibration_data["temperature_2m_max"].values

    # Initial guess: [a=0 (no bias), b=1 (scale 1:1), c=0.01 (baseline var), d=1 (scale 1:1)]
    initial_guess = array([init_a, init_b, init_c, init_d])

    # Set strict physical bounds
    bounds = [
      (None, None),   # 'a' can be any additive shift (positive or negative)
      (0.1, 3.0),     # 'b' multiplicative mean scale constraint
      (0.05, None),   # 'c' baseline variance floor (prevents division-by-zero risks)
      (0.05, None)    # 'd' variance scaling multiplier floor
    ]

    # Run the Scipy Solver
    result = minimize(
      fun=self._emos_gaussian_neg_log_likelihood,
      x0=initial_guess,
      args=(ensemble_mean, ensemble_stdev, historical_max),
      bounds=bounds,
      method="L-BFGS-B"
    )

    if not result.success:
      return WeatherCalibrationParams(
        icao_code=icao_code,
        last_updated=datetime.now(),
        a=init_a, 
        b=init_b, 
        c=init_c, 
        d=init_d
      )

    a, b, c, d = result.x
    return WeatherCalibrationParams(
      icao_code=icao_code,
      last_updated=datetime.now(),
      a=float(a),
      b=float(b),
      c=float(c),
      d=float(d)
    )
