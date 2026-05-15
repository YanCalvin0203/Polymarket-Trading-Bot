from nautilus_trader.config import ActorConfig
from nautilus_trader.common.actor import Actor
from nautilus_trader.common.enums import LogColor
from src.enums.common import Status
from src.enums.weather import WeatherEndpoint
from src.models.weather.manifest import WeatherManifestModel
from src.oracle.weather import WeatherEnsemble


class WeatherForecastIngestorActorConfig(ActorConfig):
  """
  This class contains all the configurations for the WeatherForecastIngestor actor.
  """
  pass


class WeatherForecastIngestorActor(Actor):
  """
  This class implements the WeatherForecastIngestor actor, which is responsible for
  ingesting weather forecast data and publishing it to the message bus.
  """

  def __init__(self, config: WeatherForecastIngestorActorConfig) -> None:
    """
    This function initializes the WeatherForecastIngestorActor class.

    Parameters:
    ----------------
    config (WeatherForecastIngestorActorConfig): The configuration for the 
      WeatherForecastIngestorActor.
    """
    super().__init__(config)
    self.ensemble = WeatherEnsemble()


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
      endpoint=WeatherEndpoint.WEATHER_FORECAST_REQUEST.value,
      handler=self._on_receive_forecast_request
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
      endpoint=WeatherEndpoint.WEATHER_FORECAST_STATUS.value,
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
      endpoint=WeatherEndpoint.WEATHER_FORECAST_REQUEST.value,
      handler=self._on_receive_forecast_request
    )

    self.log.info(
      message="All endpoints deregistered successfully", 
      color=LogColor.GREEN
    )


  # ---- Message Handlers -----------------------------------

  def _on_receive_forecast_request(self, manifests: dict[str, WeatherManifestModel]) -> None:
    """
    This method is called when a weather forecasts request is received.

    Parameters:
    ----------------
    manifests (dict[str, WeatherManifestModel]): The manifests requests message.
    """
    self.log.debug(
      message=f"Received {len(manifests)} forecast data requests",
      color=LogColor.CYAN
    )

    forecasts_data = self.ensemble.get_forecasts(manifests)

    self.log.info(
      message=f"Retrieved forecasts data for {len(forecasts_data)} events",
      color=LogColor.GREEN
    )
    self.log.info(
      message=f"Sending forecast updates for {len(forecasts_data)} events...",
      color=LogColor.NORMAL
    )

    self.msgbus.send(
      endpoint=WeatherEndpoint.WEATHER_FORECAST_UPDATE.value,
      msg=forecasts_data
    )
