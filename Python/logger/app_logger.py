# -*- coding: utf-8 -*-
"""Модуль для настройки и использования логгера приложения.

Содержит класс `AppLogger`, который инкапсулирует настройку корневого логгера
и предоставляет методы для записи сообщений и получения дочерних логгеров.
В модуле также определён глобальный экземпляр `app_logger`, который можно
импортировать и использовать во всём приложении.
"""

# System imports
import logging
from pathlib import Path
from typing import Optional

# User imports
from app_config.app_config import AppConfig

#############################################

# Название корневого логгера приложения
_ROOT_LOGGER_NAME = 'AppLogger'

# ------------------------------------------

class AppLogger:
    """Класс для управления логгером приложения.

    Настраивает корневой логгер с файловым и/или консольным обработчиками
    согласно конфигурации. Предоставляет метод get_logger() для получения
    дочерних логгеров с явным именем для удобного анализа логов.

    Пример использования:
        # В каждом классе получаем дочерний логгер с явным именем
        app_logger = AppLogger()
        logger = app_logger.get_logger('App.ComPort')
        logger.debug('Подключение к порту...')
    """

    def __init__(self, config: AppConfig):
        """Инициализирует логгер приложения по общей конфигурации."""
        self._config: AppConfig = config

        self._file_handler:    Optional[logging.Handler] = None
        self._console_handler: Optional[logging.Handler] = None

        # Создаём корневой логгер приложения
        self._logger = logging.getLogger(_ROOT_LOGGER_NAME)
        self._logger.setLevel(self._config.logger_config.log_level)

        # Настраиваем обработчики согласно конфигурации
        if self._config.logger_config.use_file:
            self._setup_file_handler(self._config.logger_config.log_dir)

        if self._config.logger_config.use_console:
            self._setup_console_handler()

    # =============================================================
    # =================== Настройка обработчиков ==================
    # =============================================================

    def _make_formatter(self) -> logging.Formatter:
        """Создаёт форматтер из текущей конфигурации."""
        return logging.Formatter(
            self._config.logger_config.log_format,
            self._config.logger_config.date_format
        )

    def _setup_file_handler(self, log_dir: Path) -> None:
        """Создаёт или заменяет файловый обработчик логгера.

        Если файл лога уже существует, переименовывает его в .bkp
        перед созданием нового.

        Args:
            log_dir (Path): Путь к директории для хранения файла лога.
        """
        log_dir = Path(log_dir).resolve()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / self._config.logger_config.log_filename

        # Сохраняем предыдущий лог как резервную копию
        try:
            if log_file.exists():
                backup_file = log_dir / (log_file.name + '.bkp')
                if backup_file.exists():
                    backup_file.unlink()
                log_file.rename(backup_file)
        except PermissionError:
            # Файл уже открыт другим процессом — пропускаем переименование
            pass

        # Удаляем старый обработчик если есть
        if self._file_handler is not None:
            self._logger.removeHandler(self._file_handler)
            self._file_handler.close()

        self._file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        self._file_handler.setLevel(self._config.logger_config.log_level)
        self._file_handler.setFormatter(self._make_formatter())
        self._logger.addHandler(self._file_handler)

    def _setup_console_handler(self) -> None:
        """Создаёт или заменяет консольный обработчик логгера."""

        # Удаляем старый обработчик если есть
        if self._console_handler is not None:
            self._logger.removeHandler(self._console_handler)
            self._console_handler.close()

        self._console_handler = logging.StreamHandler()
        self._console_handler.setLevel(self._config.logger_config.log_level)
        self._console_handler.setFormatter(self._make_formatter())
        self._logger.addHandler(self._console_handler)

    # =============================================================
    # =================== Публичные методы ========================
    # =============================================================

    @staticmethod
    def getLogger(name: str) -> logging.Logger:
        """Возвращает логгер с указанным именем.

        Логгер наследует уровень и обработчики корневого логгера,
        но пишет своё имя в каждую запись лога для удобной фильтрации.

        Args:
            name (str): Явное имя логгера. Рекомендуемый формат: 'App.ИмяКласса',
                        например 'App.ComPort', 'App.Decoder', 'App.Controller'.

        Returns:
            logging.Logger: Настроенный логгер.

        Пример использования:
            logger = app_logger.get_logger('App.ComPort')
            logger.info('Подключение к порту...')
        """
        return logging.getLogger(name)

    @staticmethod
    def get_child_logger(name: str) -> logging.Logger:
        """Возвращает дочерний логгер с указанным именем
        в формате _ROOT_LOGGER_NAME.name

        Дочерний логгер наследует уровень и обработчики корневого логгера,
        но пишет своё имя в каждую запись лога для удобной фильтрации.

        Args:
            name (str): Явное имя логгера. Для многоуровневой иерархии
                        логгеров имена следует разделять через точку.

        Returns:
            logging.Logger: Настроенный дочерний логгер.

        Пример использования:
            logger = app_logger.get_logger('ComPort')
            logger.info('Подключение к порту...')

            logger = app_logger.get_logger('ComPort.Device')
            logger.error('Устройство не отвечает!')
        """
        return logging.getLogger(f'{_ROOT_LOGGER_NAME}.{name}')

    def set_log_dir(self, log_dir: Path) -> None:
        """Изменяет директорию для хранения логов.

        Пересоздаёт файловый обработчик в новой директории.
        Старый файл остаётся на диске.

        Args:
            log_dir (Path): Новая директория для хранения логов.
        """
        if self._config.logger_config.use_file:
            self._setup_file_handler(log_dir)

    def set_log_level(self, level: int) -> None:
        """Изменяет уровень логирования в рантайме.

        Применяет новый уровень к корневому логгеру и ко всем его обработчикам.

        Args:
            level (int): Новый уровень логирования. Допустимые значения —
                logging.DEBUG, logging.INFO, logging.WARNING,
                logging.ERROR, logging.CRITICAL.

        Raises:
            ValueError: Если уровень не входит в список допустимых.

        Пример использования:
            import logging
            app_logger.set_log_level(logging.DEBUG)
        """
        allowed = (logging.DEBUG, logging.INFO, logging.WARNING,
                   logging.ERROR, logging.CRITICAL)
        if level not in allowed:
            raise ValueError(
                f'Недопустимый уровень логирования: {level}. '
                f'Допустимые: {list(allowed)}'
            )

        old_level = self._logger.level
        self._logger.setLevel(level)

        if self._file_handler is not None:
            self._file_handler.setLevel(level)
        if self._console_handler is not None:
            self._console_handler.setLevel(level)

        self._logger.info(
            f'Уровень логирования изменён: '
            f'{logging.getLevelName(old_level)} → {logging.getLevelName(level)}'
        )

    # =============================================================
    # ================ Методы для записи сообщений ================
    # =============================================================

    def debug(self, msg: str, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        self._logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        self._logger.exception(msg, *args, **kwargs)
