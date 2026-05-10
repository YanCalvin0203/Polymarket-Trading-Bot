from src.core.settings import settings
from nautilus_trader.live.node import (
  TradingNode, 
  TradingNodeConfig,
)
from nautilus_trader.adapters.polymarket.config import (
  PolymarketDataClientConfig,
  PolymarketExecClientConfig,
)
from nautilus_trader.adapters.polymarket.factories import (
  PolymarketLiveDataClientFactory,
  PolymarketLiveExecClientFactory,
)
from nautilus_trader.adapters.polymarket.providers import (
  PolymarketInstrumentProviderConfig,
)


def main() -> None:
  """
  This function is the main entry point to the application.
  """
  # Load the env variables from the .env file
  settings.NODE_CONFIG.inject_to_env()

  # ---- Instrument Provider Configurations ----------

  weather_instrument_provider_config = PolymarketInstrumentProviderConfig(
    load_all=True,
    event_slug_builder=settings.NODE_CONFIG.WEATHER_SLUG_BUILDER_PATH
  )


  # ---- Data Client Configurations ------------------

  weather_data_client_config = PolymarketDataClientConfig(
    instrument_config=weather_instrument_provider_config
  )


  # ---- Execution Client Configurations -------------

  weather_exec_client_config = PolymarketExecClientConfig(
    instrument_config=weather_instrument_provider_config
  )


  # ---- Client Configurations ----------------------

  node_config = TradingNodeConfig(
    trader_id=settings.NODE_CONFIG.TRADER_ID,
    environment=settings.NODE_CONFIG.ENVIRONMENT,
    data_clients={
      settings.NODE_CONFIG.WEATHER_CLIENT_NAME: weather_data_client_config
    },
    exec_clients={
      settings.NODE_CONFIG.WEATHER_CLIENT_NAME: weather_exec_client_config
    },
  )


  # ---- Engine Setup And Execution -----------------

  node = TradingNode(
    config=node_config
  )
  node.add_data_client_factory(
    name=settings.NODE_CONFIG.WEATHER_CLIENT_NAME, 
    factory=PolymarketLiveDataClientFactory
  )
  node.add_exec_client_factory(
    name=settings.NODE_CONFIG.WEATHER_CLIENT_NAME,
    factory=PolymarketLiveExecClientFactory
  )

  node.build()
  node.run()


if __name__ == "__main__":
  main()
