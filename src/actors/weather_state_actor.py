from nautilus_trader.config import ActorConfig
from nautilus_trader.common.actor import Actor
from nautilus_trader.common.enums import LogColor
from src.core.enums.common import Status
from src.core.enums.weather import WeatherEndpoint
from src.parsers.weather_parser import WeatherParser
from src.models.weather import (
  WeatherForecastModel, 
  WeatherObservationModel
)


class WeatherStateActorConfig(ActorConfig):
  """
  This class contains all the configurations for the WeatherState actor.
  """
  pass


class WeatherStateActor(Actor):
  """
  This class implements the WeatherState actor, which is responsible for 
  maintaining the state of the weather markets.
  """

  def __init__(self, config: WeatherStateActorConfig) -> None:
    """
    This function initializes the WeatherStateActor class.

    Parameters:
    ----------------
    config (WeatherStateActorConfig): The configuration for the WeatherStateActor.
    """
    super().__init__(config)
    self.events = {}
    self.manifests = {}
    self.parser = WeatherParser()
    

  # ---- Lifecycle Methods ----------------------------------

  def on_start(self) -> None:
    """
    This method is called when the actor is started.
    """
    self.log.info(
      message="Registering endpoints...", 
      color=LogColor.NORMAL
    )

    self.msgbus.register(
      endpoint=WeatherEndpoint.WEATHER_FORECAST_STATUS.value,
      handler=self._on_forecast_status
    )
    self.msgbus.register(
      endpoint=WeatherEndpoint.WEATHER_OBSERVATION_STATUS.value,
      handler=self._on_observation_status
    )
    self.msgbus.register(
      endpoint=WeatherEndpoint.WEATHER_FORECAST_UPDATE.value,
      handler=self._on_forecast_update
    )
    self.msgbus.register(
      endpoint=WeatherEndpoint.WEATHER_OBSERVATION_UPDATE.value,
      handler=self._on_observation_update
    )

    self.log.info(
      message="All endpoints registered successfully", 
      color=LogColor.GREEN
    )
    self.log.info(
      message="Parsing initial instrument and manifest data...",
      color=LogColor.NORMAL
    )

    all_instruments = self.cache.instruments()
    self.events = self.parser.parse_instruments(all_instruments)
    self.manifests = self.parser.parse_manifests(self.events)

    self.log.info(
      message=f"Parsed {len(self.events)} events and {len(self.manifests)} manifests successfully",
      color=LogColor.GREEN
    )

  def on_stop(self) -> None:
    """
    This method is called when the actor is stopped.
    """
    self.log.info(
      message="Deregistering endpoints...", 
      color=LogColor.NORMAL
    )

    self.msgbus.deregister(
      endpoint=WeatherEndpoint.WEATHER_FORECAST_STATUS.value,
      handler=self._on_forecast_status
    )
    self.msgbus.deregister(
      endpoint=WeatherEndpoint.WEATHER_OBSERVATION_STATUS.value,
      handler=self._on_observation_status
    )
    self.msgbus.deregister(
      endpoint=WeatherEndpoint.WEATHER_FORECAST_UPDATE.value,
      handler=self._on_forecast_update
    )
    self.msgbus.deregister(
      endpoint=WeatherEndpoint.WEATHER_OBSERVATION_UPDATE.value,
      handler=self._on_observation_update
    )

    self.log.info(
      message="All endpoints deregistered successfully", 
      color=LogColor.GREEN
    )


  # ---- Message Handlers ----------------------------------

  def _on_forecast_update(
      self, 
      forecast_update: dict[str, WeatherForecastModel]
    ) -> None:
    """
    This method is called when a forecast update message is received.

    Parameters
    ----------------
    forecast_update (dict[str, WeatherForecastModel]): The forecast update message.
    """
    self.log.debug(
      message=f"Received forecast update for {len(forecast_update)} events",
      color=LogColor.CYAN
    )

    for event_id, forecast in forecast_update.items():
      if self.events.get(event_id, None) is not None:
        self.events[event_id].forecast = forecast

    self.log.info(
      message=f"Updated forecasts for {len(forecast_update)} events",
      color=LogColor.GREEN
    )

  def _on_observation_update(
      self, 
      observation_update: dict[str, WeatherObservationModel]
    ) -> None:
    """
    This method is called when an observation update message is received.

    Parameters
    ----------------
    observation_update (dict[str, WeatherObservationModel]): The observation update message.
    """
    self.log.debug(
      message=f"Received observation update for {len(observation_update)} events",
      color=LogColor.CYAN
    )

    for event_id, observation in observation_update.items():
      if self.events.get(event_id, None) is not None:
        self.events[event_id].observation = observation

    self.log.info(
      message=f"Updated observations for {len(observation_update)} events",
      color=LogColor.GREEN
    )

  def _on_forecast_status(self, status: Status) -> None:
    """
    This method is called when a forecast status message is received.

    Parameters
    ----------------
    status (Status): The forecast status message.
    """
    self.log.debug(
      message=f"Received forecast status: {status.value}",
      color=LogColor.CYAN
    )

    if status == Status.READY:
      self.log.info(
        message=f"Sending {len(self.manifests)} forecast data requests...",
        color=LogColor.NORMAL
      )

      self.msgbus.send(
        endpoint=WeatherEndpoint.WEATHER_FORECAST_REQUEST.value,
        msg=self.manifests,
      )

  def _on_observation_status(self, status: Status) -> None:
    """
    This method is called when an observation status message is received.

    Parameters
    ----------------
    status (Status): The observation status message.
    """
    self.log.debug(
      message=f"Received observation status: {status.value}",
      color=LogColor.CYAN
    )

    if status == Status.READY:
      self.log.info(
        message=f"Sending {len(self.manifests)} observation data requests...",
        color=LogColor.NORMAL
      )
      self.msgbus.send(
        endpoint=WeatherEndpoint.WEATHER_OBSERVATION_REQUEST.value,
        msg=self.manifests,
      )
