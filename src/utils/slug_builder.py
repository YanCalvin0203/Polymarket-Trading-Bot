from datetime import UTC, datetime, timedelta
from src.core.settings import settings


def weather_slug_builder() -> list[str]:
  """
  This function returns a list of slugs for relevant weather
  events on Polymarket.

  Returns:
  ---------------
  list[str]: A list of slugs for the specified cities and time range.
  """
  slugs = []
  today = datetime.now(tz=UTC).date()

  cities = settings.SLUG_BUILDER_CONFIG.CITIES
  time_range = settings.SLUG_BUILDER_CONFIG.TIME_RANGE

  for city in cities:
    for i in range(time_range):
      date = today + timedelta(days=i)
      city_slug = city.lower()
      date_slug = date.strftime("%B-%d-%Y").lower()
      slug = f"highest-temperature-in-{city_slug}-on-{date_slug}"
      slugs.append(slug)

  return slugs
