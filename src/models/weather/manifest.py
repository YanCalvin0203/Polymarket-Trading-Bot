from dataclasses import dataclass
from datetime import datetime
from src.core.enums.weather.unit import TemperatureUnit
from src.models.weather.components import (
  LocationModel
)


@dataclass(slots=True)
class WeatherManifestModel:
  location: LocationModel
  temperature_unit: TemperatureUnit
  resolution_time: datetime

  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the WeatherManifestModel 
    instance.

    Returns
    --------------
    str: The string representation of the WeatherManifestModel instance.
    """
    return (
      f"---- Weather Manifest Model -------------------\n"
      f"city_name:        {self.location.city_name},\n"
      f"icao_code:        {self.location.icao_code},\n"
      f"timezone:         {self.location.timezone},\n"
      f"latitude:         {self.location.latitude},\n"
      f"longitude:        {self.location.longitude}\n"
      f"temperature_unit: {self.temperature_unit.api_value},\n"
      f"resolution_time:  {self.resolution_time}\n"
    )
