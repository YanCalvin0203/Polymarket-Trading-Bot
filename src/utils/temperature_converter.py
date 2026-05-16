def to_farenheit(celsius: float) -> float:
  """
  This function converts a temperature from Celsius to 
  Farenheit.

  Parameters
  --------------
  celsius (float): 
    The temperature in Celsius.

  Returns
  --------------
  float: 
    The temperature in Farenheit.
  """
  return (celsius * 9/5) + 32


def to_celsius(farenheit: float) -> float:
  """
  This function converts a temperature from Farenheit to 
  Celsius.

  Parameters
  --------------
  farenheit (float): 
    The temperature in Farenheit.

  Returns
  --------------
  float: 
    The temperature in Celsius.
  """
  return (farenheit - 32) * 5/9
