# System imports
import asyncio
import logging
from typing import Optional
from abc import abstractmethod

# External imports
import serial_asyncio
from serial import SerialException

# User imports
from async_mc_controller.logger import LoggerProtocol, FooLogger
from async_mc_controller.byte_source.bytes_source import AsyncBytesSource
from async_mc_controller.byte_source.com_port.com_port_error import ComPortReadError

#########################

_SETUP_TIMEOUT: float = 5.0     # Таймаут открытия COM-порта (сек)


class AsyncComPort(AsyncBytesSource):
    """Асинхронный класс для работы с COM-портом.

    Использует pyserial-asyncio для нативного асинхронного чтения байтов.

    Attributes:
        _port_name (str):                   Имя используемого COM-порта.
        _baudrate (int):                    Скорость работы порта.
        _port_reader (StreamReader | None): Поток чтения из порта.
        _port_writer (StreamWriter | None): Поток записи в порт.

    Пример использования:
        async with AsyncComPort('COM3', 115200) as port:
            await port.reading_loop()
    """

    def __init__(self, port_name: str, baudrate: int):
        # Зададим логгер модуля
        self._com_port_logger: LoggerProtocol = FooLogger()

        self._port_name: str = port_name    # Имя используемого COM-порта
        self._baudrate: int = baudrate      # Скорость работы порта

        self._port_reader: Optional[asyncio.StreamReader] = None    # Поток чтения
        self._port_writer: Optional[asyncio.StreamWriter] = None    # Поток записи

        self._reading_task: Optional[asyncio.Task] = None           # Задача цикла чтения

    # =============================================================
    # ======= Методы для работы в контекстном менеджере ===========
    # =============================================================

    async def __aenter__(self) -> 'AsyncComPort':
        """Открытие COM-порта и создание потоков чтения/записи.

        Открытие порта обёрнуто в asyncio.wait_for с таймаутом _SETUP_TIMEOUT —
        защищает от зависания при проблемах с драйвером USB-Serial или
        нестандартными конвертерами.

        Raises:
            ComPortReadError: Если не удалось открыть порт за _SETUP_TIMEOUT
                секунд (зависание драйвера) или при ошибке последовательного
                порта (неверное имя, занят другим процессом и т.п.).
        """
        self._com_port_logger.info(f'Подключение порта {self._port_name} ({self._baudrate} бод)')

        try:
            self._port_reader, self._port_writer = await asyncio.wait_for(
                serial_asyncio.open_serial_connection(
                    url=self._port_name,
                    baudrate=self._baudrate
                ),
                timeout=_SETUP_TIMEOUT
            )
            self._com_port_logger.info(f'Успешное подключение к порту {self._port_name}')

            # Запуск цикла чтения данных
            if self._reading_task is None or self._reading_task.done():
                self._com_port_logger.debug(f'Запуск чтения порта {self._port_name}')
                self._reading_task = asyncio.create_task(self._reading_loop())

            return self

        except asyncio.TimeoutError as err:
            msg = (f'Таймаут открытия порта {self._port_name} '
                   f'({_SETUP_TIMEOUT} сек) — порт не отвечает')
            self._com_port_logger.error(msg)
            raise ComPortReadError(msg, original_exception=err)

        except SerialException as err:
            self._com_port_logger.error(f'Ошибка подключения к порту {self._port_name}: {err}')
            raise ComPortReadError(f'Ошибка последовательного порта: {err}', original_exception=err)

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Закрытие COM-порта и освобождение потоков."""
        try:
            # Закрытие порта
            if self._port_writer is not None:
                self._port_writer.close()
                await self._port_writer.wait_closed()
                self._com_port_logger.info(f'Порт {self._port_name} закрыт')

            # Завершение чтения данных
            if self._reading_task is not None and not self._reading_task.done():
                self._com_port_logger.debug(f'Остановка чтения из порта {self._port_name}')
                self._reading_task.cancel()
                try:
                    await self._reading_task
                except asyncio.CancelledError:
                    pass
                self._reading_task = None

        except Exception as err:
            self._com_port_logger.warning(f'Ошибка при закрытии порта {self._port_name}: {err}')

        return False

    # =============================================================
    # =================== Внутренняя логика =======================
    # =============================================================

    def set_logger(self, logger: logging.Logger) -> None:
        """Установление логгера"""
        self._com_port_logger = logger

    async def read_byte(self) -> bytes:
        """Асинхронное чтение одного байта из COM-порта.

        Returns:
            bytes: Один прочитанный байт.

        Raises:
            ComPortReadError: При ошибке чтения или потере соединения.
        """
        try:
            data = await self._port_reader.read(1)
            if not data:
                raise ComPortReadError('Соединение с COM-портом разорвано')
            return data
        except SerialException as err:
            self._com_port_logger.error(f'Ошибка чтения из порта {self._port_name}: {err}')
            raise ComPortReadError(f'Ошибка последовательного порта: {err}', original_exception=err)

    async def _reading_loop(self) -> None:
        """Основной цикл чтения байтов из COM-порта.

        Читает байты в бесконечном цикле и эмиттит сигнал NEW_BYTE в шину
        для каждого полученного байта. При перехвате ComPortReadError
        (физический обрыв соединения, ошибка последовательного порта)
        эмиттит READ_ERROR с исключением в качестве аргумента и завершается
        штатно — без проброса исключения наружу. Реакцию на ошибку
        выполняет Controller, подписанный на READ_ERROR: он выставляет
        _force_stop и из stop() эмиттит INTERRUPT_MEASURING.
        """
        self._com_port_logger.debug(f'Запуск цикла чтения из порта {self._port_name}')
        try:
            while True:
                bt = await self.read_byte()
                await self.new_byte_callback(bt)
        except ComPortReadError as err:
            self._com_port_logger.error(
                f'Прерывание цикла чтения из порта {self._port_name}: {err}'
            )
            await self.read_error_callback(err)


    @abstractmethod
    async def new_byte_callback(self, bt: bytes) -> None:
        """Отработка получения нового байта из порта.

        Метод должен быть определён в наследнике!
        """
        ...

    @abstractmethod
    async def read_error_callback(self, err: ComPortReadError) -> None:
        """Отработка ошибки чтения данных из порта.

        Метод должен быть определён в наследнике!
        """
        ...
