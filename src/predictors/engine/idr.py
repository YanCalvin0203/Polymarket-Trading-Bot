from numpy import ndarray
from sklearn.isotonic import IsotonicRegression


class IDREngine:
  """
  This class implements the Isotonic Distributional Regression (IDR) engine, which
  is responsible for generating calibrated probability predictions for weather events.
  """

  def __init__(self) -> None:
    """
    This function initializes the IDREngine class.
    """
    self.model = IsotonicRegression(
      increasing=True, 
      out_of_bounds="clip"
    )
  

  # ---- Public API ----------------------------------

  def predict(self, samples: ndarray) -> ndarray:
    """
    This functions runs the prediction function on the IDR model.

    Parameters
    ----------------
    samples (ndarray):
      The input samples for which to generate predictions.

    Returns
    ----------------
    ndarray:
      The predicted probabilities for the input samples.
    """
    return self.model.predict(T=samples)

  def train(self, X: ndarray, y: ndarray) -> IsotonicRegression:
    """
    This function trains the IDR model.

    Parameters
    ----------------
    X (ndarray):
      The input features for training the model.

    y (ndarray):
      The target probabilities for training the model.

    Returns
    ----------------
    IsotonicRegression:
      The trained IDR model.
    """
    trained_model = self.model.fit(X, y)
    return trained_model

  def load_model(self, model: IsotonicRegression) -> IsotonicRegression:
    """
    This function loads a pre-trained IDR model.

    Parameters
    ----------------
    model (IsotonicRegression):
      The pre-trained IDR model to load.

    Returns
    ----------------
    IsotonicRegression:
      The loaded IDR model.
    """
    self.model = model
    return self.model
    