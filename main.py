from src.settings import settings
from nautilus_trader.live.node import TradingNode
from nautilus_trader.live.config import TradingNodeConfig
from nautilus_trader.trading.config import ImportableStrategyConfig
from nautilus_trader.common.config import ImportableActorConfig
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


  # ---- Strategy Configurations ---------------------

  weather_strategy_config = ImportableStrategyConfig(
    strategy_path=settings.NODE_CONFIG.WEATHER_STRATEGY_PATH,
    config_path=settings.NODE_CONFIG.WEATHER_STRATEGY_CONFIG_PATH,
    config={}
  )


  # ---- Actor Configurations -----------------------
  
  weather_state_actor_config = ImportableActorConfig(
    actor_path=settings.NODE_CONFIG.WEATHER_STATE_ACTOR_PATH,
    config_path=settings.NODE_CONFIG.WEATHER_STATE_ACTOR_CONFIG_PATH,
    config={}
  )
  weather_forecast_ingestor_actor_config = ImportableActorConfig(
    actor_path=settings.NODE_CONFIG.WEATHER_FORECAST_INGESTOR_ACTOR_PATH,
    config_path=settings.NODE_CONFIG.WEATHER_FORECAST_INGESTOR_ACTOR_CONFIG_PATH,
    config={}
  )
  weather_observation_ingestor_actor_config = ImportableActorConfig(
    actor_path=settings.NODE_CONFIG.WEATHER_OBSERVATION_INGESTOR_ACTOR_PATH,
    config_path=settings.NODE_CONFIG.WEATHER_OBSERVATION_INGESTOR_ACTOR_CONFIG_PATH,
    config={}
  )
  weather_data_collector_actor_config = ImportableActorConfig(
    actor_path=settings.NODE_CONFIG.WEATHER_DATA_COLLECTOR_ACTOR_PATH,
    config_path=settings.NODE_CONFIG.WEATHER_DATA_COLLECTOR_ACTOR_CONFIG_PATH,
    config={}
  )
  weather_predictor_calibrator_actor_config = ImportableActorConfig(
    actor_path=settings.NODE_CONFIG.WEATHER_PREDICTOR_CALIBRATOR_ACTOR_PATH,
    config_path=settings.NODE_CONFIG.WEATHER_PREDICTOR_CALIBRATOR_ACTOR_CONFIG_PATH,
    config={}
  )
  weather_predictor_actor_config = ImportableActorConfig(
    actor_path=settings.NODE_CONFIG.WEATHER_PREDICTOR_ACTOR_PATH,
    config_path=settings.NODE_CONFIG.WEATHER_PREDICTOR_ACTOR_CONFIG_PATH,
    config={}
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
    strategies=[
      weather_strategy_config,
    ],
    actors=[
      # ---- State Actors --------------------------------
      weather_state_actor_config,


      # ---- Component Actors ----------------------------
      weather_forecast_ingestor_actor_config,
      weather_observation_ingestor_actor_config,
      weather_data_collector_actor_config,
      weather_predictor_calibrator_actor_config,
      weather_predictor_actor_config,
    ]
  )


  # ---- Engine Setup And Execution -----------------

  node = TradingNode(
    config=node_config,
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
