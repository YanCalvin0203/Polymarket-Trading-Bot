from dataclasses import dataclass
from datetime import datetime
from src.models.weather.components import LocationModel


@dataclass(slots=True)
class WeatherManifestModel:
  location: LocationModel
  resolution_time: datetime
  observation_max: float

  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the WeatherManifestModel 
    instance.

    Returns
    --------------
    str: 
      The string representation of the WeatherManifestModel instance.
    """
    return (
      f"---- Weather Manifest Model -------------------\n"
      f"city_name:        {self.location.city_name},\n"
      f"icao_code:        {self.location.icao_code},\n"
      f"timezone:         {self.location.timezone},\n"
      f"temperature_unit: {self.location.temperature_unit.api_value},\n"
      f"latitude:         {self.location.latitude},\n"
      f"longitude:        {self.location.longitude}\n"
      f"resolution_time:  {self.resolution_time}\n"
      f"observation_max:  {self.observation_max}\n"
    )
