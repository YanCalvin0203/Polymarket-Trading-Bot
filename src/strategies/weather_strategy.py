from src.models.weather_model import WeatherEvent, WeatherMarket
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.trading.config import StrategyConfig


class WeatherStrategyConfig(StrategyConfig):
  """
  This class contains all the configurations for the WeatherStrategy.
  """
  pass


class WeatherStrategy(Strategy):
  """
  This class implements the trading strategy for weather markets.
  """

  def __init__(self, config: WeatherStrategyConfig) -> None:
    """
    This function initializes the WeatherStrategy class.

    Parameters:
    ----------------
    config (WeatherStrategyConfig): The configuration for the WeatherStrategy.
    """
    super().__init__(config)

  def on_start(self) -> None:
    """
    This method is called when the strategy is started.
    """
    all_instruments = self.cache.instruments()

  def on_stop(self) -> None:
    """
    This method is called when the strategy is stopped.
    """
    pass
