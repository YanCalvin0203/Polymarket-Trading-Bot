import re
import json
import airportsdata

from typing import Any
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pandas import Timestamp
from src.models.common import PricingModel
from src.enums.weather import (
  TemperatureUnit,
  TemperatureQualifier,
)
from src.models.weather import (
  LocationModel,
  WeatherEventModel,
  WeatherMarketModel,
  WeatherForecastModel,
  WeatherObservationModel,
  WeatherManifestModel,
)

# ---- Regex Patterns ----------------------------------

CITY_NAME_REGEX = re.compile(r"in\s+(.*?)\s+(?:be|reach|on)", re.IGNORECASE)
STATION_CODE_REGEX = re.compile(r"/([A-Z]{4})$", re.IGNORECASE)
TEMPERATURE_PATTERN = re.compile(
  r"(?P<first_temp>-?\d+)"                      # First temperature
  r"(?:\s*-\s*(?P<second_temp>-?\d+))?"         # Optional second temperature (range)
  r"\s*°?\s*(?P<unit>[CF])"                     # Required Unit (C or F)
  r"\s*(?P<qualifier>" + "|".join(qualifier.value for qualifier in TemperatureQualifier) + ")?",
  re.IGNORECASE
)
TEMPERATURE_UNIT_REGEX = re.compile(r"°?\s*(?P<unit>[CF])", re.IGNORECASE)


# ---- Main Parser Class ----------------------------------

