from dataclasses import dataclass
from datetime import datetime
from pandas import DataFrame
from src.enums.weather.units import TemperatureUnit


@dataclass(slots=True)
class WeatherHistoricalMaxModel:
  historical_max_data: DataFrame
  last_updated: datetime

  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the
    WeatherHistoricalMaxModel instance.

    Returns
    --------------
    str: 
      The string representation of the WeatherHistoricalMaxModel 
      instance.
    """
    return (
      f"---- Weather Historical Max Model ----------------\n"
      f"historical_max_data: {self.historical_max_data},\n"
      f"last_updated:        {self.last_updated}\n"
    )
  

@dataclass(slots=True)
class WeatherHistoricalForecastModel:
  historical_forecast_data: DataFrame
  last_updated: datetime

  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the
    WeatherHistoricalForecastModel instance.

    Returns
    --------------
    str: 
      The string representation of the WeatherHistoricalForecastModel 
      instance.
    """
    return (
      f"---- Weather Historical Forecast Model ----------------\n"
      f"historical_forecast_data: {self.historical_forecast_data},\n"
      f"last_updated:             {self.last_updated}\n"
    )


@dataclass(slots=True)
class WeatherForecastModel:
  forecast_mean: float
  forecast_stdev: float
  last_updated: datetime

  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the WeatherForecastModel 
    instance.

    Returns
    --------------
    str: 
      The string representation of the WeatherForecastModel instance.
    """
    return (
      f"---- Weather Forecast Model ----------------------\n"
      f"forecast_mean:  {self.forecast_mean},\n"
      f"forecast_stdev:  {self.forecast_stdev},\n"
      f"last_updated:   {self.last_updated}\n"
    )
  
  
@dataclass(slots=True)
class WeatherObservationModel:
  observation_current: float
  observation_max: float
  last_updated: datetime

  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the WeatherObservationModel 
    instance.

    Returns
    --------------
    str: 
      The string representation of the WeatherObservationModel instance.
    """
    return (
      f"---- Weather Observation Model -------------------\n"
      f"observation_current: {self.observation_current},\n"
      f"observation_max:     {self.observation_max},\n"
      f"last_updated:        {self.last_updated}\n"
    )


@dataclass(frozen=True, slots=True)
class LocationModel:
  city_name: str
  icao_code: str
  timezone: str
  temperature_unit: TemperatureUnit
  latitude: float
  longitude: float

  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the LocationModel 
    instance.

    Returns
    --------------
    str: 
      The string representation of the LocationModel instance.
    """
    return (
      f"---- Location Model -------------------------\n"
      f"city_name:        {self.city_name},\n"
      f"icao_code:        {self.icao_code},\n"
      f"timezone:         {self.timezone},\n"
      f"temperature_unit: {self.temperature_unit.api_value},\n"
      f"latitude:         {self.latitude},\n"
      f"longitude:        {self.longitude}\n"
    )
