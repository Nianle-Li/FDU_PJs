from __future__ import annotations

from datetime import datetime
from typing import Any


def json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    return str(value)
