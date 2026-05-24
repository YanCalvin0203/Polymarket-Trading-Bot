from nautilus_trader.config import ActorConfig
from nautilus_trader.common.actor import Actor
from nautilus_trader.common.enums import LogColor
from src.enums.common import Status
from src.enums.weather import WeatherEndpoint
from src.predictors.weather_predictor import WeatherPredictor
from src.models.weather import WeatherEventModel


class WeatherPredictorActorConfig(ActorConfig):
  """
  This class contains all the configurations for the WeatherPredictor actor.
  """
  pass


class WeatherPredictorActor(Actor):
  """
  This class implements the WeatherPredictorActor, which is responsible for 
  generating weather predictions.
  """
  
  def __init__(self, config: WeatherPredictorActorConfig) -> None:
    """
    This function initializes the WeatherPredictorActor class.

    Parameters
    ----------------
    config (WeatherPredictorActorConfig): 
      The configuration for the WeatherPredictorActor.
    """
    super().__init__(config)
    self.predictor = WeatherPredictor()


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
      endpoint=WeatherEndpoint.WEATHER_PREDICTION_REQUEST.value,
      handler=self._on_receive_prediction_request
    )

    self.log.info(
      message="All endpoints registered successfully", 
      color=LogColor.GREEN
    )

    # Notify WeatherStateActor that this ingestor is ready to receive requests
    self.msgbus.send(
      endpoint=WeatherEndpoint.WEATHER_PREDICTION_STATUS.value,
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
      endpoint=WeatherEndpoint.WEATHER_PREDICTION_REQUEST.value,
      handler=self._on_receive_prediction_request
    )

    self.log.info(
      message="All endpoints deregistered successfully", 
      color=LogColor.GREEN
    )


  # ---- Message Handlers ----------------------------------

  def _on_receive_prediction_request(
    self, 
    events: dict[str, WeatherEventModel]
  ) -> None:
    """
    This function is called when a prediction request is received.

    Parameters
    ----------------
    events (dict[str, WeatherEventModel]):
      The weather events request message.
    """
    self.log.debug(
      message=f"Received prediction request for {len(events)} events",
      color=LogColor.CYAN
    )

    predictions = {}
    for event_id, event in events.items():
      event_prediction_model = self.predictor.predict_event_probability(event=event)
      if event_prediction_model is not None:
        predictions[event_id] = event_prediction_model

    self.log.info(
      message=f"Computed probabilities for {len(events)} events",
      color=LogColor.GREEN
    )
    self.log.info(
      message=f"Sending probability updates for {len(events)} events...",
      color=LogColor.NORMAL
    )

    self.msgbus.send(
      endpoint=WeatherEndpoint.WEATHER_PREDICTION_UPDATE.value,
      msg=predictions
    )
