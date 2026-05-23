from datetime import datetime, timezone
from pandas import DataFrame
from numpy import array, ndarray, sqrt
from scipy.optimize import minimize
from scipy.stats import norm
from src.models.weather import WeatherCalibrationParamsModel


class WeatherEMOSCalibrator:
  """
  This class implements the Ensemble Model Output Statistics (EMOS) calibrator
  to calibrate the model.
  """

  def __init__(self) -> None:
    """
    This function initializes the WeatherEMOSCalibrator class.
    """
    pass


  # ---- Public API ----------------------------------

  def calibrate_model_for_city(
    self, 
    icao_code: str,
    lead_days: int,
    calibration_data: DataFrame
  ) -> WeatherCalibrationParamsModel:
    """
    This function calibrates the EMOS model for a specific city using the provided 
    calibration data.

    Parameters
    ----------------    
    icao_code (str):
      The ICAO code of the city for which the model is being calibrated.

    lead_days (int):
      The lead time in days for which the model is being calibrated.

    calibration_data (DataFrame):
      The DataFrame containing the calibration data for the city.

    Returns
    ----------------
    WeatherCalibrationParamsModel:
      The calibrated EMOS model parameters for the city.
    """
    init_a, init_b, init_c, init_d = 0.0, 1.0, 0.01, 1.0

    # Extract raw arrays and compute stddev from variance
    ensemble_mean = calibration_data["ensemble_mean"].values
    ensemble_stdev = calibration_data["ensemble_stdev"].values
    historical_max = calibration_data["actual_max"].values

    # Initial guess: [a=0 (no bias), b=1 (scale 1:1), c=0.01 (baseline var), d=1 (scale 1:1)]
    initial_guess = array([init_a, init_b, init_c, init_d])

    # Set strict physical bounds
    bounds = [
      (None, None),   # 'a' can be any additive shift (positive or negative)
      (0.1, 3.0),     # 'b' multiplicative mean scale constraint
      (0.05, None),   # 'c' baseline variance floor (prevents division-by-zero risks)
      (0.05, None)    # 'd' variance scaling multiplier floor
    ]

    # Run the Scipy Solver
    result = minimize(
      fun=self._emos_gaussian_neg_log_likelihood,
      x0=initial_guess,
      args=(ensemble_mean, ensemble_stdev, historical_max),
      bounds=bounds,
      method="L-BFGS-B"
    )

    if not result.success:
      return WeatherCalibrationParamsModel(
        icao_code=icao_code,
        lead_days=lead_days,
        last_updated=datetime.now(tz=timezone.utc),
        a=init_a, 
        b=init_b, 
        c=init_c, 
        d=init_d
      )

    a, b, c, d = result.x
    return WeatherCalibrationParamsModel(
      icao_code=icao_code,
      lead_days=lead_days,
      last_updated=datetime.now(tz=timezone.utc),
      a=float(a),
      b=float(b),
      c=float(c),
      d=float(d)
    )


  # ---- Internal Helpers ----------------------------

  def _emos_gaussian_neg_log_likelihood(
    self, 
    params: ndarray, 
    ens_means: ndarray, 
    ens_stdevs: ndarray, 
    actuals: ndarray
  ) -> float:
    """
    Calculates the Negative Log-Likelihood for a Gaussian EMOS model.

    Parameters
    ----------------
    params (ndarray):
      The EMOS parameters [a, b, c, d] where:
        a: additive bias correction
        b: multiplicative bias correction on the ensemble mean
        c: intercept for variance (must be > 0)
        d: multiplicative factor for ensemble variance (must be > 0)

    ens_means (ndarray):
      The array of ensemble mean forecasts.

    ens_stdevs (ndarray):
      The array of ensemble standard deviations.

    actuals (ndarray):
      The array of actual observed values.

    Returns
    ----------------
    float:
      The negative log-likelihood of the observed data under the EMOS model with 
      the given parameters
    """
    a, b, c, d = params
    
    # EMOS Linear Mean Transformation
    mu = a + b * ens_means
    
    # EMOS Variance Transformation
    ens_variance = ens_stdevs ** 2
    variance = c + d * ens_variance

    # Calculate Gaussian Negative Log-Likelihood
    sigma = sqrt(variance)
    log_likelihood = norm.logpdf(actuals, loc=mu, scale=sigma)
    
    return float(-log_likelihood.sum())
