"""Size and JSON Schema checks shared by schemas.py and graders.py.

Kept out of schemas.py: that module will import graders for the run request, so graders
cannot import it back.
"""

import json
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

MAX_SCHEMA_BYTES = 64 * 1024


def json_bytes(value: Any) -> int:
    # UTF-8 bytes without \uXXXX escapes, so Cyrillic text is not counted six times over
    return len(json.dumps(value, ensure_ascii=False).encode())


def check_json_schema(schema: dict[str, Any], name: str) -> None:
    """Raise ValueError (a pydantic validation error inside validators) for a bad schema."""
    if json_bytes(schema) > MAX_SCHEMA_BYTES:
        raise ValueError(f"{name} не больше 64 КБ")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as e:
        raise ValueError(f"{name} не JSON Schema: {e.message}") from e
