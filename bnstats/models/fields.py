import json
from typing import Any, Dict, Optional

from tortoise.exceptions import FieldError
from tortoise.fields import JSONField

_AVAILABLE = ["ren", "naxess"]


class ScoreField(JSONField):
    def to_db_value(self, value: Dict[str, Any], instance):  # type: ignore[override]
        db_json: Optional[Dict[str, str]]
        if value:
            db_json = {}
            for k in value.keys():
                db_json[k] = value[k]
        else:
            db_json = None
        return super().to_db_value(db_json, instance)

    def to_python_value(self, value: Optional[dict]) -> Optional[Dict]:  # type: ignore[override]
        if isinstance(value, str):
            try:
                value = self.decoder(value)
            except Exception:
                raise FieldError(f"Value {value} is invalid json value.")

        if not value:
            return {k: dict(calculator_name=k) for k in _AVAILABLE}

        output_dict: Dict[str, Any] = {}
        for k in value.keys():
            if isinstance(value[k], dict):
                output_dict[k] = value[k]
            elif isinstance(value[k], str):
                output_dict[k] = json.loads(value[k])
        return output_dict
