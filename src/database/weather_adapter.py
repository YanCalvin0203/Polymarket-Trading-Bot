from sqlalchemy import (
  create_engine, 
  MetaData,
  Table, 
  Column, 
  String, 
  Float, 
  Integer,
  DateTime, 
  Index,
  select, 
  desc
)
from datetime import datetime, timezone, timedelta
from pandas import DataFrame, read_sql_query
from sqlalchemy.dialects.postgresql import insert
from src.settings import settings
from src.models.weather import (
  WeatherDataCollectionActualMaxModel,
  WeatherDataCollectionForecastModel,
  WeatherCalibrationParamsModel
)


class WeatherPostgresAdapter:
  """
  This class implements the Postgres adapter for the Weather domain, which is
  responsible for connecting to the Postgres database and executing queries.
  """
  
  def __init__(self) -> None:
    """
    This function initializes the WeatherPostgresAdapter class.
    """
    self.engine = create_engine(
      url=settings.DATABASE_CONFIG.connection_string(
        database_name=settings.DATABASE_CONFIG.WEATHER_DB
      ),
      pool_size=settings.DATABASE_CONFIG.POOL_SIZE,
      max_overflow=settings.DATABASE_CONFIG.MAX_OVERFLOW,
    )

    self.metadata = MetaData()

    # ---- Tables --------------------------------------

    self.weather_data_table = Table(
      "weather_data",
      self.metadata,
      Column("timestamp", DateTime(timezone=True), nullable=False),
      Column("icao_code", String(5), primary_key=True, nullable=False),
      Column("lead_days", Integer, primary_key=True, nullable=False),
      Column("resolution_date", DateTime(timezone=True), primary_key=True, nullable=False),
      Column("ensemble_mean", Float),
      Column("ensemble_stdev", Float),
      Column("actual_max", Float),
    )

    Index(
      "idx_weather_data_lookup",
      self.weather_data_table.c.icao_code,
      desc(self.weather_data_table.c.resolution_date),
      self.weather_data_table.c.lead_days,
    )

    self.model_parameters_table = Table(
      "model_parameters",
      self.metadata,
      Column("icao_code", String(5), primary_key=True, nullable=False),
      Column("lead_days", Integer, primary_key=True, nullable=False),
      Column("last_updated", DateTime(timezone=True), nullable=False),
      Column("param_a", Float, nullable=False),
      Column("param_b", Float, nullable=False),
      Column("param_c", Float, nullable=False),
      Column("param_d", Float, nullable=False),
    )

    self._create_schema_if_not_exists()


  # ---- Public API ----------------------------------

  def save_forecast_data(
    self, 
    icao_code: str, 
    forecast_data_list: list[WeatherDataCollectionForecastModel]
  ) -> None:
    """
    This function saves the weather forecast data to the Postgres database.

    Parameters:
    ----------------
    icao_code (str): 
      The ICAO code of the city for which the weather data is being saved.

    forecast_data_list (list[WeatherDataCollectionForecastModel]): 
      The list of collected forecast data to be saved.
    """
    if len(forecast_data_list) == 0:
      return
    
    payload_records = []
    for forecast_data in forecast_data_list:
      payload_records.append(
        {
          "timestamp": forecast_data.created_at,
          "icao_code": icao_code,
          "lead_days": forecast_data.lead_days,
          "resolution_date": forecast_data.resolution_date,
          "ensemble_mean": float(forecast_data.ensemble_mean),
          "ensemble_stdev": float(forecast_data.ensemble_stdev),
        }
      )
    
    insert_statement = insert(self.weather_data_table).values(payload_records)
    upsert_statement = insert_statement.on_conflict_do_update(
      index_elements=["icao_code", "lead_days", "resolution_date"],
      set_={
        "timestamp": insert_statement.excluded.timestamp,
        "ensemble_mean": insert_statement.excluded.ensemble_mean,
        "ensemble_stdev": insert_statement.excluded.ensemble_stdev,
      }
    )
    
    with self.engine.begin() as connection:
      connection.execute(upsert_statement)

  def save_actual_max_data(
    self, 
    icao_code: str, 
    actual_max_data_list: list[WeatherDataCollectionActualMaxModel]
  ) -> None:
    """
    This function saves the actual max weather data to the Postgres database.

    Parameters:
    ----------------
    icao_code (str): 
      The ICAO code of the city for which the weather data is being saved.

    actual_max_data_list (list[WeatherDataCollectionActualMaxModel]): 
      The list of collected actual max data to be saved.
    """
    if len(actual_max_data_list) == 0:
      return
    
    lead_days = settings.WEATHER_ORACLE_SETTINGS.DATA_COLLECTION_LOOKAHEAD_DAYS

    payload_records = []
    for actual_max_data in actual_max_data_list:
      for day in range(lead_days + 1):
        payload_records.append(
          {
            "timestamp": actual_max_data.created_at,
            "icao_code": icao_code,
            "lead_days": day,
            "resolution_date": actual_max_data.resolution_date,
            "actual_max": float(actual_max_data.actual_max),
          }
        )

    insert_statement = insert(self.weather_data_table).values(payload_records)
    upsert_statement = insert_statement.on_conflict_do_update(
      index_elements=["icao_code", "lead_days", "resolution_date"],
      set_={
        "timestamp": insert_statement.excluded.timestamp,
        "actual_max": insert_statement.excluded.actual_max,
      }
    )
    
    with self.engine.begin() as connection:
      connection.execute(upsert_statement)

  def save_model_parameters(self, params_list: list[WeatherCalibrationParamsModel]) -> None:
    """
    This function saves the calibrated model parameters to the Postgres database.

    Parameters:
    ----------------
    params_list (list[WeatherCalibrationParamsModel]): 
      The calibrated model parameters to be saved.
    """
    if len(params_list) == 0:
      return
    
    payload_records = []
    for params in params_list:
      payload_records.append(
        {
          "icao_code": params.icao_code,
          "lead_days": params.lead_days,
          "last_updated": params.last_updated,
          "param_a": float(params.a),
          "param_b": float(params.b),
          "param_c": float(params.c),
          "param_d": float(params.d)
        }
      )

    insert_statement = insert(self.model_parameters_table).values(payload_records)
    upsert_statement = insert_statement.on_conflict_do_update(
      index_elements=["icao_code", "lead_days"],
      set_={
        "last_updated": insert_statement.excluded.last_updated,
        "param_a": insert_statement.excluded.param_a,
        "param_b": insert_statement.excluded.param_b,
        "param_c": insert_statement.excluded.param_c,
        "param_d": insert_statement.excluded.param_d
      }
    )

    with self.engine.begin() as connection:
      connection.execute(upsert_statement)

  def load_weather_data(
    self, 
    icao_code: str, 
    lookback_days: int
  ) -> DataFrame:
    """
    This function loads the weather data from the Postgres database for a given
    ICAO code and lookback period.

    Parameters:
    ----------------
    icao_code (str): 
      The ICAO code of the city for which to load the weather data.

    lookback_days (int): 
      The number of days to look back for the weather data.

    Returns:
    ----------------
    DataFrame:
      A DataFrame containing the weather data for the specified ICAO code and lookback 
      period.
    """
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=lookback_days)
    statement = select(self.weather_data_table).where(
      self.weather_data_table.c.icao_code == icao_code,
      self.weather_data_table.c.resolution_date >= cutoff_date,
      self.weather_data_table.c.ensemble_mean.is_not(None),
      self.weather_data_table.c.ensemble_stdev.is_not(None),
      self.weather_data_table.c.actual_max.is_not(None)
    )

    with self.engine.connect() as connection:
      return read_sql_query(
        sql=statement,
        con=connection,
        parse_dates=["timestamp", "resolution_date"]
      )

  def load_model_parameters(
    self, 
    icao_code: str, 
    lead_days: int
  ) -> WeatherCalibrationParamsModel | None:
    """
    This function loads the calibrated model parameters from the Postgres database for a 
    given ICAO code.

    Parameters:
    ----------------
    icao_code (str): 
      The ICAO code of the city for which to load the model parameters.
    
    lead_days (int): 
      The number of days into the future for which to load the model parameters.

    Returns:
    ----------------
    WeatherCalibrationParamsModel | None:
      The loaded model parameters for the specified ICAO code, or None if no parameters 
      are found.
    """
    statement = select(self.model_parameters_table).where(
      self.model_parameters_table.c.icao_code == icao_code,
      self.model_parameters_table.c.lead_days == lead_days,
    )
    with self.engine.connect() as connection:
      result = connection.execute(statement).fetchone()

    if result is None:
      return None
    
    return WeatherCalibrationParamsModel(
      icao_code=result.icao_code,
      lead_days=result.lead_days,
      last_updated=result.last_updated,
      a=result.param_a,
      b=result.param_b,
      c=result.param_c,
      d=result.param_d
    )

  # ---- Internal Helpers ----------------------------

  def _create_schema_if_not_exists(self) -> None:
    """
    This function creates the weather_data table in the Postgres database 
    if it does not already exist.
    """
    with self.engine.begin() as connection:
      self.metadata.create_all(connection)
