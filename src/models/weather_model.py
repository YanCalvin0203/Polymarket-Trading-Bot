from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class PricingModel:
  best_yes_ask: float
  best_no_ask: float
  best_yes_bid: float
  best_no_bid: float


  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the PricingModel 
    instance.

    Returns
    --------------
    str: The string representation of the PricingModel instance.
    """
    return (
      f"---- Pricing Model -------------------------\n"
      f"best_yes_ask:  {self.best_yes_ask},\n"
      f"best_no_ask:  {self.best_no_ask},\n"
      f"best_yes_bid:  {self.best_yes_bid},\n"
      f"best_no_bid:  {self.best_no_bid}\n"
    )


@dataclass(frozen=True, slots=True)
class LocationModel:
  city_name: str
  icao_code: str
  timezone: str
  latitude: float
  longitude: float


  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the LocationModel 
    instance.

    Returns
    --------------
    str: The string representation of the LocationModel instance.
    """
    return (
      f"---- Location Model -------------------------\n"
      f"city_name:  {self.city_name},\n"
      f"icao_code:  {self.icao_code},\n"
      f"timezone:   {self.timezone},\n"
      f"latitude:   {self.latitude},\n"
      f"longitude:  {self.longitude}\n"
    )


@dataclass(slots=True)
class WeatherEventModel:
  # ---- Base attributes ---------------------------------

  event_id: str
  markets: dict[str, 'WeatherMarketModel']


  # ---- Weather specific attributes ---------------------

  location: LocationModel
  temperature_unit: str
  resolution_time: datetime
  resolution_source: str


  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the WeatherEventModel 
    instance.

    Returns
    --------------
    str: The string representation of the WeatherEventModel instance.
    """
    return (
      f"---- Weather Event Model --------------------------\n"
      f"event_id:          {self.event_id},\n"
      f"total markets:     {len(self.markets)},\n"
      f"city_name:         {self.location.city_name},\n"
      f"icao_code:         {self.location.icao_code},\n"
      f"timezone:          {self.location.timezone},\n"
      f"latitude:          {self.location.latitude},\n"
      f"longitude:         {self.location.longitude},\n"
      f"temperature_unit:  {self.temperature_unit},\n"
      f"resolution_time:   {self.resolution_time},\n"
      f"resolution_source: {self.resolution_source})\n"
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
  probability: float


  # ---- Raw market data ---------------------------------

  market_data: dict[str, Any]


  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the WeatherMarketModel 
    instance.

    Returns
    --------------
    str: The string representation of the WeatherMarketModel instance.
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
      f"probability:       {self.probability},\n"
    )
