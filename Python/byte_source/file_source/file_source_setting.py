# -*- coding: utf-8 -*-
"""Модуль для настройки файлового источника данных.

Предоставляет класс `FileSourceSetting`, который управляет выбором файла
с лог-данными, используя глобальную конфигурацию приложения (`config`).
Позволяет использовать сохранённый путь из конфига или запросить новый у пользователя,
а затем сохраняет выбранный путь обратно в конфигурацию.
"""

# System imports
from pathlib import Path

# External imports

# User imports
from config import config
from byte_source import BytesSource
from byte_source.file_source import FileSource
from utils import confirm_from_console

#########################

class FileSourceSetting:
    """Настройка файлового источника с использованием глобальной конфигурации.

    При создании экземпляра пытается загрузить путь к файлу из конфигурации.
    Если в конфиге есть путь и файл существует, предлагает пользователю
    использовать его. В противном случае или при отказе пользователя
    запрашивает новый путь, проверяет существование файла и сохраняет
    его в конфигурацию.

    Attributes:
        _filename (str): Выбранный путь к файлу (строка). Путь нормализован.
    """

    _filename: Path

    def __init__(self) -> None:
        """Инициализирует настройку, загружая данные из конфигурации."""
        self._load_from_config()

    def _load_from_config(self) -> None:
        """Пытается загрузить путь из конфига, если файл существует.

        Если в `config.file_source.filename` указан путь и файл существует,
        пользователю предлагается подтвердить его использование.
        При подтверждении путь сохраняется в `_filename` и метод завершается.
        Иначе вызывается `_load_filename_from_console()` для ручного ввода.
        """
        cached_path = config.file_source.filename

        if cached_path and cached_path.is_file():
            print(f'Использовать файл "{cached_path}" в качестве источника данных?')
            if confirm_from_console():
                self._filename = cached_path
                return

        # Если нет сохранённого пути, файл не найден или пользователь отказался
        self._load_filename_from_console()

    def _load_filename_from_console(self) -> None:
        """Запрашивает путь к файлу у пользователя, проверяет существование и сохраняет в конфиг.

        Выводит приглашение для ввода абсолютного пути к файлу.
        Введённая строка очищается от кавычек и преобразуется в объект `Path`.
        Если файл существует:
            - сохраняет нормализованный путь в `_filename`
            - обновляет `config.file_source.filename` и вызывает `config.save()`
        Иначе выводит сообщение об ошибке и завершает программу (exit(1)).
        """
        user_input = input('Введите абсолютный путь log файла с записанными данными:\n').strip()

        # Удаляем возможные кавычки
        user_input = user_input.replace('"', '').replace("'", "")
        path = Path(user_input).resolve()

        if path.is_file():
            self._filename = path
            # Сохраняем путь в глобальный конфиг
            config.file_source.filename = path
            config.save()
        else:
            print(f'Не удаётся найти файл "{path}"!\n'
                  f'Проверьте корректность ввода.\n')
            exit(1)

    def get_bytes_source(self) -> BytesSource:
        """Возвращает источник байтов для чтения из выбранного файла.

        Returns:
            BytesSource: Экземпляр `FileSource`, привязанный к выбранному файлу.

        Raises:
            RuntimeError: Если имя файла не было задано (например, если метод
                вызван до завершения настройки).
        """
        if not self._filename:
            raise RuntimeError('Имя файла не задано!')

        return FileSource(self._filename)