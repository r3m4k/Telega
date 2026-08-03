# -*- coding: utf-8 -*-
"""Потоковое сохранение пакетов тележки в CSV-файлы.

Модуль содержит синхронное CSV-хранилище и асинхронного владельца записи.
Все операции с файлом выполняются последовательно одной фоновой задачей,
чтобы при частоте телеметрии 200 Гц не блокировать обработку байтов МК.
"""

# System imports
import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Optional, TextIO

# External imports

# User imports
from telega_session.decoder_telega import TelegaData

#############################################

_MAX_PACKAGES_IN_BATCH: int = 64
_BATCH_MAX_WAIT: float = 0.02
_STORAGE_QUEUE_SIZE: int = 2048

StorageErrorHandler = Callable[[Exception, Optional[Path]], Awaitable[None]]


class DataStorageError(RuntimeError):
    """Ошибка работы потокового CSV-хранилища."""


class DataStorage:
    """Синхронное потоковое сохранение пакетов :class:`TelegaData` в CSV."""

    def __init__(self) -> None:
        """Инициализирует хранилище без открытого файла."""
        self.file_path: Optional[Path] = None
        self._file: Optional[TextIO] = None
        self._sep: str = ' '
        self._count: int = 0

    @property
    def is_open(self) -> bool:
        """Возвращает ``True``, если файл сохранения открыт."""
        return self._file is not None and not self._file.closed

    @property
    def count(self) -> int:
        """Возвращает количество записанных пакетов текущего файла."""
        return self._count

    def set_file(self, file_path: Path, sep: str = ' ') -> None:
        """Открывает новый CSV-файл и записывает заголовок.

        Args:
            file_path: Абсолютный путь к создаваемому CSV-файлу.
            sep: Разделитель полей CSV.

        Raises:
            TypeError: Если ``file_path`` не является :class:`Path`.
            OSError: Если не удалось создать директорию или открыть файл.
        """
        if not isinstance(file_path, Path):
            raise TypeError(f'Ожидается file_path: Path, получен {type(file_path)}')

        self.close()
        self.file_path = file_path
        self._sep = sep
        self._count = 0

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(file_path, 'w', encoding='utf-8', newline='')
            self._write_header()
        except OSError:
            self.close()
            raise

    def add_packages(self, packages: list[TelegaData]) -> None:
        """Записывает одну пачку декодированных пакетов.

        Args:
            packages: Пакеты телеметрии в порядке получения от МК.

        Raises:
            DataStorageError: Если файл сохранения не открыт.
            TypeError: Если в пачке находится объект другого типа.
            OSError: Если не удалось записать данные.
        """
        if not packages:
            return

        file = self._file
        if file is None or file.closed:
            raise DataStorageError('Невозможно записать данные: CSV-файл не открыт')

        lines: list[str] = []
        for package in packages:
            if not isinstance(package, TelegaData):
                raise TypeError(f'Ожидается package: TelegaData, получен {type(package)}')
            lines.append(
                f'{package.package_num}{self._sep}'
                f'{package.dpp_code}{self._sep}'
                f'{package.acc.x_coord}{self._sep}{package.acc.y_coord}{self._sep}{package.acc.z_coord}{self._sep}'
                f'{package.gyro.x_coord}{self._sep}{package.gyro.y_coord}{self._sep}{package.gyro.z_coord}'
                f'{self._sep}{package.temp}\n'
            )

        file.writelines(lines)
        self._count += len(packages)

    def flush(self) -> None:
        """Сбрасывает буфер текущего CSV-файла в операционную систему."""
        file = self._file
        if file is not None and not file.closed:
            file.flush()

    def close(self) -> None:
        """Сбрасывает буфер и закрывает текущий CSV-файл."""
        file = self._file
        if file is None:
            return

        try:
            if not file.closed:
                file.flush()
                file.close()
        finally:
            self._file = None

    def _write_header(self) -> None:
        """Записывает заголовок CSV-файла."""
        file = self._file
        if file is None or file.closed:
            raise DataStorageError('Невозможно записать заголовок: CSV-файл не открыт')

        file.write(
            f'PackageNum{self._sep}DppCode{self._sep}'
            f'AccX{self._sep}AccY{self._sep}AccZ{self._sep}'
            f'GyroX{self._sep}GyroY{self._sep}GyroZ{self._sep}Temp\n'
        )


