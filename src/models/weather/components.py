from dataclasses import dataclass
from datetime import datetime
from src.enums.weather.units import TemperatureUnit



@dataclass(slots=True)
class WeatherDataCollectionActualMaxModel:
  actual_max: float
  resolution_date: datetime
  created_at: datetime

  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the
    WeatherDataCollectionActualMaxModel instance.

    Returns
    --------------
    str: 
      The string representation of the WeatherDataCollectionActualMaxModel 
      instance.
    """
    return (
      f"---- Weather Data Collection Actual Max Model ----------------\n"
      f"actual_max:       {self.actual_max},\n"
      f"resolution_date:  {self.resolution_date},\n"
      f"created_at:       {self.created_at}\n"
    )
  

@dataclass(slots=True)
class WeatherDataCollectionForecastModel:
  lead_days: int
  forecast_mean: float
  forecast_stdev: float
  resolution_date: datetime
  created_at: datetime

  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the
    WeatherDataCollectionForecastModel instance.

    Returns
    --------------
    str: 
      The string representation of the WeatherDataCollectionForecastModel 
      instance.
    """
    return (
      f"---- Weather Data Collection Forecast Model ----------------\n"
      f"lead_days:       {self.lead_days},\n"
      f"forecast_mean:   {self.forecast_mean},\n"
      f"forecast_stdev:  {self.forecast_stdev},\n"
      f"resolution_date: {self.resolution_date},\n"
      f"created_at:      {self.created_at}\n"
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
      f"forecast_mean:   {self.forecast_mean},\n"
      f"forecast_stdev:  {self.forecast_stdev},\n"
      f"last_updated:    {self.last_updated}\n"
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
  iata_code: str
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
      f"iata_code:        {self.iata_code},\n"
      f"timezone:         {self.timezone},\n"
      f"temperature_unit: {self.temperature_unit.api_value},\n"
      f"latitude:         {self.latitude},\n"
      f"longitude:        {self.longitude}\n"
    )
