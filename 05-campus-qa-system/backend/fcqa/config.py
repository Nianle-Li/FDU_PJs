from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


_TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class LlmConfig:
    enabled: bool
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int
    max_rows: int


@dataclass(frozen=True)
class AppConfig:
    root_dir: Path
    frontend_dir: Path
    host: str
    port: int
    database_url: str
    demo_mode: bool
    llm: LlmConfig


def env_flag(value: str | None) -> bool:
    return (value or "").lower() in _TRUE_VALUES


def _load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def _int_env(source: Mapping[str, str], key: str, default: int) -> int:
    try:
        return int(source.get(key, str(default)))
    except ValueError:
        return default


def load_config(env: Mapping[str, str] | None = None) -> AppConfig:
    root_dir = Path(__file__).resolve().parents[2]
    if env is None:
        source = {**_load_dotenv(root_dir / ".env"), **os.environ}
    else:
        source = env
    return AppConfig(
        root_dir=root_dir,
        frontend_dir=root_dir / "frontend",
        host=source.get("FCQA_HOST", "127.0.0.1"),
        port=int(source.get("FCQA_PORT", source.get("PORT", "8000"))),
        database_url=source.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/fcqa"),
        demo_mode=env_flag(source.get("FCQA_DEMO_MODE")),
        llm=LlmConfig(
            enabled=env_flag(source.get("FCQA_LLM_MODE")),
            api_key=source.get("DEEPSEEK_API_KEY", "").strip(),
            base_url=source.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip(),
            model=source.get("DEEPSEEK_MODEL", "deepseek-chat").strip(),
            timeout_seconds=_int_env(source, "FCQA_LLM_TIMEOUT_SECONDS", 30),
            max_rows=_int_env(source, "FCQA_LLM_MAX_ROWS", 50),
        ),
    )
