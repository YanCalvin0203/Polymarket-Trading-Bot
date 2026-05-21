from sqlalchemy import create_engine, text
from src.settings import settings
from pandas import DataFrame
from src.models.weather import (
  WeatherHistoricalMaxModel,
  WeatherHistoricalForecastModel
)


# ---- SQL Queries -----------------------------------

CREATE_TABLE_QUERY = text(
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

CREATE_INDEX_QUERY = text(
  """
  CREATE INDEX IF NOT EXISTS idx_weather_data_lookup 
  ON weather_data (icao_code, timestamp DESC);
  """
)

UPSERT_QUERY = text(
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
      connection.execute(UPSERT_QUERY, data_records)


  # ---- Internal Helpers ----------------------------

  def _create_schema_if_not_exists(self) -> None:
    """
    This function creates the weather_data table in the Postgres database if it 
    does not already exist.
    """
    with self.engine.begin() as connection:
      connection.execute(CREATE_TABLE_QUERY)
      connection.execute(CREATE_INDEX_QUERY)

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
