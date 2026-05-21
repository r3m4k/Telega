# -*- coding: utf-8 -*-
"""Модуль для настройки COM-порта в GUI.

Содержит класс `ComPortSettings`, который управляет виджетами для выбора
COM-порта, отображения информации о порте, обновления списка портов и
выбора скорости передачи данных. Также предоставляет пользовательское
исключение `ComPortError` для обработки ошибок, связанных с настройкой порта.
"""

# System imports
from pathlib import Path

# External imports
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import (QComboBox, QPushButton,
                             QMessageBox, QToolButton)
from PyQt5.QtGui import QIcon

# User imports
from app_config import AppConfig
from async_mc_controller.byte_source.com_port import get_ComPorts

##########################################################

class ComPortSettingsError(Exception):
    """Исключение, возникающее при неправильной настройке COM порта."""
    pass

# --------------------------------------------------------

class ComPortSettings(QObject):
    """Управление настройками COM-порта.

    Класс связывает выпадающий список портов (`QComboBox`), кнопку обновления
    списка (`QPushButton`) и кнопку информации о порте (`QPushButton`).
    При инициализации загружает сохранённые настройки из переданного конфига
    (восстанавливает порт по `hwid`). Скорость передачи данных фиксирована
    (115200) для USB-протокола, которому не требуется настройка скорости.

    Args:
        app_config (AppConfig): Объект конфигурации приложения.
        com_port_combo_box (QComboBox): Выпадающий список доступных COM-портов.
        com_port_info_button (QPushButton): Кнопка для отображения информации о выбранном порте.
        update_com_ports_button (QPushButton): Кнопка для обновления списка портов.

    Raises:
        TypeError: Если переданные виджеты имеют неверный тип.
    """

    _default_port: str = '-----'
    _default_baudrate = 115200

    def __init__(self,
                 app_config: AppConfig,
                 com_port_combo_box: QComboBox,
                 com_port_info_button: QPushButton,
                 update_com_ports_button: QToolButton):
        # -------------------------------------------------------------
        super().__init__()

        # Проверка типов переданных параметров
        if not isinstance(app_config, AppConfig):
            raise TypeError(f"Ожидается app_config: AppConfig, получен {type(app_config)}")
        if not isinstance(com_port_combo_box, QComboBox):
            raise TypeError(f"Ожидается com_port_combo_box: QComboBox, получен {type(com_port_combo_box)}")
        if not isinstance(com_port_info_button, QPushButton):
            raise TypeError(f"Ожидается com_port_info_button: QPushButton, получен {type(com_port_info_button)}")
        if not isinstance(update_com_ports_button, QToolButton):
            raise TypeError(f"Ожидается update_com_ports_button: QToolButton, получен {type(update_com_ports_button)}")

        # -------------------------------------------------------------

        self._app_config: AppConfig = app_config
        self._com_port_combo_box: QComboBox = com_port_combo_box
        self._com_port_info_button: QPushButton = com_port_info_button
        self._update_com_ports_button: QToolButton = update_com_ports_button

        self._com_ports: dict[str, dict[str, str]] = {}     # информация о доступных портах
        self._current_port: str = self._default_port        # текущий выбранный порт (по умолчанию заглушка)

        self._init_UI()

    def _init_UI(self) -> None:
        """Инициализация интерфейса: установка иконки, подключение сигналов,
        первичное обновление списка портов и загрузка настроек из конфига.
        """
        # Поместим на кнопку обновления соответствующую иконку
        icon_path = Path(__file__).parent / "ui" / "update.png"
        self._update_com_ports_button.setIcon(QIcon(str(icon_path)))

        self._connect_signals()
        self._load_com_ports()
        self._load_from_config()

    def reset(self) -> None:
        """ Сброс настроек порта """
        self._load_com_ports()

    def get_port_name(self) -> str:
        """Возвращает имя выбранного порта.

        Raises:
            ComPortSettingsError: если имя порта не задано.
        """
        if self._com_port_combo_box.currentText() and self._com_port_combo_box.currentText() != self._default_port:
            return self._com_port_combo_box.currentText()
        raise ComPortSettingsError("Выберите порт для подключения!")

    def lock_input(self) -> None:
        """Блокирует все элементы управления настройками COM-порта."""
        self._com_port_combo_box.setEnabled(False)
        self._update_com_ports_button.setEnabled(False)

    def unlock_input(self) -> None:
        """Разблокирует все элементы управления настройками COM-порта."""
        self._com_port_combo_box.setEnabled(True)
        self._update_com_ports_button.setEnabled(True)

    def save_config(self) -> None:
        """Сохраняет текущие настройки порта в конфиг."""
        if self._current_port != self._default_port:
            self._app_config.com_port.name = self._current_port
            self._app_config.com_port.desc = self._com_ports[self._current_port]["desc"]
            self._app_config.com_port.hwid = self._com_ports[self._current_port]["hwid"]
            self._app_config.com_port.baudrate = self._default_baudrate
        self._app_config.save()

    def _connect_signals(self) -> None:
        """Подключает сигналы виджетов к внутренним слотам."""
        self._com_port_combo_box.currentTextChanged.connect(self._on_port_changed)
        self._com_port_info_button.clicked.connect(self._show_port_info)
        self._update_com_ports_button.clicked.connect(self._load_com_ports)

    def _load_from_config(self) -> None:
        """Загружает сохранённые настройки из конфига и применяет их.

        - Восстанавливает порт по совпадению `hwid` (если такой порт есть в текущем списке).
        """
        # Зададим порт по умолчанию, если hwid одного из порта совпадает с self._app_config.com_port.hwid
        for port in self._com_ports.keys():
            if self._app_config.com_port.hwid:
                if self._com_ports[port]["hwid"] == self._app_config.com_port.hwid:
                    self._com_port_combo_box.setCurrentIndex(list(self._com_ports.keys()).index(port))

    def _load_com_ports(self) -> None:
        """Обновляет список доступных COM-портов.

        Получает актуальный список через `get_ComPorts()`, добавляет фиктивный
        элемент self._default_port в начало и заполняет комбобокс.
        """
        self._com_ports = (
                {self._default_port: {"desc": "Здесь будет отображаться дескриптор выбранного COM порта",
                                      "hwid": "Здесь будет отображаться hwid выбранного COM порта"}} | get_ComPorts()
        )
        self._com_port_combo_box.clear()
        self._com_port_combo_box.addItems(self._com_ports.keys())

    def _show_port_info(self) -> None:
        """Отображает диалоговое окно с информацией о выбранном порте."""
        QMessageBox.information(self._com_port_info_button.parent(),
                                "Информация о выбранном порте",
                                f"Выбранный порт: {self._current_port}\n"
                                f"| desc: {self._com_ports[self._current_port]['desc']}\n"
                                f"| hwid: {self._com_ports[self._current_port]['hwid']}\n")

    def _on_port_changed(self, port_name: str) -> None:
        """Слот, вызываемый при изменении выбранного порта в комбобоксе."""
        self._current_port = port_name
