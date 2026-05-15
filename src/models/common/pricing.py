from dataclasses import dataclass


@dataclass(slots=True)
class PricingModel:
  best_yes_ask: float
  best_no_ask: float
  best_yes_bid: float
  best_no_bid: float

  # ---- Public API -------------------------------------

  def __str__(self) -> str:
    """
    This functions returns a string representation of the PricingModel 
    instance.

    Returns
    --------------
    str: The string representation of the PricingModel instance.
    """
    return (
      f"---- Pricing Model -------------------------\n"
      f"best_yes_ask:  {self.best_yes_ask},\n"
      f"best_no_ask:  {self.best_no_ask},\n"
      f"best_yes_bid:  {self.best_yes_bid},\n"
      f"best_no_bid:  {self.best_no_bid}\n"
    )
