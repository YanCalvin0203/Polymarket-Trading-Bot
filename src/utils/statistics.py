from numpy import sign, sqrt, pi


def convert_skew_to_alpha(sample_skew: float) -> float:
  """
  Converts sample skewness to the skew-normal shape parameter
  using the method-of-moments estimator.

  Parameters
  --------------
  sample_skew (float): 
    The sample skewness of the data.

  Returns
  --------------
  float: 
    The skew-normal shape parameter.
  """
  if abs(sample_skew) < 1e-6:
    return 0.0

  max_skew = 0.9953
  
  clamped_skew = max(-max_skew, min(max_skew, sample_skew))
  abs_skew_23 = abs(clamped_skew) ** (2 / 3)
  skew_normal_constant = ((4 - pi) / 2) ** (2 / 3)

  delta = sqrt((pi / 2) * (abs_skew_23 / (abs_skew_23 + skew_normal_constant)))
  inversion = sign(clamped_skew) * (delta / sqrt(1 - delta ** 2))
  
  return float(inversion)
