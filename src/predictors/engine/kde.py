from scipy.special import erf
from numpy import (
  ndarray, 
  std, 
  array, 
  newaxis, 
  mean, 
  sqrt, 
  clip,
  percentile,
  minimum
)


class KDEEngine:
  """
  This class implements the Kernel Density Estimation (KDE) engine, which
  is responsible for generating probability density estimates for custom events.
  """

  # ---- Public API ----------------------------------

  def compute_kde(self, members: ndarray, buckets: list[tuple[float, float]]) -> ndarray:
    """
    This function computes the KDE probability for a custom event based on the
    provided ensemble members.

    Parameters
    ----------------
    members (ndarray):
      The ensemble members for which to compute the KDE probability.

    buckets (list[tuple[float, float]]):
      The list of buckets defining the custom event. Each bucket is a tuple of
      (lower_bound, upper_bound).

    Returns
    ----------------
    ndarray:
      The computed KDE probabilities for the custom event.
    """
    number_of_members = len(members)
    sigma_ensemble = std(members, ddof=1)

    # Zero-Variance Partition Guard
    if sigma_ensemble == 0:
      probabilities = array([1.0 if lo <= members[0] < hi else 0.0 for lo, hi in buckets])
      return probabilities

    # Calculate the Interquartile Range
    q25 = percentile(members, 25)
    q75 = percentile(members, 75)
    iqr = q75 - q25

    # Normalize the IQR to match standard deviation scaling
    normalized_iqr = iqr / 1.349 if iqr > 0 else sigma_ensemble

    # Take the tighter of σ and IQR/1.349 to resist outliers
    A = minimum(sigma_ensemble, normalized_iqr)

    # Apply robust adaptive bandwidth calculation
    h = 0.9 * A * (number_of_members ** -0.2)

    # Extract boundary horizons into clean evaluation vectors
    lower_bound_buckets = array([b[0] for b in buckets])
    upper_bound_buckets = array([b[1] for b in buckets])

    # Parallel Broadcasting Grid Analysis (Shape: [Num Buckets, 51 Members])
    z_lower = (lower_bound_buckets[:, newaxis] - members) / h
    z_upper = (upper_bound_buckets[:, newaxis] - members) / h

    # Analytical Vectorized CDF Integration via the Error Function
    cdf_lower_bound = mean(0.5 * (1.0 + erf(z_lower / sqrt(2.0))), axis=1)
    cdf_upper_bound = mean(0.5 * (1.0 + erf(z_upper / sqrt(2.0))), axis=1)

    # Extract interval slices and bound to valid physical limits
    probabilities = cdf_upper_bound - cdf_lower_bound
    return clip(probabilities, 0.0, 1.0)
