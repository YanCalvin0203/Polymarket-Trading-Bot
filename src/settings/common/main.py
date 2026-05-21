from pydantic_settings import BaseSettings
from src.settings.common.node import NodeConfig
from src.settings.common.database import DatabaseConfig
from src.settings.weather.oracle import WeatherOracleSettings
from src.settings.weather.slug_builder import WeatherSlugBuilderConfig
from src.settings.weather.collector import WeatherCollectorSettings
from src.settings.weather.trainer import WeatherTrainerSettings


class MainSettings(BaseSettings):
  """
  This class loads the env variables and program specific parameters for 
  the program.
  """
  NODE_CONFIG: NodeConfig                               = NodeConfig()
  DATABASE_CONFIG: DatabaseConfig                       = DatabaseConfig()
  WEATHER_SLUG_BUILDER_CONFIG: WeatherSlugBuilderConfig = WeatherSlugBuilderConfig()
  WEATHER_ORACLE_SETTINGS: WeatherOracleSettings        = WeatherOracleSettings()
  WEATHER_COLLECTOR_SETTINGS: WeatherCollectorSettings  = WeatherCollectorSettings()
  WEATHER_TRAINER_SETTINGS: WeatherTrainerSettings      = WeatherTrainerSettings()


# ---- Public API -------------------------------------

settings = MainSettings()
