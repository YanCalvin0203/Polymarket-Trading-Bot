from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class WeatherCalibrationParamsModel:
  """
  This dataclass encapsulates the parameters of the calibrated EMOS 
  model for a specific city.
  """
  icao_code: str
  lead_days: int
  last_updated: datetime
  a: float
  b: float
  c: float
  d: float

  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the WeatherCalibrationParamsModel
    instance.

    Returns
    --------------
    str: 
      The string representation of the WeatherCalibrationParamsModel instance.
    """
    return (
      f"---- Weather Calibration Params Model -----------------\n"
      f"icao_code:    {self.icao_code}\n"
      f"lead_days:    {self.lead_days}\n"
      f"last_updated: {self.last_updated}\n"
      f"a:            {self.a},\n"
      f"b:            {self.b},\n"
      f"c:            {self.c},\n"
      f"d:            {self.d}\n"
    ) 
