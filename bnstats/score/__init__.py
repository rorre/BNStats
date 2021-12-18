from typing import Dict, Type, Optional

from bnstats.score.base import CalculatorABC
from bnstats.score.naxess import NaxessCalculator
from bnstats.score.ren import RenCalculator

# fmt: off
_AVAILABLE: Dict[str, Type[CalculatorABC]] = {}
for c in (NaxessCalculator, RenCalculator):
    _AVAILABLE[c.name] = c  # type: ignore

def get_system(name: str) -> Optional[Type[CalculatorABC]]: # noqa
    """Get calculator system from name.

    Args:
        name (str): Calculator system's name to be fetched from

    Returns:
        Type[CalculatorABC]: The calculator's class.
    """
    return _AVAILABLE.get(name)
# fmt: on
