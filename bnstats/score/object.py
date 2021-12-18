from typing import Dict, NamedTuple, SupportsFloat


class Score(NamedTuple):
    total_score: float
    attribs: Dict[str, SupportsFloat]
