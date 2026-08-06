"""Базовый класс стадий и контракт главного окна."""

# System imports
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol

# External imports
from PyQt5.QtWidgets import QMessageBox

# User imports
from gui.com_port_settings import ComPortSettings
from gui.saving_params import SavingParams

##########################################################


class MainWindowProtocol(Protocol):
    """Описывает интерфейс главного окна, необходимый стадиям программы."""

    _saving_params: SavingParams
    _com_port_settings: ComPortSettings

    def configure_session(self,
                          saving_path: Path,
                          template_filename: str,
                          com_port_name: str) -> None:
        """Применяет параметры и запускает настройку сессии.

        Args:
            saving_path: Директория сохранения данных.
            template_filename: Шаблон имени файлов текущей сессии.
            com_port_name: Имя используемого COM-порта.
        """
        ...

    def add_info_message(self, message: str) -> None:
        """Добавляет информационное сообщение в пользовательский журнал.

        Args:
            message: Текст сообщения.
        """
        ...

    def add_warning_message(self, title: str, message: str) -> None:
        """Добавляет предупреждение в пользовательский журнал.

        Args:
            title: Заголовок предупреждения.
            message: Текст предупреждения.
        """
        ...

    def add_error_message(self, title: str, message: str) -> None:
        """Добавляет сообщение об ошибке в пользовательский журнал.

        Args:
            title: Заголовок ошибки.
            message: Описание ошибки.
        """
        ...

    def start_static_init(self) -> None:
        """Запускает набор статического буфера."""
        ...

    def start_measuring(self) -> None:
        """Запускает сбор данных."""
        ...

    def stop_measuring(self) -> None:
        """Завершает сбор данных."""
        ...


# =============================================================


class ProgramStage(ABC):
    """Определяет обработку команд для одной стадии программы.

    Args:
        main_window: Главное окно, выполняющее действия текущей стадии.
    """

    name: str = 'неизвестная стадия'

    def __init__(self, main_window: MainWindowProtocol) -> None:
        self._main_window: MainWindowProtocol = main_window

    def _show_warning(self, title: str, message: str) -> None:
        """Показывает пользователю предупреждение текущей стадии."""
        self._main_window.add_warning_message(title, message)
        QMessageBox.warning(self._main_window, title, message)

    def _show_settings_locked_warning(self) -> None:
        """Предупреждает о запрете изменения настроек после запуска работы."""
        self._show_warning(
            'Ошибка изменения параметров сохранения',
            'Параметры сохранения и настройки com порта '
            'не могут быть изменены во время работы программы'
        )

    @abstractmethod
    def apply_settings(self) -> None:
        """Сохраняет настройки COM-порта и параметры сохранения."""
        ...

    @abstractmethod
    def start_static_init(self) -> None:
        """Запускает сбор статического буфера."""
        ...

    @abstractmethod
    def start_measuring(self) -> None:
        """Запускает сбор данных."""
        ...

    @abstractmethod
    def stop_measuring(self) -> None:
        """Завершает сбор данных."""
        ...
