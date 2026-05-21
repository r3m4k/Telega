# -*- coding: utf-8 -*-
"""Модуль для настройки пути сохранения данных в GUI.

Содержит класс `SavingParams`, который управляет виджетами
`QLineEdit` и `QToolButton` для выбора директории сохранения,
а также пользовательское исключение `InvalidPathError` для обработки
ошибок, связанных с некорректным путём.
"""

# System imports
from pathlib import Path
from datetime import date
import re

# External imports
from PyQt5.QtWidgets import QFileDialog, QLineEdit, QToolButton, QPushButton, QMessageBox

# User imports
from app_config import AppConfig

##########################################################

class InvalidPathError(Exception):
    """Исключение, возникающее при некорректном пути сохранения."""
    pass

class InvalidTemplateFilenameError(Exception):
    """Исключение, возникающее при некорректном пути сохранения."""
    pass

# --------------------------------------------------------

class SavingParams:
    """Управление выбором пути сохранения и шаблонным именем файлов.

    Класс связывает:
      - поле ввода пути (`QLineEdit`) и кнопку выбора директории (`QToolButton`);
      - поле ввода шаблона имени файла (`QLineEdit`) и информационную кнопку (`QPushButton`).

    При инициализации загружает сохранённый путь из переданного конфига.
    Шаблон имени файла по умолчанию устанавливается как 'telega_YYYY-MM-DD' (текущая дата).

    Предоставляет методы:
      - get_saving_path() – возвращает абсолютный путь после проверки существования/каталога;
      - get_template_filename() – возвращает непустой шаблон с проверкой на недопустимые символы;
      - save_config() – сохраняет текущий валидный путь в конфиг (игнорирует невалидный);
      - lock_input() / unlock_input() – блокирует/разблокирует все виджеты группы.

    Исключения:
      - InvalidPathError – при некорректном пути (пустой, не существует, не директория);
      - InvalidTemplateFilenameError – при пустом шаблоне или наличии запрещённых символов.
    """

    def __init__(self,
                 app_config: AppConfig,
                 saving_path_edit: QLineEdit,
                 choose_saving_path_button: QToolButton,
                 template_filename_edit: QLineEdit,
                 template_info_button: QPushButton):
        # -------------------------------------------------------------
        super().__init__()

        if (not isinstance(saving_path_edit, QLineEdit)
                or not isinstance(choose_saving_path_button, QToolButton)
                or not isinstance(template_filename_edit, QLineEdit)
                or not isinstance(template_info_button, QPushButton)):

            raise TypeError("Ожидаются QLineEdit, QToolButton, QLineEdit и QPushButton\n"
                            f"Получены: {type(saving_path_edit)}, {type(choose_saving_path_button)}, "
                            f"{type(template_filename_edit)} и {type(template_info_button)}")
        # -------------------------------------------------------------
        self._config: AppConfig = app_config
        self._saving_path_edit: QLineEdit = saving_path_edit
        self._choose_saving_path_button: QToolButton = choose_saving_path_button
        self._template_filename_edit: QLineEdit = template_filename_edit
        self._template_info_button: QPushButton = template_info_button

        # Зададим путь сохранения и шаблонное название файлов
        self._load_saving_dir_from_config()
        self._template_filename_edit.setText(f'telega_{date.today().isoformat()}')

        # Подключим кнопки
        self._choose_saving_path_button.clicked.connect(self._select_path)
        self._template_info_button.clicked.connect(self._template_info)

    def get_saving_path(self) -> Path:
        """Возвращает выбранный путь как объект Path после проверки.

        Returns:
            Path: Абсолютный путь к директории.

        Raises:
            InvalidPathError: если путь не задан, не существует или не является директорией.
        """
        text = self._saving_path_edit.text().strip()
        if not text:
            raise InvalidPathError("Укажите путь сохранения!")

        path = Path(text).resolve()  # преобразуем в абсолютный путь

        if not path.exists():
            raise InvalidPathError(f"Указанный путь {path} не существует!")
        if not path.is_dir():
            raise InvalidPathError(f"Указанный путь {path} не является директорией!")

        return path

    def get_template_filename(self) -> str:
        """Возвращает указанное шаблонное название файлов.

        Returns:
            str: Шаблонное название файлов

        Raises:
            InvalidTemplateFilenameError: если шаблонное имя не задано.
        """
        template_filename = self._template_filename_edit.text().strip()
        if not template_filename:
            raise InvalidTemplateFilenameError("Укажите шаблонное название для файлов!")
        if re.search(r'[\\/*?:"<>|]', template_filename):
            raise InvalidTemplateFilenameError("Имя файла содержит запрещённые символы: \\ / : * ? \" < > |")
        return template_filename

    def save_config(self) -> None:
        """Сохраняет текущий путь в объект конфигурации.

        Обновляет поле `self._config.save_dir` значением, взятым из поля ввода,
        преобразованным в абсолютный путь.
        """
        try:
            path = self.get_saving_path()
            self._config.save_dir = path
            self._config.save()
        except InvalidPathError:
            pass

    def lock_input(self) -> None:
        """Блокировка редактирование параметров сохранения."""
        self._saving_path_edit.setEnabled(False)
        self._choose_saving_path_button.setEnabled(False)
        self._template_filename_edit.setEnabled(False)

    def unlock_input(self) -> None:
        """Разблокировка редактирование параметров сохранения."""
        self._saving_path_edit.setEnabled(True)
        self._choose_saving_path_button.setEnabled(True)
        self._template_filename_edit.setEnabled(True)

    def _load_saving_dir_from_config(self) -> None:
        """Загрузка пути сохранения из конфига."""
        if self._config.save_dir:
            self._saving_path_edit.setText(str(self._config.save_dir.resolve()))

    def _select_path(self) -> None:
        """Выбор пути сохранения через диалоговое окно."""

        # Текущий путь (для начальной директории диалога)
        current_path = self._saving_path_edit.text() or str(Path.home())

        # Используем поле как родительский виджет для правильного позиционирования
        directory = QFileDialog.getExistingDirectory(
            self._saving_path_edit,
            "Выберите директорию сохранения",
            current_path,
            QFileDialog.ShowDirsOnly
        )
        if directory:
            self._saving_path_edit.setText(directory)

    def _template_info(self) -> None:
        """Вывод пользователю пояснения про шаблонное название файлов"""
        QMessageBox.information(self._template_info_button,
                                'Информация о шаблонном названии файлов:',
                                'Шаблонное название файлов используется в качестве '
                                'префиксов в названиях для всех файлов, которые будут '
                                'созданы во время сбора данных.')