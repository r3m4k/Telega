# -*- coding: utf-8 -*-
"""Модуль конфигурации логгера.

Содержит модель `LoggerConfig` для настройки файлового логирования.
"""

# System imports
from typing import Optional
import logging
from pathlib import Path

# External imports
from pydantic import BaseModel, Field, field_validator

# User imports

#############################################

class LoggerConfig(BaseModel):
    """Настройки файлового логгера.

    Attributes:
        log_dir (Path): Директория для сохранения логов. По умолчанию "./logs".
        log_filename (str): Имя файла лога. По умолчанию ".logger.log".
        log_format (str): Строка форматирования логов.
        date_format (str): Формат даты в логах.
        log_level (int): Уровень логирования (одно из значений logging.DEBUG, INFO и т.д.).
    """

    log_dir: Path = Field(Path(".logs"), description="Директория для логов")
    log_filename: str = Field(".logger.log", description="Имя файла лога")
    log_format: str = Field(
        "%(asctime)s - %(levelname)s - %(name)s:\n%(message)s",
        description="Строка форматирования логов"
    )
    date_format: str = Field("%Y-%m-%d %H:%M:%S", description="Формат даты")
    log_level: int = Field(logging.DEBUG, description="Уровень логирования")

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: int) -> int:
        allowed = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
        if v not in allowed:
            raise ValueError(f"Недопустимый уровень логирования: {v}. Допустимые: {allowed}")
        return v