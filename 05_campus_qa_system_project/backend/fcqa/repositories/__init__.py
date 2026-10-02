from __future__ import annotations

from ..config import AppConfig
from .base import CampusRepository
from .demo import DemoRepository
from .postgres import PostgresRepository


def create_repository(config: AppConfig) -> CampusRepository:
    if config.demo_mode:
        return DemoRepository()
    return PostgresRepository(config.database_url, config.llm)


__all__ = ["CampusRepository", "DemoRepository", "PostgresRepository", "create_repository"]
