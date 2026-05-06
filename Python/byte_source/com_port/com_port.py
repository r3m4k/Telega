# System imports
from typing import Callable, Any
from serial import Serial, SerialException, SerialTimeoutException

# External imports

# User imports
from byte_source.bytes_source import BytesSource
from byte_source.com_port.com_port_error import ComPortReadError


#########################

# Класс для работы с com портом
class ComPort(BytesSource):
    _port: Serial     # Используемый com порт

    def __init__(self, port_name: str, baudrate: int, printing_func: Callable[..., None] = print):
        self._port_name: str = port_name    # Имя используемого com порта
        self._baudrate: int = baudrate      # Скорость работы порта
        self._printing_func: Callable[[str, ...], ...] = printing_func

    def setup(self):
        """ Настройка порта """
        self._printing_func(f'\nПодключение к порту {self._port_name}...')
        try:
            self._port = Serial(port=self._port_name, baudrate=self._baudrate)
            self._printing_func('✅ Успешно')
            self._port.write(bytes([0x7e, 0xe7, 0xff, 0xbc, 0xcb, 0xeb]),)
        except Exception as err:
            self._printing_func('❌ Ошибка подключения. Подробная информация:')
            self._printing_func(err)
            raise ComPortReadError(f"Ошибка последовательного порта: {err}", original_exception=err)

    def cleanup(self):
        """ Завершение работы порта """
        try:
            self._port.write(bytes([0x7e, 0xe7, 0xff, 0xcd, 0xdc, 0x0d]))
            self._port.close()
        except Exception:
            pass

    def read_byte(self) -> bytes:
        try:
            data = self._port.read(1)
            if not data:  # таймаут, байт не прочитан
                raise ComPortReadError("Таймаут при чтении байта из COM-порта")
            return data
        except (SerialException, SerialTimeoutException) as err:
            raise ComPortReadError(f"Ошибка последовательного порта: {err}", original_exception=err)
