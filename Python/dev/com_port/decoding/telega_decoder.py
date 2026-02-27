# System imports
from enum import Enum
from typing import Callable

# External imports
import numpy as np

# User imports
from .data_description import TelegaData, TelegaDataIndexes
from .command import Command
from .utils import bytes_to_float, bytes_to_uint32, bytes_to_triaxial

#############################################

class PackageFormat:
    """Константы форматов пакетов протокола."""
    DataFormat = b'\xc8'        # Байт, обозначающий пакет с данными
    CommandFormat = b'\xff'     # Байт, обозначающий командный пакет

# Стадии обработки данных из порта
class Stage(Enum):
    WantHeader = 1          # Ожидание заголовка посылки
    WantFormat = 2          # Ожидание формата
    WantDataLen = 3         # Ожидание длины посылки
    WantData = 4            # Ожидание данных посылки
    WantControlSum = 5      # Ожидание контрольной суммы

# -------------------------------------------

# Декодер посылок формата Гиронавт
class TelegaDecoder:
    _header = [b'\x7e', b'\xe7']    # Заголовок посылки (2 байта)

    def __init__(self):
        self.received_data: list[TelegaData] = []       # Список данных, полученных от платы
        self.input_command: list[Command] = []          # Список поступивших команд

        # Метод для декодирования полученной посылки (по умолчанию - self._bytes_to_telega_data)
        self._decode_func: Callable[[list[bytes]], None] = self._bytes_to_telega_data

        self._stage: Stage = Stage.WantHeader       # Изначальная стадия декодера
        self._received_bytes: list[bytes] = []      # Список поступивших байтов

        self._data_bt_index = 0         # Индекс байта данных в посылке
        self._package_size = 0          # Количество байт данных в посылке

        self._num_correct_packages = 0      # Количество пакетов, полученных без ошибок
        self._num_wrong_packages = 0        # Количество пакетов, полученных с ошибками
        self._num_unknown_packages = 0      # Количество пакетов с неизвестным форматом

    @property
    def data_len(self) -> int:
        return len(self.received_data)

    def __str__(self):
        return (
            f'Информация о TelegaDecoder:\n'
            f'| Количество корректно принятых пакетов данных:     {self._num_correct_packages} из {self._num_correct_packages + self._num_wrong_packages}\n'
            f'| Количество пакетов данных, полученных с ошибкой:  {self._num_wrong_packages} из {self._num_correct_packages + self._num_wrong_packages}\n'
            f'| Среднее абсолютное значение ускорения:                  {np.mean([np.sqrt(values.acc.x_coord**2 + values.acc.y_coord**2 + values.acc.z_coord**2) for values in self.received_data]):.8f} м/с**2\n'
            f'| Среднее абсолютное значение угловой скорости:           {np.mean([np.sqrt(values.gyro.x_coord**2 + values.gyro.y_coord**2 + values.gyro.z_coord**2) for values in self.received_data]):.9f} градус/с\n'
            f'| Среднее абсолютное значение температуры:    {np.mean([values.temp for values in self.received_data]):.6f} ___\n'
        )

    def save_received_data(self, filename: str) -> None:
        pass

    def byte_processing(self, bt: bytes) -> None:
        """ Обработка поступившего байта """

        self._received_bytes.append(bt)
        # print(f'stage = {self._stage}       bt = {bt}')

        match self._stage:
            case Stage.WantHeader:
                if self._received_bytes[-2::] == self._header:
                    self._stage = Stage.WantData
                    # Отчистим self._received_bytes от возможных прошлых записанных байтов
                    self._received_bytes = self._header.copy()

            case Stage.WantFormat:
                if bt == PackageFormat.DataFormat:
                    self._decode_func = self._bytes_to_telega_data
                    self._stage = Stage.WantDataLen

                elif bt == PackageFormat.CommandFormat:
                    self._decode_func = self._bytes_to_command
                    self._package_size = 2
                    self._stage = Stage.WantData

                else:
                    self._stage = Stage.WantHeader
                    self._num_unknown_packages += 1
                    return

            case Stage.WantDataLen:
                self._package_size = int.from_bytes(bt, byteorder='big')
                self._stage = Stage.WantData

            case Stage.WantData:
                # Добавим в self._received_bytes все байты данных
                if self._data_bt_index < self._package_size - 1:
                    self._data_bt_index += 1
                else:
                    self._stage = Stage.WantControlSum
                    self._data_bt_index = 0

            case Stage.WantControlSum:
                # Проверка контрольной суммы
                if bt == self._count_control_sum(self._received_bytes):
                    self._decode_func(self._received_bytes)
                    self._num_correct_packages += 1
                else:
                    self._num_wrong_packages += 1

                self._stage = Stage.WantHeader
                self._received_bytes = []

    def _bytes_to_telega_data(self, byte_list: list[bytes]) -> None:

        time = bytes_to_uint32(byte_list[TelegaDataIndexes.time_index: TelegaDataIndexes.time_index + 4])
        acc  = bytes_to_triaxial(byte_list[TelegaDataIndexes.acc_index : TelegaDataIndexes.acc_index + 12])
        gyro = bytes_to_triaxial(byte_list[TelegaDataIndexes.gyro_index : TelegaDataIndexes.gyro_index + 12])
        temp  = bytes_to_float(byte_list[TelegaDataIndexes.temp_index : TelegaDataIndexes.temp_index + 4])

        self.received_data.append(TelegaData(time, acc, gyro, temp))

    def _bytes_to_command(self, byte_list: list[bytes]) -> None:
        """Декодирует список байт в объект Command и добавляет в список команд.

        Args:
            byte_list (list[bytes]): Список байтов всей посылки.
        """
        self.input_command.append(Command(byte_list))

    @staticmethod
    def _count_control_sum(data_bytes: list[bytes]) -> bytes:
        """ Вычисление контрольной суммы согласно документации """
        total = 0
        # Исключим последний байт (полученную контрольную сумму) из расчёта контрольной суммы
        for b in data_bytes[:-1]:
            total += int.from_bytes(b, 'big')
        return bytes([total & 0xFF])
