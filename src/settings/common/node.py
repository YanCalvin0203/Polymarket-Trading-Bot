import os

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from nautilus_trader.common import Environment
from src.utils.path_builder import make_path


class NodeConfig(BaseSettings):
  """
  This class contains all the configuration variables for the trading node.
  """
  model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore",
    env_prefix="POLYMARKET_"
  )

  TRADER_ID: str = "WEATHER-TRADER"
  ENVIRONMENT: Environment = Environment.SANDBOX

  # ---- Client Names --------------------------------

  WEATHER_CLIENT_NAME: str = "WEATHER"

  # ---- Package Paths --------------------------------

  _UTILS_PACKAGE: str = "src.utils"
  _ACTOR_PACKAGE: str = "src.actors"
  _STRATEGY_PACKAGE: str = "src.strategies"

  # ---- Slug Builder Paths --------------------------

  WEATHER_SLUG_BUILDER_PATH: str = make_path(
    package=_UTILS_PACKAGE,
    module="slug_builder",
    class_name="weather_slug_builder"
  )

  # ---- Strategy Paths ------------------------------

  WEATHER_STRATEGY_PATH: str = make_path(
    package=_STRATEGY_PACKAGE,
    module="weather_strategy",
    class_name="WeatherStrategy"
  )
  WEATHER_STRATEGY_CONFIG_PATH: str = make_path(
    package=_STRATEGY_PACKAGE,
    module="weather_strategy",
    class_name="WeatherStrategyConfig"
  )

  # ---- Actor Paths --------------------------------

  WEATHER_STATE_ACTOR_PATH: str = make_path(
    package=_ACTOR_PACKAGE,
    domain="weather",
    module="state_actor",
    class_name="WeatherStateActor"
  )
  WEATHER_STATE_ACTOR_CONFIG_PATH: str = make_path(
    package=_ACTOR_PACKAGE,
    domain="weather",
    module="state_actor",
    class_name="WeatherStateActorConfig"
  )
  WEATHER_FORECAST_INGESTOR_ACTOR_PATH: str = make_path(
    package=_ACTOR_PACKAGE,
    domain="weather",
    module="forecast_ingestor_actor",
    class_name="WeatherForecastIngestorActor"
  )
  WEATHER_FORECAST_INGESTOR_ACTOR_CONFIG_PATH: str = make_path(
    package=_ACTOR_PACKAGE,
    domain="weather",
    module="forecast_ingestor_actor",
    class_name="WeatherForecastIngestorActorConfig"
  )
  WEATHER_OBSERVATION_INGESTOR_ACTOR_PATH: str = make_path(
    package=_ACTOR_PACKAGE,
    domain="weather",
    module="observation_ingestor_actor",
    class_name="WeatherObservationIngestorActor"
  )
  WEATHER_OBSERVATION_INGESTOR_ACTOR_CONFIG_PATH: str = make_path(
    package=_ACTOR_PACKAGE,
    domain="weather",
    module="observation_ingestor_actor",
    class_name="WeatherObservationIngestorActorConfig"
  )
  WEATHER_DATA_COLLECTOR_ACTOR_PATH: str = make_path(
    package=_ACTOR_PACKAGE,
    domain="weather",
    module="data_collector_actor",
    class_name="WeatherDataCollectorActor"
  )
  WEATHER_DATA_COLLECTOR_ACTOR_CONFIG_PATH: str = make_path(
    package=_ACTOR_PACKAGE,
    domain="weather",
    module="data_collector_actor",
    class_name="WeatherDataCollectorActorConfig"
  )

  # ---- Polymarket API Credentials ----------------------

  API_KEY: str = Field(
    description="The API key used for authentication when making Polymarket API calls."
  )
  API_SECRET: SecretStr = Field(
    description="The API secret used for authentication when making Polymarket API calls."
  )
  PASSPHRASE: SecretStr = Field(
    description="The API passphrase used for authentication when making Polymarket API calls."
  )

  # ---- Polymarket Account Credentials ------------------

  PK: SecretStr = Field(
    description="The private key used for signing Polymarket transactions."
  )
  FUNDER: str = Field(
    description="The address of the funder for the Polymarket account."
  )

  # ---- Public API --------------------------------------

  def inject_to_env(self) -> None:
    """
    This function injects the configuration variables into the environment variables.
    """
    env_prefix = self.model_config.get("env_prefix", "")
    dump = self.model_dump(
      exclude_defaults=True,
    )
    
    for key, value in dump.items():
      env_key = f"{env_prefix}{key}"
      env_value = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
      os.environ[env_key] = env_value

