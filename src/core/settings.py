import os

from typing import Any
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from nautilus_trader.common import Environment


# ---- Module Specific Configurations -----------------

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

  WEATHER_CLIENT_NAME: str = "WEATHER"
  WEATHER_SLUG_BUILDER_PATH: str = "src.utils.slug_builder:weather_slug_builder"

  WEATHER_STRATEGY_PATH: str = "src.strategies.weather_strategy:WeatherStrategy"
  WEATHER_STRATEGY_CONFIG_PATH: str = "src.strategies.weather_strategy:WeatherStrategyConfig"

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
    This method injects the configuration variables into the environment variables.
    """
    env_prefix = self.model_config.get("env_prefix", "")
    dump = self.model_dump(
      exclude_defaults=True,
    )
    
    for key, value in dump.items():
      env_key = f"{env_prefix}{key}"
      env_value = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
      os.environ[env_key] = env_value

  
class WeatherSlugBuilderConfig:
  """
  This class contains all the configuration variables for the weather scanner.
  """
  TIME_RANGE: int = 3
  CITIES: list[str] = ["nyc"]


class WeatherOracleSettings:
  """
  This class contains all the configuration variables for the oracle.
  """
  # ---- Ensemble ----------------------------------------

  ENSEMBLE_ENDPOINT: str = "https://ensemble-api.open-meteo.com/v1/ensemble"
  ENSEMBLE_QUERY_PARAMS: dict[str, Any] = {
    "hourly": ["temperature_2m"],
    "models": "ecmwf_ifs025",
    "timezone": "auto"
  }
  ENSEMBLE_COUNT: int = 51

  # ---- Observation -------------------------------------

  METAR_ENDPOINT: str = "https://aviationweather.gov/api/data/metar"
  METAR_QUERY_PARAMS: dict[str, Any] = {
    "format": "json"
  }

  # ---- HTTP --------------------------------------------

  RETRY_RETRIES: int = 3
  RETRY_BACKOFF_FACTOR: float = 0.2

  REQUEST_DELAY: float = 0.01
  REQUEST_TIMEOUT: int = 10



# ---- Public API Configuration --------------------------

class MainSettings(BaseSettings):
  """
  This class loads the env variables and program specific parameters for 
  the program.
  """
  NODE_CONFIG: NodeConfig                               = NodeConfig()
  WEATHER_SLUG_BUILDER_CONFIG: WeatherSlugBuilderConfig = WeatherSlugBuilderConfig()
  WEATHER_ORACLE_SETTINGS: WeatherOracleSettings        = WeatherOracleSettings()

# ---- Public API -------------------------------------

settings = MainSettings()
