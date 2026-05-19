# -*- coding: utf-8 -*-
"""Модуль потокового сохранения данных, полученных от МК тележки."""

# System imports
from pathlib import Path
from typing import Optional, TextIO

# User imports
from telega_session import TelegaData

##########################################################

class DataStorage:
    """Потоковое сохранение пакетов TelegaData в CSV-файл."""

    def __init__(self) -> None:
        """Инициализирует хранилище без открытого файла."""
        self.file_path: Optional[Path] = None
        self._file: Optional[TextIO] = None
        self._sep: str = ' '
        self._count: int = 0

    @property
    def is_open(self) -> bool:
        """Возвращает True, если файл сохранения открыт."""
        return self._file is not None and not self._file.closed

    @property
    def count(self) -> int:
        """Возвращает количество записанных пакетов в текущий файл."""
        return self._count

    def set_file(self, file_path: Path, sep: str = ' ') -> None:
        """Задаёт новый файл для потокового сохранения данных.

        Args:
            file_path: Путь к CSV-файлу.
            sep: Разделитель полей. По умолчанию пробел.

        Raises:
            TypeError: Если file_path не является экземпляром Path.
        """
        if not isinstance(file_path, Path):
            raise TypeError(f"Ожидается file_path: Path, получен {type(file_path)}")
        if self.file_path == file_path and self.is_open:
            return

        self.close()
        self.file_path = file_path
        self._sep = sep
        self._count = 0

        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self.file_path, 'w', encoding='utf-8', newline='')
            self._write_header()
        except Exception:
            self.close()
            raise

    def add_package(self, package: TelegaData) -> None:
        """Записывает новый пакет данных в текущий CSV-файл.

        Args:
            package: Объект TelegaData, полученный от МК.

        Raises:
            TypeError: Если package не является экземпляром TelegaData.
        """
        if not isinstance(package, TelegaData):
            raise TypeError(f"Ожидается package: TelegaData, получен {type(package)}")
        file = self._file
        if file is None or file.closed:
            return

        file.write(
            f'{package.package_num}{self._sep}'
            f'{package.dpp_code}{self._sep}'
            f'{package.acc.x_coord}{self._sep}{package.acc.y_coord}{self._sep}{package.acc.z_coord}{self._sep}'
            f'{package.gyro.x_coord}{self._sep}{package.gyro.y_coord}{self._sep}{package.gyro.z_coord}\n'
        )
        self._count += 1

    def close(self) -> None:
        """Закрывает текущий файл сохранения."""
        if self._file is None:
            return

        self._file.close()
        self._file = None

    def _write_header(self) -> None:
        """Записывает заголовок CSV-файла."""
        file = self._file
        if file is None or file.closed:
            return

        file.write(
            f'PackageNum{self._sep}DppCode{self._sep}'
            f'AccX{self._sep}AccY{self._sep}AccZ{self._sep}'
            f'GyroX{self._sep}GyroY{self._sep}GyroZ\n'
        )
