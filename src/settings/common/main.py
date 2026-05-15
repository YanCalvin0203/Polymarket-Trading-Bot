from pydantic_settings import BaseSettings
from src.settings.common.node import NodeConfig
from src.settings.weather.oracle import WeatherOracleSettings
from src.settings.weather.slug_builder import WeatherSlugBuilderConfig


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
