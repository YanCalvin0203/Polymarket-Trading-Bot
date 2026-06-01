from numpy import ndarray, linspace
from KDEpy import FFTKDE
from scipy.integrate import trapezoid

class KDE:
  """
  This class implements the Kernel Density Estimation (KDE) for density 
  estimation. 
  """

  def __init__(
    self, 
    kernel: str ="gaussian", 
    bw: str ="ISJ", 
    buffer: float = 0.05, 
    grid_points: int = 1000
  ) -> None:
    """
    This function initializes the KDE class.

    Parameters
    ----------------
    kernel (str):
      The kernel to use for density estimation. Defaults to "gaussian".
    
    bw (str):
      The bandwidth method to use for density estimation. Defaults to "ISJ".

    buffer (float):
      The buffer to add to the data range when creating the prediction grid. 
      Defaults to 0.05.

    grid_points (int):
      The number of points to use for the prediction grid. Defaults to 1000.
    """
    self.kernel = kernel
    self.bw = bw
    self.buffer = buffer
    self.grid_points = grid_points
    self._x_grid: ndarray | None = None
    self._y_grid: ndarray | None = None
    self._is_fitted = False


  # ---- Public API ----------------------------------

  def fit(self, samples: ndarray, bias: float = 0.0) -> None:
    """
    This function fits the KDE model to the input samples.

    Parameters
    ----------------
    samples (ndarray):
      The input samples to fit the KDE model to.

    bias (float):
      The bias to offset for the input samples. Defaults to 0.0.
    """
    samples = samples - bias
    kde = FFTKDE(kernel=self.kernel, bw=self.bw).fit(samples)
    
    data_range = samples.max() - samples.min()
    data_buffer = data_range * self.buffer
    data_grid_points = linspace(samples.min() - data_buffer, samples.max() + data_buffer, self.grid_points)

    self._x_grid, self._y_grid = kde.evaluate(grid_points=data_grid_points)
    self._is_fitted = True

  def predict(self, min_bound: float, max_bound: float) -> float:
    """
    This function generates the probability of the input bounds based on the 
    fitted KDE model.

    Parameters
    ----------------
    min_bound (float):
      The minimum bound for the prediction range.

    max_bound (float):
      The maximum bound for the prediction range.

    Returns
    ----------------
    float:
      The probability of the input bounds.
    """
    if not self._is_fitted:
      return float("nan")
    
    selected_area = (self._x_grid >= min_bound) & (self._x_grid <= max_bound)
    if not selected_area.any():
      return float("nan")
    
    return float(trapezoid(y=self._y_grid[selected_area], x=self._x_grid[selected_area]))
  