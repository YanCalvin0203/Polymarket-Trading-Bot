from datetime import datetime, timezone
from pandas import Timedelta, Timestamp
from nautilus_trader.config import ActorConfig
from nautilus_trader.common.actor import Actor
from nautilus_trader.common.enums import LogColor
from nautilus_trader.common.events import TimeEvent
from src.enums.common import Status
from src.enums.weather import WeatherTimer, WeatherEndpoint
from src.database.weather_adapter import WeatherPostgresAdapter
from src.calibrator.weather.emos_calibrator import WeatherEMOSCalibrator
from src.settings import settings
from src.models.weather import LocationModel


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
    self.calibrator = WeatherEMOSCalibrator()


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
        params = self.calibrator.calibrate_model_for_city(
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
    target_day = settings.WEATHER_CALIBRATOR_SETTINGS.DATA_CALIBRATION_TARGET_DAY

    current_time_local = Timestamp.now(tz="Asia/Kuala_Lumpur")
    start_time_local = current_time_local.normalize() + Timedelta(hours=target_hour)

    days_until_target = (target_day - current_time_local.dayofweek) % 7
    if days_until_target == 0 and current_time_local >= start_time_local:
      days_until_target = 7

    start_time_local += Timedelta(days=days_until_target)
    start_time_utc = start_time_local.tz_convert(timezone.utc).to_pydatetime().replace(tzinfo=None)
    return start_time_utc
  