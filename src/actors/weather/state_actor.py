from pandas import Timedelta
from nautilus_trader.config import ActorConfig
from nautilus_trader.common.actor import Actor
from nautilus_trader.common.enums import LogColor
from nautilus_trader.common.events import TimeEvent
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.adapters.polymarket.common.symbol import get_polymarket_instrument_id
from src.enums.common import Status
from src.enums.weather import WeatherEndpoint, WeatherTimer
from src.parsers.weather import WeatherParser
from src.models.weather import (
  WeatherEventModel,
  WeatherEventPredictionModel,
  WeatherForecastModel,
  WeatherObservationModel,
)
from src.models.weather.events import WeatherMarketModel
from src.models.common import PricingModel


class WeatherStateActorConfig(ActorConfig):
  """
  This class contains all the configurations for the WeatherState actor.
  """
  update_interval_minutes: int = 60


class WeatherStateActor(Actor):
  """
  This class implements the WeatherState actor, which is responsible for 
  maintaining the state of the weather markets.
  """

  def __init__(self, config: WeatherStateActorConfig) -> None:
    """
    This function initializes the WeatherStateActor class.

    Parameters
    ----------------
    config (WeatherStateActorConfig): 
      The configuration for the WeatherStateActor.
    """
    super().__init__(config)
    self.events: dict[str, WeatherEventModel] = {}
    self.manifests = {}
    self.cities = {}
    self.predictions = {}
    self.parser = WeatherParser()
    # Maps each YES/NO InstrumentId → (market_model, side) for quote routing
    self._instrument_map: dict[InstrumentId, tuple[WeatherMarketModel, str]] = {}
    self._predictor_ready = False
    self._strategy_ready = False
    

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
      endpoint=WeatherEndpoint.WEATHER_FORECAST_STATUS.value,
      handler=self._on_forecast_status
    )
    self.msgbus.register(
      endpoint=WeatherEndpoint.WEATHER_OBSERVATION_STATUS.value,
      handler=self._on_observation_status
    )
    self.msgbus.register(
      endpoint=WeatherEndpoint.WEATHER_DATA_COLLECTION_STATUS.value,
      handler=self._on_data_collection_status
    )
    self.msgbus.register(
      endpoint=WeatherEndpoint.WEATHER_MODEL_CALIBRATION_STATUS.value,
      handler=self._on_model_calibration_status
    )
    self.msgbus.register(
      endpoint=WeatherEndpoint.WEATHER_PREDICTION_STATUS.value,
      handler=self._on_prediction_status
    )
    self.msgbus.register(
      endpoint=WeatherEndpoint.WEATHER_FORECAST_UPDATE.value,
      handler=self._on_forecast_update
    )
    self.msgbus.register(
      endpoint=WeatherEndpoint.WEATHER_OBSERVATION_UPDATE.value,
      handler=self._on_observation_update
    )
    self.msgbus.register(
      endpoint=WeatherEndpoint.WEATHER_PREDICTION_UPDATE.value,
      handler=self._on_prediction_update
    )
    self.msgbus.register(
      endpoint=WeatherEndpoint.WEATHER_STRATEGY_STATUS.value,
      handler=self._on_strategy_status
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
    self.cities = self.parser.parse_cities(self.events)

    self.log.info(
      message=f"Parsed {len(self.events)} events and {len(self.manifests)} manifests successfully",
      color=LogColor.GREEN
    )

    self._subscribe_market_quotes()

    self.log.info(
      message="Setting update timer...",
      color=LogColor.NORMAL
    )

    self.clock.set_timer(
      name=WeatherTimer.WEATHER_UPDATE_TIMER.value,
      interval=Timedelta(minutes=self.config.update_interval_minutes),
      callback=self._on_update_timer,
      fire_immediately=False,
    )

    self.log.info(
      message=f"Update timer set to fire every {self.config.update_interval_minutes} minutes",
      color=LogColor.GREEN
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
      endpoint=WeatherEndpoint.WEATHER_FORECAST_STATUS.value,
      handler=self._on_forecast_status
    )
    self.msgbus.deregister(
      endpoint=WeatherEndpoint.WEATHER_OBSERVATION_STATUS.value,
      handler=self._on_observation_status
    )
    self.msgbus.deregister(
      endpoint=WeatherEndpoint.WEATHER_DATA_COLLECTION_STATUS.value,
      handler=self._on_data_collection_status
    )
    self.msgbus.deregister(
      endpoint=WeatherEndpoint.WEATHER_MODEL_CALIBRATION_STATUS.value,
      handler=self._on_model_calibration_status
    )
    self.msgbus.deregister(
      endpoint=WeatherEndpoint.WEATHER_PREDICTION_STATUS.value,
      handler=self._on_prediction_status
    )
    self.msgbus.deregister(
      endpoint=WeatherEndpoint.WEATHER_FORECAST_UPDATE.value,
      handler=self._on_forecast_update
    )
    self.msgbus.deregister(
      endpoint=WeatherEndpoint.WEATHER_OBSERVATION_UPDATE.value,
      handler=self._on_observation_update
    )
    self.msgbus.deregister(
      endpoint=WeatherEndpoint.WEATHER_PREDICTION_UPDATE.value,
      handler=self._on_prediction_update
    )
    self.msgbus.deregister(
      endpoint=WeatherEndpoint.WEATHER_STRATEGY_STATUS.value,
      handler=self._on_strategy_status
    )

    self.log.info(
      message="All endpoints deregistered successfully",
      color=LogColor.GREEN
    )

    self.clock.cancel_timer(
      name=WeatherTimer.WEATHER_UPDATE_TIMER.value
    )

    for instrument_id in self._instrument_map:
      self.unsubscribe_quote_ticks(instrument_id)
    self._instrument_map.clear()


  # ---- Quote Tick Handler ----------------------------------

  def on_quote_tick(self, tick: QuoteTick) -> None:
    """
    This function is called when a quote tick is received for a subscribed instrument.
    Updates the relevant market's PricingModel with the latest best bid/ask.

    Parameters
    ----------------
    tick (QuoteTick):
      The incoming quote tick.
    """
    entry = self._instrument_map.get(tick.instrument_id)
    if entry is None:
      return

    market, side = entry
    ask = float(tick.ask_price)
    bid = float(tick.bid_price)

    if side == "YES":
      market.prices.best_yes_ask = ask
      market.prices.best_yes_bid = bid
    else:
      market.prices.best_no_ask = ask
      market.prices.best_no_bid = bid


  # ---- Timer Handlers ----------------------------------

  def _on_update_timer(self, _event: TimeEvent) -> None:
    """
    This function is called on each update timer tick. It re-parses the latest
    instruments from the cache to pick up fresh market prices, then triggers
    forecast and observation refresh.

    Parameters
    ----------------
    event (TimeEvent):
      The timer event.
    """
    self.log.info(
      message="Update timer fired — refreshing instruments, forecasts and observations...",
      color=LogColor.NORMAL
    )

    all_instruments = self.cache.instruments()
    self.events = self.parser.parse_instruments(all_instruments)
    self.manifests = self.parser.parse_manifests(self.events)
    self.cities = self.parser.parse_cities(self.events)

    self.log.info(
      message=f"Refreshed {len(self.events)} events and {len(self.manifests)} manifests",
      color=LogColor.GREEN
    )

    self._subscribe_market_quotes()

    self.msgbus.send(
      endpoint=WeatherEndpoint.WEATHER_FORECAST_REQUEST.value,
      msg=self.manifests,
    )
    self.msgbus.send(
      endpoint=WeatherEndpoint.WEATHER_OBSERVATION_REQUEST.value,
      msg=self.manifests,
    )


  # ---- Message Handlers ----------------------------------

  def _on_forecast_update(
      self, 
      forecast_update: dict[str, WeatherForecastModel]
    ) -> None:
    """
    This function is called when a forecast update message is received.

    Parameters
    ----------------
    forecast_update (dict[str, WeatherForecastModel]): 
      The forecast update message.
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

    if not self._predictor_ready:
      return

    self.log.info(
      message=f"Sending {len(self.events)} prediction requests...",
      color=LogColor.NORMAL
    )

    self.msgbus.send(
      endpoint=WeatherEndpoint.WEATHER_PREDICTION_REQUEST.value,
      msg=self.events,
    )

  def _on_observation_update(
      self, 
      observation_update: dict[str, WeatherObservationModel]
    ) -> None:
    """
    This function is called when an observation update message is received.

    Parameters
    ----------------
    observation_update (dict[str, WeatherObservationModel]): 
      The observation update message.
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

  def _on_prediction_update(
      self,
      prediction_update: dict[str, WeatherEventPredictionModel]
    ) -> None:
    """
    This function is called when a prediction update message is received.

    Parameters
    ----------------
    prediction_update (dict[str, WeatherEventPredictionModel]): 
      The prediction update message.
    """
    self.log.debug(
      message=f"Received prediction update for {len(prediction_update)} events",
      color=LogColor.CYAN
    )

    self.predictions = prediction_update

    self.log.info(
      message=f"Updated predictions for {len(prediction_update)} events",
      color=LogColor.GREEN
    )

    if not self._strategy_ready:
      return

    self._send_evaluate_payload()

  def _on_forecast_status(self, status: Status) -> None:
    """
    This function is called when a forecast status message is received.

    Parameters
    ----------------
    status (Status): 
      The forecast status message.
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
    This function is called when an observation status message is received.

    Parameters
    ----------------
    status (Status): 
      The observation status message.
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

  def _on_data_collection_status(self, status: Status) -> None:
    """
    This function is called when a data collection status message is received.

    Parameters
    ----------------
    status (Status): 
      The data collection status message.
    """
    self.log.debug(
      message=f"Received data collection status: {status.value}",
      color=LogColor.CYAN
    )

    if status == Status.READY:
      self.log.info(
        message=f"Sending {len(self.cities)} unique cities for data collection...",
        color=LogColor.NORMAL
      )
      self.msgbus.send(
        endpoint=WeatherEndpoint.WEATHER_DATA_COLLECTION_REQUEST.value,
        msg=self.cities,
      )

  def _on_model_calibration_status(self, status: Status) -> None:
    """
    This function is called when a model calibration status message is received.

    Parameters
    ----------------
    status (Status): 
      The model calibration status message.
    """
    self.log.debug(
      message=f"Received model calibration status: {status.value}",
      color=LogColor.CYAN
    )

    if status == Status.READY:
      self.log.info(
        message=f"Sending {len(self.cities)} unique cities for model calibration...",
        color=LogColor.NORMAL
      )
      self.msgbus.send(
        endpoint=WeatherEndpoint.WEATHER_MODEL_CALIBRATION_REQUEST.value,
        msg=self.cities,
      )

  def _on_strategy_status(self, status: Status) -> None:
    """
    Called when WeatherStrategy signals it is ready.
    Replays the latest predictions so the strategy doesn't miss the first cycle.

    Parameters
    ----------------
    status (Status):
      The strategy status message.
    """
    self.log.debug(
      message=f"Received strategy status: {status.value}",
      color=LogColor.CYAN
    )

    if status == Status.READY:
      self._strategy_ready = True
      if self.predictions:
        self._send_evaluate_payload()


  # ---- Internal Helpers ----------------------------------

  def _send_evaluate_payload(self) -> None:
    evaluate_payload: dict[str, tuple[WeatherEventModel, WeatherEventPredictionModel]] = {
      event_id: (self.events[event_id], prediction)
      for event_id, prediction in self.predictions.items()
      if event_id in self.events
    }
    self.log.info(
      message=f"Sending {len(evaluate_payload)} events to strategy for evaluation...",
      color=LogColor.NORMAL
    )
    self.msgbus.send(
      endpoint=WeatherEndpoint.WEATHER_STRATEGY_EVALUATE.value,
      msg=evaluate_payload,
    )

  def _subscribe_market_quotes(self) -> None:
    """
    Builds the reverse InstrumentId → (market, side) map and subscribes to
    QuoteTick for every YES and NO token across all active events. Unsubscribes
    stale instruments that are no longer in the current event set.
    """
    new_map: dict[InstrumentId, tuple[WeatherMarketModel, str]] = {}

    for event in self.events.values():
      for market in event.markets.values():
        yes_id = get_polymarket_instrument_id(market.market_id, market.yes_token_id)
        no_id  = get_polymarket_instrument_id(market.market_id, market.no_token_id)
        new_map[yes_id] = (market, "YES")
        new_map[no_id]  = (market, "NO")

    stale_ids = set(self._instrument_map) - set(new_map)
    for instrument_id in stale_ids:
      self.unsubscribe_quote_ticks(instrument_id)

    new_ids = set(new_map) - set(self._instrument_map)
    for instrument_id in new_ids:
      self.subscribe_quote_ticks(instrument_id)

    self._instrument_map = new_map

    self.log.info(
      message=f"Subscribed to quote ticks for {len(new_ids)} new instrument(s), "
              f"unsubscribed {len(stale_ids)} stale instrument(s)",
      color=LogColor.GREEN,
    )


  def _on_prediction_status(self, status: Status) -> None:
    """
    This function is called when a prediction status message is received.

    Parameters
    ----------------
    status (Status): 
      The prediction status message.
    """
    self.log.debug(
      message=f"Received prediction status: {status.value}",
      color=LogColor.CYAN
    )

    if status == Status.READY:
      self._predictor_ready = True
      self.log.info(
        message=f"Sending {len(self.events)} prediction requests...",
        color=LogColor.NORMAL
      )
      self.msgbus.send(
        endpoint=WeatherEndpoint.WEATHER_PREDICTION_REQUEST.value,
        msg=self.events,
      )
