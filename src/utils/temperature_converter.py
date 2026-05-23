def to_fahrenheit(celsius: float) -> float:
  """
  This function converts a temperature from Celsius to 
  Fahrenheit.

  Parameters
  --------------
  celsius (float): 
    The temperature in Celsius.

  Returns
  --------------
  float: 
    The temperature in Fahrenheit.
  """
  return (celsius * 9/5) + 32


def to_celsius(fahrenheit: float) -> float:
  """
  This function converts a temperature from Fahrenheit to 
  Celsius.

  Parameters
  --------------
  fahrenheit (float): 
    The temperature in Fahrenheit.

  Returns
  --------------
  float: 
    The temperature in Celsius.
  """
  return (fahrenheit - 32) * 5/9
