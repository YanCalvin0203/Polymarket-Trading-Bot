from datetime import datetime, timezone
from pandas import Timedelta, Timestamp
from nautilus_trader.config import ActorConfig
from nautilus_trader.common.actor import Actor
from nautilus_trader.common.enums import LogColor
from nautilus_trader.common.events import TimeEvent
from src.enums.common import Status
from src.enums.weather import WeatherTimer, WeatherEndpoint
from src.oracle.weather.ensemble import WeatherEnsemble
from src.database.weather_adapter import WeatherPostgresAdapter
from src.models.weather import LocationModel
from src.settings import settings


class WeatherDataCollectorActorConfig(ActorConfig):
  """
  This class contains all the configurations for the WeatherDataCollector actor.
  """
  pass


class WeatherDataCollectorActor(Actor):
  """
  This class implements the WeatherDataCollector actor, which is responsible for 
  collecting historical weather data and publishing it to the message bus.
  """

  def __init__(self, config: WeatherDataCollectorActorConfig) -> None:
    """
    This function initializes the WeatherDataCollectorActor class.

    Parameters:
    ----------------
    config (WeatherDataCollectorActorConfig): 
      The configuration for the WeatherDataCollectorActor.
    """
    super().__init__(config)
    self.cities = {}
    self.ensemble = WeatherEnsemble()
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
      endpoint=WeatherEndpoint.WEATHER_DATA_COLLECTION_REQUEST.value,
      handler=self._on_receive_data_collection_request
    )

    self.log.info(
      message="All endpoints registered successfully", 
      color=LogColor.GREEN
    )
    self.log.debug(
      message="Initializing handshake with State Actor...", 
      color=LogColor.CYAN
    )

    self.log.info(
      message="Setting timers...", 
      color=LogColor.NORMAL
    )

    self.clock.set_timer(
      name=WeatherTimer.WEATHER_DATA_COLLECTION_TIMER.value,
      start_time=self._calculate_start_time(),
      interval=Timedelta(days=settings.WEATHER_COLLECTOR_SETTINGS.DATA_COLLECTION_INTERVAL_DAYS),
      callback=self._on_data_collection_timer,
      fire_immediately=True
    )

    self.log.info(
      message="All timers set successfully", 
      color=LogColor.GREEN
    )

    # Notify WeatherStateActor that this ingestor is ready to receive requests
    self.msgbus.send(
      endpoint=WeatherEndpoint.WEATHER_DATA_COLLECTION_STATUS.value,
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
      endpoint=WeatherEndpoint.WEATHER_DATA_COLLECTION_REQUEST.value,
      handler=self._on_receive_data_collection_request
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
      name=WeatherTimer.WEATHER_DATA_COLLECTION_TIMER.value
    )

    self.log.info(
      message="All timers cancelled successfully", 
      color=LogColor.GREEN
    )


  # ---- Message Handlers ----------------------------------

  def _on_receive_data_collection_request(self, cities: dict[str, LocationModel]) -> None:
    """
    This function is called when a weather data collection request is received.

    Parameters:
    ----------------
    cities (dict[str, LocationModel]): 
      The dictionary of cities for which to collect data.
    """
    self.log.debug(
      message=f"Received {len(cities)} unique cities for data collection",
      color=LogColor.CYAN
    )

    self.cities = cities

  def _on_data_collection_timer(self, event: TimeEvent) -> None:
    """
    This function is called when the weather data collection timer 
    expires.

    Parameters:
    ----------------
    event (TimeEvent):
      The timer event.
    """
    self.log.info(
      message=f"Collecting weather data for {len(self.cities)} cities...",
      color=LogColor.NORMAL
    )
    
    historical_max = self.ensemble.get_historical_max(
      cities=self.cities,
      historical_range_days=settings.WEATHER_ORACLE_SETTINGS.HISTORICAL_RANGE_DAYS
    )
    historical_forecast = self.ensemble.get_historical_forecasts(
      cities=self.cities,
      historical_range_days=settings.WEATHER_ORACLE_SETTINGS.HISTORICAL_RANGE_DAYS
    )

    self.log.info(
      message=f"Collected weather data for {len(self.cities)} cities",
      color=LogColor.GREEN
    )

    for icao_code in self.cities.keys():
      historical_max_model = historical_max.get(icao_code, None)
      historical_forecast_model = historical_forecast.get(icao_code, None)

      if historical_max_model is None and historical_forecast_model is None:
        continue

      try:
        self.database_adapter.save_weather_data(
          icao_code=icao_code,
          historical_max=historical_max_model,
          historical_forecast=historical_forecast_model
        )

      except Exception as e:
        self.log.error(
          message=f"Error saving weather data for {icao_code} into the database: {str(e)}",
          color=LogColor.RED
         )
        continue

    self.log.info(
      message=f"Saved weather data for {len(self.cities)} cities into the database",
      color=LogColor.GREEN
    )
  
  
  # ---- Helper Handlers -----------------------------------

  def _calculate_start_time(self) -> datetime:
    """
    This function calculates the start time for the historical data collection timer.

    Returns:
    ----------------
    datetime:
      The start time for the historical data collection in UTC.
    """
    target_hour = settings.WEATHER_COLLECTOR_SETTINGS.DATA_COLLECTION_TARGET_HOUR
    target_day = settings.WEATHER_COLLECTOR_SETTINGS.DATA_COLLECTION_INTERVAL_DAYS

    current_time_local = Timestamp.now(tz="Asia/Kuala_Lumpur")
    start_time_local = current_time_local.normalize() + Timedelta(hours=target_hour)

    if current_time_local >= start_time_local:
      start_time_local += Timedelta(days=target_day)

    start_time_utc = start_time_local.tz_convert(timezone.utc).to_pydatetime().replace(tzinfo=None)
    return start_time_utc
  