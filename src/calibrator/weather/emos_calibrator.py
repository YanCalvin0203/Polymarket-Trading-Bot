from datetime import datetime, timezone
from pandas import DataFrame
from numpy import array, ndarray, sqrt, any, isinf, isnan
from scipy.optimize import minimize
from scipy.stats import skewnorm
from src.enums.weather import TemperatureUnit
from src.models.weather import WeatherCalibrationParamsModel
from src.settings import settings


class WeatherEMOSCalibrator:
  """
  This class implements the Ensemble Model Output Statistics (EMOS) calibrator
  to calibrate the model.
  """

  # ---- Public API ----------------------------------

  def calibrate_model_for_city(
    self, 
    icao_code: str,
    lead_days: int,
    temperature_unit: TemperatureUnit,
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

    temperature_unit (TemperatureUnit):
      The unit of temperature for the calibration data.

    calibration_data (DataFrame):
      The DataFrame containing the calibration data for the city.

    Returns
    ----------------
    WeatherCalibrationParamsModel:
      The calibrated EMOS model parameters for the city.
    """
    init_a = settings.WEATHER_CALIBRATOR_SETTINGS.INIT_A
    init_b = settings.WEATHER_CALIBRATOR_SETTINGS.INIT_B
    init_d = settings.WEATHER_CALIBRATOR_SETTINGS.INIT_D

    bounds_a = settings.WEATHER_CALIBRATOR_SETTINGS.BOUNDS_A
    bounds_b = settings.WEATHER_CALIBRATOR_SETTINGS.BOUNDS_B
    bounds_d = settings.WEATHER_CALIBRATOR_SETTINGS.BOUNDS_D

    if temperature_unit.api_value == TemperatureUnit.FAHRENHEIT.api_value:
      init_c = settings.WEATHER_CALIBRATOR_SETTINGS.INIT_C_FAHRENHEIT
      bounds_c = settings.WEATHER_CALIBRATOR_SETTINGS.BOUNDS_C_FAHRENHEIT

    else:
      init_c = settings.WEATHER_CALIBRATOR_SETTINGS.INIT_C_CELSIUS
      bounds_c = settings.WEATHER_CALIBRATOR_SETTINGS.BOUNDS_C_CELSIUS

    # Return initial parameters if insufficient data for calibration
    if len(calibration_data) < settings.WEATHER_CALIBRATOR_SETTINGS.CALIBRATION_MIN_SAMPLES:
      return WeatherCalibrationParamsModel(
        icao_code=icao_code,
        lead_days=lead_days,
        last_updated=datetime.now(tz=timezone.utc),
        a=init_a, 
        b=init_b, 
        c=init_c, 
        d=init_d
      )

    # Extract data from raw arrays
    ensemble_mean = calibration_data["ensemble_mean"].values
    ensemble_stdev = calibration_data["ensemble_stdev"].values
    ensemble_alpha = calibration_data["ensemble_alpha"].values
    actual_max = calibration_data["actual_max"].values

    # Initial guess
    initial_guess = array([init_a, init_b, init_c, init_d])

    # Set strict physical bounds
    bounds = [bounds_a, bounds_b, bounds_c, bounds_d]

    # Run the Scipy Solver
    result = minimize(
      fun=self._emos_skew_normal_neg_log_likelihood,
      x0=initial_guess,
      args=(ensemble_mean, ensemble_stdev, ensemble_alpha, actual_max),
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

  def _emos_skew_normal_neg_log_likelihood(
    self, 
    params: ndarray, 
    ens_means: ndarray, 
    ens_stdevs: ndarray, 
    ensemble_alpha: ndarray, 
    actuals: ndarray
  ) -> float:
    """
    Calculates the Negative Log-Likelihood for a Skew Normal EMOS model.

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

    ensemble_alpha (ndarray):
      The array of ensemble skewness parameters.

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

    # Calculate Skew Normal Negative Log-Likelihood
    sigma = sqrt(variance)
    log_likelihood = skewnorm.logpdf(actuals, a=ensemble_alpha, loc=mu, scale=sigma)

    # Handle cases where the likelihood is extremely low or invalid
    if any(isinf(log_likelihood)) or any(isnan(log_likelihood)):
      return 1e10
    
    return float(-log_likelihood.sum())
