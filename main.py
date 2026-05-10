import asyncio

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


async def main() -> None:
  """
  This function is the main entry point to the application.
  """
  # Load the env variables from the .env file
  settings.NODE_CONFIG.inject_to_env()

  # ---- Client Configurations ----------------------

  data_client_config = PolymarketDataClientConfig()
  exec_client_config = PolymarketExecClientConfig()
  node_config = TradingNodeConfig(
    trader_id=settings.NODE_CONFIG.TRADER_ID,
    environment=settings.NODE_CONFIG.ENVIRONMENT,
    data_clients={
      settings.NODE_CONFIG.CLIENT_NAME: data_client_config
    },
    exec_clients={
      settings.NODE_CONFIG.CLIENT_NAME: exec_client_config
    },
  )

  # ---- Engine Setup And Execution------------------

  node = TradingNode(
    config=node_config
  )
  node.add_data_client_factory(
    name=settings.NODE_CONFIG.CLIENT_NAME, 
    factory=PolymarketLiveDataClientFactory
  )
  node.add_exec_client_factory(
    name=settings.NODE_CONFIG.CLIENT_NAME,
    factory=PolymarketLiveExecClientFactory
  )

  node.build()
  node.run()


if __name__ == "__main__":
  asyncio.run(main())