class AsyncDataStorageWriter:
    """Асинхронный владелец пакетной записи :class:`TelegaData` в CSV.

    Производитель помещает данные в ограниченную очередь, а единственная
    фоновая задача записывает их пачками. При заполнении очереди применяется
    обратное давление, поэтому память не растёт бесконтрольно.
    """

    def __init__(self, error_handler: StorageErrorHandler) -> None:
        """Инициализирует писатель.

        Args:
            error_handler: Асинхронный обработчик ошибки фоновой записи.
        """
        self._storage: DataStorage = DataStorage()
        self._queue: asyncio.Queue[TelegaData] = asyncio.Queue(maxsize=_STORAGE_QUEUE_SIZE)
        self._lock: asyncio.Lock = asyncio.Lock()
        self._error_handler: StorageErrorHandler = error_handler
        self._task: Optional[asyncio.Task] = None
        self._write_error: Optional[Exception] = None

    @property
    def file_path(self) -> Optional[Path]:
        """Возвращает путь текущего CSV-файла."""
        return self._storage.file_path

    @property
    def is_open(self) -> bool:
        """Возвращает ``True``, если CSV-файл готов к записи."""
        return self._storage.is_open

    async def start(self) -> None:
        """Запускает фоновую задачу записи."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._writing_loop())

    async def set_file(self, file_path: Path) -> None:
        """Осушает очередь и открывает новый CSV-файл.

        Args:
            file_path: Абсолютный путь к файлу сохранения.

        Raises:
            DataStorageError: Если фоновая запись уже завершилась ошибкой.
            OSError: Если не удалось подготовить файл.
        """
        self._raise_write_error()
        async with self._lock:
            await self._queue.join()
            await asyncio.to_thread(self._storage.set_file, file_path)

    async def write_package(self, package: TelegaData) -> None:
        """Добавляет пакет в очередь фонового писателя.

        Args:
            package: Декодированный пакет телеметрии.

        Raises:
            DataStorageError: Если фоновая запись завершилась ошибкой.
            TypeError: Если ``package`` имеет неверный тип.
        """
        if not isinstance(package, TelegaData):
            raise TypeError(f'Ожидается package: TelegaData, получен {type(package)}')

        self._raise_write_error()
        async with self._lock:
            if not self.is_open:
                return
            await self._queue.put(package)

    async def close(self) -> None:
        """Осушает очередь, сбрасывает буфер и закрывает CSV-файл."""
        async with self._lock:
            await self._queue.join()
            if self.is_open:
                await asyncio.to_thread(self._storage.close)

    async def stop(self) -> None:
        """Останавливает фоновую задачу записи после закрытия файла."""
        await self.close()
        task = self._task
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def _writing_loop(self) -> None:
        """Извлекает пакеты из очереди и записывает их пачками."""
        try:
            while True:
                package = await self._queue.get()
                packages: list[TelegaData] = [package]
                deadline = asyncio.get_running_loop().time() + _BATCH_MAX_WAIT

                while len(packages) < _MAX_PACKAGES_IN_BATCH:
                    timeout = deadline - asyncio.get_running_loop().time()
                    if timeout <= 0:
                        break
                    try:
                        package = await asyncio.wait_for(self._queue.get(), timeout=timeout)
                    except asyncio.TimeoutError:
                        break
                    packages.append(package)

                try:
                    await asyncio.to_thread(self._storage.add_packages, packages)
                except (DataStorageError, OSError) as err:
                    self._write_error = err
                    self._complete_packages(packages)
                    await self._discard_queued_packages()
                    await self._error_handler(err, self.file_path)
                    return

                self._complete_packages(packages)

        except asyncio.CancelledError:
            raise

    def _complete_packages(self, packages: list[TelegaData]) -> None:
        """Отмечает пакеты как полностью обработанные очередью."""
        for _ in packages:
            self._queue.task_done()

    async def _discard_queued_packages(self) -> None:
        """Освобождает ожидание ``join`` после неисправимой ошибки записи."""
        while True:
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            self._queue.task_done()

    def _raise_write_error(self) -> None:
        """Пробрасывает ранее полученную ошибку фоновой записи."""
        if self._write_error is not None:
            raise DataStorageError(f'Фоновая запись CSV завершилась ошибкой: {self._write_error}')