class WeatherParser:
  """
  This class implements a parse raw Polymarket market data into structured
  data.
  """

  def __init__(self) -> None:
    """
    This function initializes the WeatherParser class.
    """
    self._airport_dict = airportsdata.load("ICAO")

  
  # ---- Public API ----------------------------------

  def parse_instruments(
    self, 
    instruments: list[dict[str, Any]]
  ) -> dict[str, WeatherEventModel]:
    """
    This function parses raw instrument data into a dictionary of structured event data.

    Parameters
    --------------
    instruments (list[dict[str, Any]]): 
      The list of raw instrument data retrieved from Polymarket.

    Returns
    --------------
    dict[str, WeatherEventModel]: 
      The parsed and structured dictionary of instrument data.
    """
    events = {}
    for instrument in instruments:
      instrument_data: dict[str, Any] = instrument.info
      event_id = instrument_data.get("neg_risk_market_id", None)
      if event_id is None:
        continue

      event_model = events.get(event_id, None)
      if event_model is None:
        event_model = self._parse_single_event(instrument_data)
        if event_model is None:
          continue

        events[event_id] = event_model

      market_model = self._parse_single_market(instrument_data)
      if market_model is None:
        continue

      event_model.markets[market_model.market_id] = market_model

    return events

  def parse_manifests(
    self, 
    events_dict: dict[str, WeatherEventModel]
  ) -> dict[str, WeatherManifestModel]:
    """
    This function parses event models into a dictionary of structured manifest data.

    Parameters
    --------------
    events_dict (dict[str, WeatherEventModel]): 
      The dictionary of event models to parse manifests for.

    Returns
    --------------
    dict[str, WeatherManifestModel]: 
      The parsed and structured dictionary of manifest data.
    """
    manifests = {}
    for event_id, event_model in events_dict.items():
      manifest_model = self._parse_single_manifest(event_model)
      if manifest_model is None:
        continue 

      manifests[event_id] = manifest_model

    return manifests
  
  def parse_cities(
    self,
    events_dict: dict[str, WeatherEventModel]
  ) -> dict[str, LocationModel]:
    """
    This function parses event models into a dictionary of structured city data.

    Parameters
    --------------
    events_dict (dict[str, WeatherEventModel]): 
      The dictionary of event models to parse city data for.

    Returns
    --------------
    dict[str, LocationModel]: 
      The parsed and structured dictionary of city data.
    """
    cities = {}
    for event_model in events_dict.values():
      icao_code = event_model.location.icao_code
      if cities.get(icao_code, None) is not None:
        continue

      cities[icao_code] = event_model.location

    return cities
  
  # ---- Internal Helpers ----------------------------

  def _parse_single_event(
    self, 
    instrument_data: dict[str, Any]
  ) -> WeatherEventModel | None:
    """
    This function parses a single instrument data into a structured event format.

    Parameters
    --------------
    instrument_data (dict[str, Any]): 
      The instrument data.

    Returns
    --------------
    WeatherEventModel | None: 
      The parsed and structured event data, or None if parsing fails.
    """
    raw_instrument: dict[str, Any] = instrument_data.get("_gamma_original", None)
    if raw_instrument is None:
      return None
    
    latitude, longitude = self._parse_coordinates(raw_instrument)
    location_model = LocationModel(
      city_name=self._parse_city_name(raw_instrument),
      icao_code=self._parse_icao_code(raw_instrument),
      iata_code=self._parse_iata_code(raw_instrument),
      timezone=self._parse_timezone(raw_instrument),
      temperature_unit=self._parse_temperature_unit(raw_instrument),
      latitude=latitude,
      longitude=longitude
    )

    forecast_model = WeatherForecastModel(
      forecast_mean=0.0,
      forecast_stdev=0.0,
      forecast_alpha=0.0,
      last_updated=Timestamp.now(tz=timezone.utc)
    )
    observation_model = WeatherObservationModel(
      observation_current=0.0,
      observation_max=0.0,
      last_updated=Timestamp.now(tz=timezone.utc)
    )

    event_model = WeatherEventModel(
      # ---- Base attributes ---------------------------------
      event_id=instrument_data.get("neg_risk_market_id", ""),
      markets={},

      # ---- Weather specific attributes ---------------------
      location=location_model,
      resolution_time=self._parse_resolution_time(raw_instrument),
      resolution_source=raw_instrument.get("resolutionSource", None),
      forecast=forecast_model,
      observation=observation_model
    )

    if not self._is_event_valid(event_model):
      return None

    return event_model

  def _parse_single_market(
    self, 
    instrument_data: dict[str, Any]
  ) -> WeatherMarketModel | None:
    """
    This function parses a single instrument data into a structured market format.

    Parameters
    --------------
    instrument_data (dict[str, Any]): 
      The instrument data.

    Returns
    --------------
    WeatherMarketModel | None: 
      The parsed and structured market data, or None if parsing fails.
    """
    raw_instrument: dict[str, Any] = instrument_data.get("_gamma_original", None)
    if raw_instrument is None:
      return None
    
    yes_token_id, no_token_id = self._parse_token_ids(raw_instrument)

    pricing_model = PricingModel(
      best_yes_ask=0.0,
      best_no_ask=0.0,
      best_yes_bid=0.0,
      best_no_bid=0.0
    )

    market_model = WeatherMarketModel(
      # ---- Base attributes ---------------------------------
      parent_event_id=instrument_data.get("neg_risk_market_id", ""),
      market_id=raw_instrument.get("id", ""),
      market_slug=raw_instrument.get("slug", ""),
      market_name=raw_instrument.get("question", ""),
      yes_token_id=yes_token_id,
      no_token_id=no_token_id,
      prices=pricing_model,

      # ---- Weather specific attributes ---------------------
      bucket_range=self._parse_bucket_range(raw_instrument),

      # ---- Raw market data --------------------------------
      market_data=raw_instrument
    )

    if not self._is_market_valid(market_model):
      return None
    
    return market_model
  
  def _parse_single_manifest(
    self, 
    event_model: WeatherEventModel
  ) -> WeatherManifestModel | None:
    """
    This function parses a single event model into a structured manifest format.

    Parameters
    --------------
    event_model (WeatherEventModel): 
      The event model.

    Returns
    --------------
    WeatherManifestModel | None: 
      The parsed and structured manifest data, or None if parsing fails.
    """
    observation_max = None
    if event_model.observation is not None:
      observation_max = event_model.observation.observation_max
      
    manifest_model = WeatherManifestModel(
      location=event_model.location,
      resolution_time=event_model.resolution_time,
      observation_max=observation_max
    )

    if not self.is_manifest_valid(manifest_model):
      return None

    return manifest_model
  
  def _is_location_valid(self, location_model: LocationModel) -> bool:
    """
    This function checks if a parsed location model is valid.

    Parameters
    --------------
    location_model (LocationModel): 
      The parsed location model to validate.

    Returns
    --------------
    bool: 
      True if the location model is valid, False otherwise.
    """
    if location_model.city_name == "":
      return False
    
    if location_model.icao_code == "" or location_model.iata_code == "":
      return False
    
    if location_model.timezone == "" or location_model.temperature_unit is None:
      return False
    
    if location_model.latitude is None or location_model.longitude is None:
      return False

    return True
  
  def _is_event_valid(self, event_model: WeatherEventModel) -> bool:
    """
    This function checks if a parsed event model is valid to be traded.

    Parameters
    --------------
    event_model (WeatherEventModel): 
      The parsed event model to validate.

    Returns
    --------------
    bool: 
      True if the event model is valid, False otherwise.
    """
    if event_model.event_id == "":
      return False
    
    if event_model.resolution_time is None or event_model.resolution_source is None:
      return False
    
    if not self._is_location_valid(event_model.location):
      return False

    return True
  
  def _is_market_valid(self, market_model: WeatherMarketModel) -> bool:
    """
    This function checks if a parsed market model is valid to be traded.

    Parameters
    --------------
    market_model (WeatherMarketModel): 
      The parsed market model to validate.

    Returns
    --------------
    bool: 
      True if the market model is valid, False otherwise.
    """
    if market_model.parent_event_id == "" or  market_model.bucket_range == (None, None):
      return False
    
    if market_model.yes_token_id is None or market_model.no_token_id is None:
      return False

    return True
  
  def is_manifest_valid(self, manifest_model: WeatherManifestModel) -> bool:
    """
    This function checks if a parsed manifest model is valid to be used.

    Parameters
    --------------
    manifest_model (WeatherManifestModel): 
      The parsed manifest model to validate.

    Returns
    --------------
    bool: 
      True if the manifest model is valid, False otherwise.
    """
    if manifest_model.resolution_time is None:
      return False
    
    if not self._is_location_valid(manifest_model.location):
      return False

    return True
  
  def _parse_city_name(self, raw_instrument: dict[str, Any]) -> str:
    """
    This function parses the city name from the raw instrument data.

    Parameters
    --------------
    raw_instrument (dict[str, Any]): 
      The raw instrument data.

    Returns
    --------------
    str: 
      The parsed city name.
    """
    market_question = raw_instrument.get("question", "")
    if market_question == "":
      return ""
    
    city_name = CITY_NAME_REGEX.search(market_question)
    if city_name is None:
      return ""
    
    return city_name.group(1)
  
  def _parse_icao_code(self, raw_instrument: dict[str, Any]) -> str:
    """
    This function parses the ICAO code from the raw instrument data.

    Parameters
    --------------
    raw_instrument (dict[str, Any]): 
      The raw instrument data.

    Returns
    --------------
    str: 
      The parsed ICAO code.
    """
    resolution_source = raw_instrument.get("resolutionSource", "")
    if resolution_source == "":
      return ""
    
    station_code = STATION_CODE_REGEX.search(resolution_source)
    if station_code is None:
      return ""
    
    return station_code.group(1)
  
  def _parse_iata_code(self, raw_instrument: dict[str, Any]) -> str:
    """
    This function parses the IATA code from the raw instrument data.

    Parameters
    --------------
    raw_instrument (dict[str, Any]): 
      The raw instrument data.

    Returns
    --------------
    str: 
      The parsed IATA code.
    """
    icao_code = self._parse_icao_code(raw_instrument)
    if icao_code == "":
      return ""
    
    city_info = self._airport_dict.get(icao_code, None)
    if city_info is None:
      return ""
    
    iata_code = city_info.get("iata", "")
    return iata_code
  
  def _parse_coordinates(
    self, 
    raw_instrument: dict[str, Any]
  ) -> tuple[float | None, float | None]:
    """
    This function parses the coordinates of the city from the raw instrument data.

    Parameters
    --------------
    raw_instrument (dict[str, Any]): 
      The raw instrument data.

    Returns
    --------------
    tuple[float | None, float | None]: 
      The parsed latitude and longitude of the city.
    """
    icao_code = self._parse_icao_code(raw_instrument)
    if icao_code == "":
      return (None, None)
    
    city_info = self._airport_dict.get(icao_code, None)
    if city_info is None:
      return (None, None)
    
    latitude = city_info.get("lat", None)
    longitude = city_info.get("lon", None)

    return (latitude, longitude)

  def _parse_timezone(self, raw_instrument: dict[str, Any]) -> str:
    """
    This function parses the timezone of the city from the raw instrument data.

    Parameters
    --------------
    raw_instrument (dict[str, Any]): 
      The raw instrument data.

    Returns
    --------------
    str: 
      The parsed timezone of the city.
    """
    icao_code = self._parse_icao_code(raw_instrument)
    if icao_code == "":
      return ""
    
    city_info = self._airport_dict.get(icao_code, None)
    if city_info is None:
      return ""
    
    timezone = city_info.get("tz", None)
    return timezone

  def _parse_resolution_time(self, raw_instrument: dict[str, Any]) -> datetime | None:
    """
    This function parses the resolution time from the raw instrument data.

    Parameters
    --------------
    raw_instrument (dict[str, Any]): 
      The raw instrument data.

    Returns
    --------------
    datetime | None: 
      The parsed resolution time or None if not found.
    """
    resolution_date_iso = raw_instrument.get("endDateIso", None)
    if resolution_date_iso is None:
      return None

    icao_code = self._parse_icao_code(raw_instrument)
    if icao_code == "":
      return None
    
    city_info = self._airport_dict.get(icao_code, None)
    if city_info is None:
      return None
    
    base_date = datetime.fromisoformat(resolution_date_iso)
    city_timezone  = city_info.get("tz", None)
    if city_timezone is None: 
      return None

    resolution_time = datetime.combine(
      base_date.date(), 
      datetime.max.time(), 
      tzinfo=ZoneInfo(city_timezone)
    )

    return resolution_time
  
  def _parse_bucket_range(
    self, 
    raw_instrument: dict[str, Any]
  ) -> tuple[float, float]:
    """
    This function parses the bucket range from the raw instrument data.

    Parameters
    --------------
    raw_instrument (dict[str, Any]): 
      The raw instrument data.

    Returns
    --------------
    tuple[float, float]: 
      The parsed bucket range.
    """
    temperature_str = raw_instrument.get("groupItemTitle", "")
    if temperature_str == "":
      return (None, None)
    
    temperature_bucket = TEMPERATURE_PATTERN.search(temperature_str)
    if temperature_bucket is None:
      return (None, None)
    
    first_num = temperature_bucket.group("first_temp")
    second_num = temperature_bucket.group("second_temp")
    qualifier = temperature_bucket.group("qualifier")

    first_temp = float(first_num) if first_num is not None else None
    second_temp = float(second_num) if second_num is not None else None
    qualifier = qualifier.lower() if qualifier is not None else None

    infinity = float("inf")
    negative_infinity = float("-inf")

    lower_bound = first_temp - 0.5
    upper_bound = (second_temp + 0.5) if second_temp is not None else (first_temp + 0.5)

    if qualifier == TemperatureQualifier.OR_BELOW.value:
      lower_bound = negative_infinity

    elif qualifier == TemperatureQualifier.OR_HIGHER.value:
      upper_bound = infinity

    return (lower_bound, upper_bound)

  def _parse_temperature_unit(
    self, 
    raw_instrument: dict[str, Any]
  ) -> TemperatureUnit | None:
    """
    This function parses the temperature unit from the raw instrument data.

    Parameters
    --------------
    raw_instrument (dict[str, Any]): 
      The raw instrument data.

    Returns
    --------------
    TemperatureUnit | None: 
      The parsed temperature unit enum or None if not found.
    """
    temperature_str = raw_instrument.get("groupItemTitle", "")
    if temperature_str == "":
      return None
    
    unit_match = TEMPERATURE_UNIT_REGEX.search(temperature_str)
    if unit_match is None:
      return None
    
    temperature_unit = unit_match.group("unit").upper()
    try:
      return TemperatureUnit(temperature_unit)
    
    except ValueError:
      return None
  
  def _parse_token_ids(
    self, 
    raw_instrument: dict[str, Any]
  ) -> tuple[int | None, int | None]:
    """
    This function parses the token IDs from the raw instrument data.

    Parameters
    --------------
    raw_instrument (dict[str, Any]): 
      The raw instrument data.

    Returns
    --------------
    tuple[int | None, int | None]: 
      The parsed yes and no token IDs.
    """
    raw_clob_token_ids = raw_instrument.get("clobTokenIds", None)
    if raw_clob_token_ids is None:
      return (None, None)

    try:
      clob_token_ids = json.loads(raw_clob_token_ids)
      if clob_token_ids is None or len(clob_token_ids) != 2:
        return (None, None)
      
      yes_token_id = int(clob_token_ids[0])
      no_token_id = int(clob_token_ids[1])
      return (yes_token_id, no_token_id)
    
    except Exception:
      return (None, None)
    