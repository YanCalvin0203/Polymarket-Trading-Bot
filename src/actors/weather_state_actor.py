from nautilus_trader.config import ActorConfig
from nautilus_trader.common.actor import Actor
from src.parsers.weather_parser import WeatherParser
from src.models.weather.components import (
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
    self.parser = WeatherParser()
    

  # ---- Lifecycle Methods ----------------------------------

  def on_start(self) -> None:
    """
    This method is called when the actor is started.
    """
    self.msgbus.subscribe(
      topic="weather_forecast_update", 
      handler=self._on_forecast_update
    )
    self.msgbus.subscribe(
      topic="weather_observation_update", 
      handler=self._on_observation_update
    )

    all_instruments = self.cache.instruments()
    self.events = self.parser.parse_instruments(all_instruments)

    self.manifests = self.parser.parse_manifests(self.events)
    self.msgbus.publish(
      topic="weather_data_requests",
      msg=self.manifests
    )

  def on_stop(self) -> None:
    """
    This method is called when the actor is stopped.
    """
    self.msgbus.unsubscribe(
      topic="weather_forecast_update", 
      handler=self._on_forecast_update
    )
    self.msgbus.unsubscribe(
      topic="weather_observation_update", 
      handler=self._on_observation_update
    )


  # ---- Message Handlers ----------------------------------

  def _on_forecast_update(self, forecast_update: dict[str, WeatherForecastModel]) -> None:
    """
    This method is called when a forecast update message is received.

    Parameters:
    ----------------
    forecast_update (dict[str, WeatherForecastModel]): The forecast update message.
    """
    for event_id, forecast in forecast_update.items():
      if self.events.get(event_id, None) is not None:
        self.events[event_id].forecast = forecast

  def _on_observation_update(self, observation_update: dict[str, WeatherObservationModel]) -> None:
    """
    This method is called when an observation update message is received.

    Parameters:
    ----------------
    observation_update (dict[str, WeatherObservationModel]): The observation update message.
    """
    for event_id, observation in observation_update.items():
      if self.events.get(event_id, None) is not None:
        self.events[event_id].observation = observation
