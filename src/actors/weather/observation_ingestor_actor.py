from nautilus_trader.config import ActorConfig
from nautilus_trader.common.actor import Actor
from nautilus_trader.common.enums import LogColor
from src.enums.common import Status
from src.enums.weather import WeatherEndpoint
from src.models.weather.manifest import WeatherManifestModel
from src.oracle.weather import WeatherMetar


class WeatherObservationIngestorActorConfig(ActorConfig):
  """
  This class contains all the configurations for the WeatherObservationIngestor actor.
  """
  pass


class WeatherObservationIngestorActor(Actor):
  """
  This class implements the WeatherObservationIngestor actor, which is responsible for
  ingesting weather observation data and publishing it to the message bus.
  """

  def __init__(self, config: WeatherObservationIngestorActorConfig) -> None:
    """
    This function initializes the WeatherObservationIngestorActor class.

    Parameters:
    ----------------
    config (WeatherObservationIngestorActorConfig): The configuration for the 
      WeatherObservationIngestorActor.
    """
    super().__init__(config)
    self.metar = WeatherMetar()


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
      endpoint=WeatherEndpoint.WEATHER_OBSERVATION_REQUEST.value,
      handler=self._on_receive_observation_request
    )

    self.log.info(
      message="All endpoints registered successfully", 
      color=LogColor.GREEN
    )
    self.log.debug(
      message="Initializing handshake with State Actor...", 
      color=LogColor.CYAN
    )

    # Notify WeatherStateActor that this ingestor is ready to receive requests
    self.msgbus.send(
      endpoint=WeatherEndpoint.WEATHER_OBSERVATION_STATUS.value,
      msg=Status.READY
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
      endpoint=WeatherEndpoint.WEATHER_OBSERVATION_REQUEST.value,
      handler=self._on_receive_observation_request
    )

    self.log.info(
      message="All endpoints deregistered successfully", 
      color=LogColor.GREEN
    )


  # ---- Message Handlers -----------------------------------

  def _on_receive_observation_request(self, manifests: dict[str, WeatherManifestModel]) -> None:
    """
    This method is called when a weather observations request is received.

    Parameters:
    ----------------
    manifests (dict[str, WeatherManifestModel]): The manifests requests message.
    """
    self.log.debug(
      message=f"Received {len(manifests)} observation data requests",
      color=LogColor.CYAN
    )

    observations_data = self.metar.get_observations(manifests)

    self.log.info(
      message=f"Retrieved observation data for {len(observations_data)} events",
      color=LogColor.GREEN
    )
    self.log.info(
      message=f"Sending observation updates for {len(observations_data)} events...",
      color=LogColor.NORMAL
    )

    self.msgbus.send(
      endpoint=WeatherEndpoint.WEATHER_OBSERVATION_UPDATE.value,
      msg=observations_data
    )
