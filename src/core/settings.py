import os

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
  CITIES: list[str] = ["nyc", "los-angeles", "chicago"]


# ---- Public API Configuration -----------------------

class MainSettings(BaseSettings):
  """
  This class loads the env variables and program specific parameters for 
  the program.
  """
  NODE_CONFIG: NodeConfig = NodeConfig()
  WEATHER_SLUG_BUILDER_CONFIG: WeatherSlugBuilderConfig = WeatherSlugBuilderConfig()


# ---- Public API -------------------------------------

settings = MainSettings()
