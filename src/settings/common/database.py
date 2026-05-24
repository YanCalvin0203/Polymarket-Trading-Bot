from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
  """
  This class contains all the configuration variables for the database connection.
  """
  model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore",
    env_prefix="POSTGRES_"
  )

  POOL_SIZE: int = 5
  MAX_OVERFLOW: int = 10

  # ---- Database Names ----------------------------------

  WEATHER_DB: str = "weather_db"

  # ---- Connection Credentials --------------------------

  USER: str = Field(
    default="postgres",
    description="The username for the Postgres database connection."
  )
  PASSWORD: SecretStr = Field(
    description="The password for the Postgres database connection."
  )
  HOST: str = Field(
    default="127.0.0.1",
    description="The host for the Postgres database connection."
  )
  PORT: int = Field(
    default=5432,
    description="The port for the Postgres database connection."
  )

  # ---- Public API --------------------------------------

  def connection_string(self, database_name: str) -> str:
    """
    This function returns the connection string for the Postgres database.

    Parameters
    ----------------
    database_name (str):
      The name of the database to connect to.

    Returns
    ----------------
    str: The connection string for the Postgres database.
    """
    return f"postgresql://{self.USER}:{self.PASSWORD.get_secret_value()}@{self.HOST}:{self.PORT}/{database_name}"
  