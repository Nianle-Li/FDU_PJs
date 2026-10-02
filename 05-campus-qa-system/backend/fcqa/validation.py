from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
from typing import Any

from .errors import ApiError


def clean_text(payload: dict[str, Any], key: str, *, required: bool = True, default: str | None = None) -> str:
    value = payload.get(key, default)
    if value is None:
        if required:
            raise ApiError(HTTPStatus.BAD_REQUEST, f"缺少字段：{key}")
        return ""
    value = str(value).strip()
    if required and not value:
        raise ApiError(HTTPStatus.BAD_REQUEST, f"字段不能为空：{key}")
    return value


def clean_int(payload: dict[str, Any], key: str, *, required: bool = True) -> int | None:
    value = payload.get(key)
    if value in (None, ""):
        if required:
            raise ApiError(HTTPStatus.BAD_REQUEST, f"缺少字段：{key}")
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ApiError(HTTPStatus.BAD_REQUEST, f"字段必须是整数：{key}") from exc


def parse_datetime_text(value: str | None) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip().replace("T", " ")
    try:
        datetime.fromisoformat(text)
    except ValueError as exc:
        raise ApiError(HTTPStatus.BAD_REQUEST, "时间格式应为 YYYY-MM-DD HH:MM:SS 或浏览器 datetime-local 格式") from exc
    return text
