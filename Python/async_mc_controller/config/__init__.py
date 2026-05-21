# -*- coding: utf-8 -*-
"""Пакет управления конфигурацией приложения.

Предоставляет класс модели конфигурации `AppConfig` и готовый к использованию
глобальный экземпляр `config`, загруженный из JSON-файла при импорте пакета.

Attributes:
    config (McConfig): Глобальный экземпляр конфигурации. Создаётся
        однократно при первом импорте пакета. Все последующие импорты
        `from config import config` возвращают один и тот же объект.
    AppConfig (class): Класс модели конфигурации. Может быть использован
        для создания отдельных экземпляров (например, в тестах) или для
        аннотаций типов.
"""


__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from pathlib import Path
from async_mc_controller.config.mc_config import McConfig
from async_mc_controller.config.com_port_config import ComPortConfig
from async_mc_controller.config.logger_config import LoggerConfig

# Определяем путь к файлу конфигурации
config_path = Path(__file__).parent / "settings.json"

# --------------------------------------------------------

__all__ = [
    'config_path',
    'McConfig',
    'ComPortConfig',
    'LoggerConfig'
]

# --------------------------------------------------------
