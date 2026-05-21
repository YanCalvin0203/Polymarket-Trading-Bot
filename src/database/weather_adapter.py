from sqlalchemy import create_engine, text
from src.settings import settings
from pandas import DataFrame, read_sql_query
from src.models.weather import (
  WeatherHistoricalMaxModel,
  WeatherHistoricalForecastModel,
  WeatherCalibrationParams
)


# ---- SQL Queries -----------------------------------

CREATE_DATA_TABLE_QUERY = text(
  """
  CREATE TABLE IF NOT EXISTS weather_data (
    timestamp TIMESTAMPTZ NOT NULL,
    icao_code VARCHAR(10) NOT NULL,
    ensemble_mean FLOAT,
    ensemble_stdev FLOAT,
    temperature_2m_max FLOAT,
    PRIMARY KEY (timestamp, icao_code)
  );
  """
)

CREATE_DATA_INDEX_QUERY = text(
  """
  CREATE INDEX IF NOT EXISTS idx_weather_data_lookup 
  ON weather_data (icao_code, timestamp DESC);
  """
)

UPSERT_DATA_QUERY = text(
  """
  INSERT INTO weather_data (
    timestamp, 
    icao_code, 
    ensemble_mean, 
    ensemble_stdev, 
    temperature_2m_max
  ) VALUES (
    :timestamp, 
    :icao_code, 
    :ensemble_mean, 
    :ensemble_stdev, 
    :temperature_2m_max
  )
  ON CONFLICT (timestamp, icao_code) 
  DO UPDATE SET 
    ensemble_mean = EXCLUDED.ensemble_mean,
    ensemble_stdev = EXCLUDED.ensemble_stdev,
    temperature_2m_max = EXCLUDED.temperature_2m_max;
  """
)

LOAD_DATA_QUERY = text(
  """
  SELECT timestamp, ensemble_mean, ensemble_stdev, temperature_2m_max
  FROM weather_data
  WHERE icao_code = :icao_code
    AND timestamp >= NOW() - INTERVAL '1 day' * :lookback_days
  ORDER BY timestamp DESC;
  """
)

CREATE_PARAMS_TABLE_QUERY = text(
  """
  CREATE TABLE IF NOT EXISTS model_parameters (
    icao_code VARCHAR(10) NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL,
    param_a FLOAT NOT NULL,
    param_b FLOAT NOT NULL,
    param_c FLOAT NOT NULL,
    param_d FLOAT NOT NULL,
    PRIMARY KEY (icao_code)
  );
  """
)

UPSERT_PARAMS_QUERY = text(
  """
  INSERT INTO model_parameters (
    icao_code, 
    last_updated, 
    param_a, 
    param_b, 
    param_c, 
    param_d
  ) VALUES (
    :icao_code, 
    :last_updated, 
    :param_a, 
    :param_b, 
    :param_c, 
    :param_d
  )
  ON CONFLICT (icao_code) 
  DO UPDATE SET 
    last_updated = EXCLUDED.last_updated,
    param_a = EXCLUDED.param_a,
    param_b = EXCLUDED.param_b,
    param_c = EXCLUDED.param_c,
    param_d = EXCLUDED.param_d;
  """
)

# ---- Main Adapter Class ----------------------------

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
    self._create_schema_if_not_exists()


  # ---- Public API ----------------------------------

  def save_weather_data(
    self, 
    icao_code: str, 
    historical_max: WeatherHistoricalMaxModel, 
    historical_forecast: WeatherHistoricalForecastModel
  ) -> None:
    """
    This function saves the weather data to the Postgres database.

    Parameters:
    ----------------
    icao_code (str): 
      The ICAO code of the city for which the weather data is being saved.

    historical_max (WeatherHistoricalMaxModel): 
      The historical max model containing the max temperature data.

    historical_forecast (WeatherHistoricalForecastModel): 
      The historical forecast model containing the forecast data.
    """
    payload = self._combine_historical_data(
      icao_code=icao_code,
      historical_max=historical_max,
      historical_forecast=historical_forecast
    )
    if payload is None:
      return None
    
    # Convert the combined DataFrame into a list of dictionaries for bulk upsert
    data_records = payload.to_dict(orient="records")
    
    with self.engine.begin() as connection:
      connection.execute(UPSERT_DATA_QUERY, data_records)

  def save_model_parameters(self, params: WeatherCalibrationParams) -> None:
    """
    This function saves the calibrated model parameters to the Postgres database.

    Parameters:
    ----------------
    params (WeatherCalibrationParams): 
      The calibrated model parameters to be saved.
    """
    with self.engine.begin() as connection:
      connection.execute(
        UPSERT_PARAMS_QUERY,
        {
          "icao_code": params.icao_code,
          "last_updated": params.last_updated,
          "param_a": params.a,
          "param_b": params.b,
          "param_c": params.c,
          "param_d": params.d
        }
      )

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
    with self.engine.connect() as connection:
      return read_sql_query(
        sql=LOAD_DATA_QUERY,
        con=connection,
        params={
          "icao_code": icao_code,
          "lookback_days": lookback_days
        },
        parse_dates=["timestamp"]
      )


  # ---- Internal Helpers ----------------------------

  def _create_schema_if_not_exists(self) -> None:
    """
    This function creates the weather_data table in the Postgres database if it 
    does not already exist.
    """
    with self.engine.begin() as connection:
      connection.execute(CREATE_DATA_TABLE_QUERY)
      connection.execute(CREATE_DATA_INDEX_QUERY)
      connection.execute(CREATE_PARAMS_TABLE_QUERY)

  def _combine_historical_data(
    self, 
    icao_code: str,
    historical_max: WeatherHistoricalMaxModel, 
    historical_forecast: WeatherHistoricalForecastModel
  ) -> DataFrame | None:
    """
    This function combines the historical maximum temperature data and the 
    historical forecast data into a single DataFrame.

    Parameters:
    ----------------
    icao_code (str): 
      The ICAO code of the city for which the data is being combined.

    historical_max (WeatherHistoricalMaxModel): 
      The historical max model containing the max temperature data.

    historical_forecast (WeatherHistoricalForecastModel): 
      The historical forecast model containing the forecast data.

    Returns:
    ----------------
    DataFrame | None: 
      A combined DataFrame containing both maximum temperature and forecast data, 
      or None if either DataFrame is empty.
    """
    max_temperature_df = historical_max.historical_max_data
    forecast_df = historical_forecast.historical_forecast_data

    if max_temperature_df is None or forecast_df is None:
      return None
    
    if max_temperature_df.empty or forecast_df.empty:
      return None
    
    # Align the DataFrames perfectly on the timezone aware index (timestamp)
    combined_df = max_temperature_df.join(
      forecast_df,
      how="inner"
    )

    # Reset the index to turn the timestamp into an explicit column
    combined_df.reset_index(inplace=True)
    combined_df.rename(columns={combined_df.columns[0]: "timestamp"}, inplace=True)

    # Inject the identifier metadata column
    combined_df["icao_code"] = icao_code

    # Map the columns to the expected format for the database
    payload = combined_df[[
      "timestamp",
      "icao_code",
      "ensemble_mean",
      "ensemble_stdev",
      "temperature_2m_max"
    ]]

    return payload
