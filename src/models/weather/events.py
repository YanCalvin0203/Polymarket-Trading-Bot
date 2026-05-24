from dataclasses import dataclass
from datetime import datetime
from typing import Any
from src.models.common import PricingModel
from src.enums.weather.units import TemperatureUnit
from src.models.weather.components import (
  WeatherForecastModel,
  WeatherObservationModel,
  LocationModel,
)


@dataclass(slots=True)
class WeatherEventModel:
  # ---- Base attributes ---------------------------------
  event_id: str
  markets: dict[str, 'WeatherMarketModel']

  # ---- Weather specific attributes ---------------------
  location: LocationModel
  resolution_time: datetime
  resolution_source: str

  # ---- Weather Prediction attributes -------------------
  forecast: WeatherForecastModel
  observation: WeatherObservationModel

  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the WeatherEventModel
    instance.

    Returns
    --------------
    str: 
      The string representation of the WeatherEventModel instance.
    """
    return (
      f"---- Weather Event Model --------------------------\n"
      f"event_id:             {self.event_id},\n"
      f"total markets:        {len(self.markets)},\n"
      f"city_name:            {self.location.city_name},\n"
      f"icao_code:            {self.location.icao_code},\n"
      f"iata_code:            {self.location.iata_code},\n"
      f"timezone:             {self.location.timezone},\n"
      f"temperature_unit:     {self.location.temperature_unit.api_value},\n"
      f"latitude:             {self.location.latitude},\n"
      f"longitude:            {self.location.longitude},\n"
      f"resolution_time:      {self.resolution_time},\n"
      f"resolution_source:    {self.resolution_source})\n"
      f"forecast_mean:        {self.forecast.forecast_mean},\n"
      f"forecast_stdev:       {self.forecast.forecast_stdev},\n"
      f"forecast_alpha:       {self.forecast.forecast_alpha},\n"
      f"last_updated:         {self.forecast.last_updated}\n"
      f"observation_current:  {self.observation.observation_current},\n"
      f"observation_max:      {self.observation.observation_max},\n"
      f"last_updated:         {self.observation.last_updated}\n"
    )


@dataclass(slots=True)
class WeatherMarketModel:
  # ---- Base attributes ---------------------------------
  parent_event_id: str
  market_id: str
  market_slug: str
  market_name: str
  yes_token_id: str
  no_token_id: str
  prices: PricingModel

  # ---- Weather specific attributes ---------------------
  bucket_range: tuple[float, float]

  # ---- Raw market data ---------------------------------
  market_data: dict[str, Any]


  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the WeatherMarketModel 
    instance.

    Returns
    --------------
    str: 
      The string representation of the WeatherMarketModel instance.
    """
    return (
      f"---- Weather Market Model -------------------------\n"
      f"parent_event_id:   {self.parent_event_id},\n"
      f"market_id:         {self.market_id},\n"
      f"market_slug:       {self.market_slug},\n"
      f"market_name:       {self.market_name},\n"
      f"yes_token_id:      {self.yes_token_id},\n"
      f"no_token_id:       {self.no_token_id},\n"
      f"best_yes_ask:      {self.prices.best_yes_ask},\n"
      f"best_no_ask:       {self.prices.best_no_ask},\n"
      f"best_yes_bid:      {self.prices.best_yes_bid},\n"
      f"best_no_bid:       {self.prices.best_no_bid}\n"
      f"bucket_range:      {self.bucket_range},\n"
    )
