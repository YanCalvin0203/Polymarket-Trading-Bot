from enum import Enum


class TemperatureQualifier(Enum):
  """
  This enum defines the possible qualifiers for temperature buckets.
  """
  OR_BELOW = "or below"
  OR_HIGHER = "or higher"
