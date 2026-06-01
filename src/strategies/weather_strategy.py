from dataclasses import dataclass
from typing import Literal

from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.trading.config import StrategyConfig
from nautilus_trader.common.enums import LogColor
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.events import OrderFilled, PositionClosed
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.instruments import BinaryOption
from nautilus_trader.model.currencies import USDC
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.adapters.polymarket.common.symbol import get_polymarket_instrument_id

from src.enums.common import Status
from src.enums.weather import WeatherEndpoint
from src.models.weather.events import WeatherEventModel, WeatherMarketModel
from src.models.weather.components import (
  WeatherEventPredictionModel,
  WeatherMarketPredictionModel,
)


@dataclass(frozen=True, slots=True)
class BetSignal:
  market_id: str
  token_id: str | int
  side: Literal["YES", "NO"]
  edge: float
  model_probability: float
  market_price: float
  full_kelly: float
  recommended_stake: float

  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    return (
      f"---- Bet Signal -------------------------\n"
      f"market_id:          {self.market_id}\n"
      f"side:               {self.side}\n"
      f"edge:               {self.edge:.4f}\n"
      f"model_probability:  {self.model_probability:.4f}\n"
      f"market_price:       {self.market_price:.4f}\n"
      f"full_kelly:         {self.full_kelly:.4f}\n"
      f"recommended_stake:  ${self.recommended_stake:.2f}\n"
    )


class WeatherStrategyConfig(StrategyConfig):
  edge_threshold: float = 0.08
  kelly_fraction: float = 0.50
  max_stake_per_bet: float = 10.0
  bankroll: float = 100.0
  fade_model_threshold: float = 0.02


