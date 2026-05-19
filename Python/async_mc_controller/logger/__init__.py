"""
Пакет для настройки и использования логгера приложения.
"""

__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from async_mc_controller.logger.logger_protocol import LoggerProtocol
from async_mc_controller.logger.mc_logger import McLogger
from async_mc_controller.logger.foo_logger import FooLogger

# --------------------------------------------------------

__all__ = [
    'LoggerProtocol',
    'McLogger',
    'FooLogger'
]

# --------------------------------------------------------