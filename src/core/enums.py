from enum import Enum

class TemperatureUnit(Enum):
  CELSIUS = "C"
  FAHRENHEIT = "F"

  @property
  def api_value(self) -> str:
    """
    This property returns the corresponding value for the TemperatureUnit
    enum.
    """
    mapping = {
      TemperatureUnit.CELSIUS: "celsius",
      TemperatureUnit.FAHRENHEIT: "fahrenheit"
    }
    return mapping[self]