class WeatherStrategy(Strategy):
  """
  Buys undervalued YES/NO tokens on Polymarket weather temperature markets.

  Two tactics:
    - Standard edge: buy YES when model probability > market ask by >= edge_threshold.
    - Fade the impossible: buy NO when model probability <= fade_model_threshold
      and NO is underpriced by >= edge_threshold.

  Sizing uses fractional Kelly (kelly_fraction * full Kelly), capped at max_stake_per_bet.
  """

  def __init__(self, config: WeatherStrategyConfig) -> None:
    super().__init__(config)
    self._config = config


  # ---- Lifecycle Methods ----------------------------------

  def on_start(self) -> None:
    self.msgbus.register(
      endpoint=WeatherEndpoint.WEATHER_STRATEGY_EVALUATE.value,
      handler=self._on_evaluate,
    )
    self.log.info(
      message="WeatherStrategy ready — listening for evaluation requests",
      color=LogColor.GREEN,
    )
    self.msgbus.send(
      endpoint=WeatherEndpoint.WEATHER_STRATEGY_STATUS.value,
      msg=Status.READY,
    )

  def on_stop(self) -> None:
    self.msgbus.deregister(
      endpoint=WeatherEndpoint.WEATHER_STRATEGY_EVALUATE.value,
      handler=self._on_evaluate,
    )


  # ---- Public API ----------------------------------

  def evaluate_event(
    self,
    event: WeatherEventModel,
    prediction: WeatherEventPredictionModel,
  ) -> list[BetSignal]:
    """
    Evaluates all markets in an event and returns actionable bet signals.

    Parameters
    ----------------
    event (WeatherEventModel):
      The weather event containing all markets and their current prices.

    prediction (WeatherEventPredictionModel):
      The model's probability predictions for each market in the event.

    Returns
    ----------------
    list[BetSignal]:
      Signals sorted by edge descending. Empty if no edge found.
    """
    signals: list[BetSignal] = []

    for market_id, market in event.markets.items():
      market_pred = prediction.market_predictions.get(market_id)
      if market_pred is None:
        continue
      signal = self._evaluate_market(market, market_pred)
      if signal is not None:
        signals.append(signal)

    signals.sort(key=lambda s: s.edge, reverse=True)
    return signals

  def best_bet(
    self,
    event: WeatherEventModel,
    prediction: WeatherEventPredictionModel,
  ) -> BetSignal | None:
    """
    Returns the single highest-edge signal from the event, or None if no
    qualifying opportunity exists.
    """
    signals = self.evaluate_event(event, prediction)
    return signals[0] if signals else None


  # ---- Message Handlers ----------------------------------

  def _on_evaluate(
    self,
    payload: dict[str, tuple[WeatherEventModel, WeatherEventPredictionModel]],
  ) -> None:
    """
    This function is called when the StateActor sends fresh events and predictions
    for evaluation. Takes the best signal per event and submits a limit order for
    each qualifying opportunity that doesn't already have an open position.

    Parameters
    ----------------
    payload (dict[str, tuple[WeatherEventModel, WeatherEventPredictionModel]]):
      Map of event_id → (event, prediction) for every active event.
    """
    self.log.debug(
      message=f"Received evaluation request for {len(payload)} events",
      color=LogColor.CYAN,
    )

    orders_submitted = 0

    for _event_id, (event, prediction) in payload.items():
      signal = self.best_bet(event, prediction)
      if signal is None:
        continue

      submitted = self._submit_order_for_signal(signal)
      if submitted:
        orders_submitted += 1

    if orders_submitted == 0:
      self.log.info(
        message="No qualifying opportunities found across all events",
        color=LogColor.NORMAL,
      )
    else:
      self.log.info(
        message=f"Submitted {orders_submitted} order(s)",
        color=LogColor.GREEN,
      )


  # ---- Internal Helpers ----------------------------------

  def _submit_order_for_signal(self, signal: BetSignal) -> bool:
    """
    Resolves the instrument, checks for existing exposure, and submits a limit
    BUY order. Returns True if an order was submitted.

    Parameters
    ----------------
    signal (BetSignal):
      The signal to act on.

    Returns
    ----------------
    bool:
      True if the order was submitted, False otherwise.
    """
    instrument_id = get_polymarket_instrument_id(signal.market_id, signal.token_id)
    instrument = self.cache.instrument(instrument_id)

    if instrument is None:
      self.log.warning(
        message=f"Instrument not found in cache for {instrument_id} — skipping",
        color=LogColor.YELLOW,
      )
      return False

    if not isinstance(instrument, BinaryOption):
      self.log.warning(
        message=f"Unexpected instrument type {type(instrument)} for {instrument_id} — skipping",
        color=LogColor.YELLOW,
      )
      return False

    if self.cache.orders_open(instrument_id=instrument_id):
      self.log.debug(
        message=f"Open order already exists for {instrument_id} — skipping",
        color=LogColor.CYAN,
      )
      return False

    if self.portfolio.net_position(instrument_id) != 0:
      self.log.debug(
        message=f"Existing position for {instrument_id} — skipping",
        color=LogColor.CYAN,
      )
      return False

    price = Price(signal.market_price, instrument.price_precision)
    raw_quantity = signal.recommended_stake / signal.market_price
    quantity = Quantity(raw_quantity, instrument.size_precision)

    if quantity <= 0:
      self.log.warning(
        message=f"Computed quantity {quantity} is zero for {instrument_id} — skipping",
        color=LogColor.YELLOW,
      )
      return False

    order = self.order_factory.limit(
      instrument_id=instrument_id,
      order_side=OrderSide.BUY,
      quantity=quantity,
      price=price,
      time_in_force=TimeInForce.GTC,
    )

    self.submit_order(order)

    self.log.info(
      message=(
        f"Order submitted: {signal.side} {instrument_id} | "
        f"qty={quantity} @ {price} | edge={signal.edge:.4f} | stake=${signal.recommended_stake:.2f}"
      ),
      color=LogColor.GREEN,
    )

    return True

  def _evaluate_market(
    self,
    market: WeatherMarketModel,
    prediction: WeatherMarketPredictionModel,
  ) -> BetSignal | None:
    model_prob = prediction.predicted_probability
    yes_ask = market.prices.best_yes_ask
    no_ask = market.prices.best_no_ask

    # Standard edge: model says YES is underpriced
    if yes_ask > 0:
      yes_edge = model_prob - yes_ask
      if yes_edge >= self._config.edge_threshold:
        full_kelly = self._full_kelly(yes_edge, yes_ask)
        stake = self._kelly_stake(full_kelly)
        return BetSignal(
          market_id=market.market_id,
          token_id=market.yes_token_id,
          side="YES",
          edge=yes_edge,
          model_probability=model_prob,
          market_price=yes_ask,
          full_kelly=full_kelly,
          recommended_stake=stake,
        )

    # Fade the impossible: model says the event is near-zero, buy NO
    if no_ask > 0 and model_prob <= self._config.fade_model_threshold:
      model_no_prob = 1.0 - model_prob
      no_edge = model_no_prob - no_ask
      if no_edge >= self._config.edge_threshold:
        full_kelly = self._full_kelly(no_edge, no_ask)
        stake = self._kelly_stake(full_kelly)
        return BetSignal(
          market_id=market.market_id,
          token_id=market.no_token_id,
          side="NO",
          edge=no_edge,
          model_probability=model_no_prob,
          market_price=no_ask,
          full_kelly=full_kelly,
          recommended_stake=stake,
        )

    return None

  def on_order_filled(self, event: OrderFilled) -> None:
    self.log.info(
      message=(
        f"Fill: {event.instrument_id} | "
        f"qty={event.last_qty} @ {event.last_px} | "
        f"side={event.order_side.name}"
      ),
      color=LogColor.GREEN,
    )

  def on_position_closed(self, event: PositionClosed) -> None:
    position = event.position
    pnl = position.realized_pnl
    color = LogColor.GREEN if pnl is not None and float(pnl) >= 0 else LogColor.RED
    self.log.info(
      message=(
        f"Position closed: {position.instrument_id} | "
        f"realized_pnl={pnl} | "
        f"duration_ns={position.duration_ns}"
      ),
      color=color,
    )

  def _get_available_balance(self) -> float:
    account = self.cache.account_for_venue(Venue("POLYMARKET"))
    if account is None:
      return self._config.bankroll
    balance = account.balance_free(USDC)
    if balance is None:
      return self._config.bankroll
    return float(balance.as_decimal())

  def _full_kelly(self, edge: float, price: float) -> float:
    """
    Computes the full Kelly fraction of bankroll to bet.

    For a binary contract paying $1 on win:
      f* = (model_prob - price) / (1 - price) = edge / (1 - price)
    """
    if price <= 0.0 or price >= 1.0:
      return 0.0
    return edge / (1.0 - price)

  def _kelly_stake(self, full_kelly: float) -> float:
    """
    Applies fractional Kelly and the hard stake cap to produce a dollar amount.
    Uses live USDC balance from the portfolio, falling back to config bankroll.
    """
    bankroll = self._get_available_balance()
    raw = full_kelly * self._config.kelly_fraction * bankroll
    return min(raw, self._config.max_stake_per_bet)
