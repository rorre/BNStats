import json
from typing import Dict, Optional, Union
from tortoise.fields import JSONField
from tortoise.exceptions import FieldError
from pydantic import BaseModel

_AVAILABLE = ["ren", "naxess"]


class Score(BaseModel):
    mapset_score: float = 0.0
    mapper_score: float = 0.0
    ranked_score: float = 0.0
    penalty: float = 0.0
    total_score: float = 0.0
    calculator_name: str


class ScoreField(JSONField):
    def to_db_value(self, value: Dict[str, Score], instance) -> str:
        db_json: Dict[str, str] = {}
        for k in value.keys():
            db_json[k] = value[k].json()
        return super().to_db_value(db_json, instance)

    def to_python_value(self, value: Optional[Union[str, dict]]) -> Optional[Dict]:
        if isinstance(value, str):
            try:
                value = self.decoder(value)
            except Exception:
                raise FieldError(f"Value {value} is invalid json value.")

        if not value:
            return {k: Score(calculator_name=k) for k in _AVAILABLE}

        output_dict: Dict[str, Score] = {}
        for k in value.keys():
            if isinstance(value[k], Score):
                output_dict[k] = value[k]
            else:
                if isinstance(value[k], str):
                    value[k] = json.loads(value[k])
                output_dict[k] = Score(**value[k])
        return output_dict
