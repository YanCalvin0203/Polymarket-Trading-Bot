from numpy import sqrt
from scipy.stats import norm
from datetime import timezone
from pandas import Timestamp
from src.database.weather_adapter import WeatherPostgresAdapter
from src.models.weather import (
  WeatherEventModel,
  WeatherMarketModel,
  WeatherEventPredictionModel,
  WeatherMarketPredictionModel,
)


class WeatherPredictor:
  """
  This class implements the WeatherPredictor, which is responsible for generating
  weather predictions.
  """

  def __init__(self) -> None:
    """
    This function initializes the WeatherPredictor class.
    """
    self.database_adapter = WeatherPostgresAdapter()


  # ---- Public API ----------------------------------

  def predict_event_probability(
    self, 
    event: WeatherEventModel
  ) -> WeatherEventPredictionModel:
    """
    This function predicts the probability of a weather event occurring with calibration
    applied, when possible.

    Parameters
    ----------------
    event (WeatherEventModel):
      The weather event for which to predict the probability.

    Returns
    ----------------
    WeatherEventPredictionModel:
      The structured prediction data for the weather event.
    """
    forecast_mean = event.forecast.forecast_mean
    forecast_stdev = event.forecast.forecast_stdev

    target_date = Timestamp(event.resolution_time).tz_convert(timezone.utc).normalize()
    current_date = Timestamp.now(tz=timezone.utc).normalize()
    lead_days = (target_date - current_date).days

    try:
      model_params = self.database_adapter.load_model_parameters(
        icao_code=event.location.icao_code,
        lead_days=lead_days
      )
      if model_params is None:
        mu_calibrated = forecast_mean
        sigma_calibrated = forecast_stdev

      else:
        mu_calibrated = model_params.a + (model_params.b * forecast_mean)
        variance_calibrated = model_params.c + (model_params.d * (forecast_stdev ** 2))
        sigma_calibrated = sqrt(variance_calibrated)

    except Exception as e:
      mu_calibrated = forecast_mean
      sigma_calibrated = forecast_stdev

    execution_time = Timestamp.now(tz=timezone.utc)
    market_predictions = {}
    for market_id, market_model in event.markets.items():
      prediction_result_model = self._predict_market_probability(
        event=event,
        market=market_model,
        lead_days=lead_days,
        mu_calibrated=float(mu_calibrated),
        sigma_calibrated=float(sigma_calibrated),
        execution_time=execution_time
      )
      market_predictions[market_id] = prediction_result_model

    event_prediction_model = WeatherEventPredictionModel(
      market_predictions=market_predictions
    )

    return event_prediction_model
  

  # ---- Internal Helpers ----------------------------

  def _predict_market_probability(
    self,
    event: WeatherEventModel,
    market: WeatherMarketModel,
    lead_days: int,
    mu_calibrated: float,
    sigma_calibrated: float,
    execution_time: Timestamp
  ) -> WeatherMarketPredictionModel:
    """
    This function predicts the probability of a weather event occurring for a specific market.

    Parameters
    ----------------
    event (WeatherEventModel):
      The weather event for which the market is associated.

    market (WeatherMarketModel):
      The market for which to predict the probability.

    lead_days (int):
      The number of lead days until the event's resolution.

    mu_calibrated (float):
      The calibrated mean for the event's forecast.

    sigma_calibrated (float):
      The calibrated standard deviation for the event's forecast.

    execution_time (Timestamp):
      The timestamp when the prediction is executed.

    Returns
    ----------------
    WeatherMarketPredictionModel:
      The structured prediction data for the market.
    """
    lower_temperature_bound, upper_temperature_bound = market.bucket_range

    cdf_upper = norm.cdf(upper_temperature_bound, loc=mu_calibrated, scale=sigma_calibrated)
    cdf_lower = norm.cdf(lower_temperature_bound, loc=mu_calibrated, scale=sigma_calibrated)
    predicted_probability = cdf_upper - cdf_lower

    market_prediction_model = WeatherMarketPredictionModel(
      market_id=market.market_id,
      icao_code=event.location.icao_code,
      lead_days=lead_days,
      predicted_probability=float(predicted_probability),
      last_updated=execution_time
    )

    return market_prediction_model
