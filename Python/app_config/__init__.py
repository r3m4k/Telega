# -*- coding: utf-8 -*-
"""Пакет управления конфигурацией приложения.

Предоставляет класс модели конфигурации `AppConfig` и готовый к использованию
глобальный экземпляр `config`, загруженный из JSON-файла при импорте пакета.

Attributes:
    AppConfig (class): Класс модели конфигурации. Может быть использован
        для создания отдельных экземпляров (например, в тестах) или для
        аннотаций типов.
"""


__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from pathlib import Path
from .app_config import AppConfig, LoggerConfig, ComPortConfig

# Определяем путь к файлу конфигурации
config_path = Path(__file__).parent / "settings.json"

# --------------------------------------------------------

__all__ = [
    'AppConfig',
    'config_path',
    'LoggerConfig',
    'ComPortConfig'
]

# --------------------------------------------------------
