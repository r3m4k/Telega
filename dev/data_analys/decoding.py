# System imports
import os
from enum import Enum
import binascii
from typing import BinaryIO

# External imports
import numpy as np

# User imports


##########################################################


class Decoder:
    """
    Класс для декодировки данных из файла в формате:
    Заголовок - 4 байта
    Временная метка - 2 байта
    Ускорения по осям - 6 байт
    Угловые скорости по осям - 6 байт
    Температура - 2 байта
    Контрольная сумма - 1 байт
    """

    _Stages = Enum(
        value='STM_Stages',
        names=('WantHeader', 'WantPacketBody', 'WantConSum')
    )

    def __init__(self, filename: str):
        self._index = 0  # Индекс прочитанного символа в файле
        self._con_sum = 0  # Посчитанная контрольная сумма
        self._filename = filename  # Имя обрабатываемого файла
        self._file: BinaryIO = None  # Переменная для хранения файла

        with open(JSON_FILE, 'r') as json_file:
            json_data = json.load(json_file)["Decoder"]
            self._header = json_data["header"]
            self._titles = json_data["titles"]
            self._coefficients = json_data["value_coefficients"]

        self._received_data = {key: np.array([], dtype=float) for key in self._titles}
        self._supported_formats = (0xc8,)
        self._package_size = 0

    def get_data(self):
        return self._received_data

    def decoding(self):

        self._file = open(self._filename, "rb")
        max_size = os.path.getsize(self._filename)

        bytes_buffer = []  # Буфер для байтов, прочитанных из очереди данных

        Stages = self._Stages
        stage = Stages.WantHeader

        while self._index < (max_size - self._package_size - 4):
            val = self._read_bin()
            match stage:
                case Stages.WantHeader:
                    if val == self._header[0]:
                        if self._read_bin() == self._header[1]:
                            self._check_format(self._read_bin())
                            self._package_size = self._read_bin()
                            stage = Stages.WantPacketBody

                case Stages.WantPacketBody:
                    bytes_buffer.append(val)
                    for i in range(self._package_size - 1):
                        bytes_buffer.append(self._read_bin())

                    stage = Stages.WantConSum

                case Stages.WantConSum:
                    # Тк мы высчитываем сумму при каждом чтении байта, то необходимо вычесть значение последнего байта,
                    # который несёт в себе значение контрольной суммы
                    self._con_sum -= val
                    # Сравним полученную контрольную сумму с посчитанной
                    if (self._con_sum & 255) == val:
                        self._list_to_dict(bytes_buffer)
                    else:
                        print(f'\n#############\n'
                              f'Несовпадение контрольной суммы в пакете данных!\n'
                              f'Полученная КС = {val}, вычисленная КС = {self._con_sum} & 255 = {self._con_sum & 255}\n'
                              f'Данный пакет данных не будет обработан.\n'
                              f'#############\n')
                    stage = Stages.WantHeader
                    self._con_sum = 0
                    bytes_buffer = []

        self._file.close()

    @staticmethod
    def _mod_code(low_bit, high_bit):
        """
        Перевод числа high_bit << 8 + low_bit в модифицированном дополнительном коде в
        классическое с 15-ью значащими битами.
        :param low_bit: младшие 8 бит числа.
        :param high_bit: старшие 8 бит числа.
        :return: классическое знаковое число.
        """
        result = high_bit * 256 + low_bit
        sign_const = result >> 15
        if sign_const == 1:
            result &= 32767  # 32767 = 0111 1111 1111 1111
            # Обрежем старший бит
            result ^= 32767  # Инвертируем вс биты числа
            result *= -1

        return result

    def _read_bin(self):
        """
        Чтение бинарного числа в шестнадцатеричной системе исчисления.
        :param val: Шестнадцатеричное число.
        :return: Число в десятичной системе счисления.
        """
        try:
            res = int(binascii.hexlify(self._new_byte()), 16)
        except ValueError:
            # При достижении конца файла self._new_byte() вернёт b''.
            # ValueError: invalid literal for int() with base 16: b''
            raise EOFError

        self._index += 1
        self._con_sum += res
        return res

    def _new_byte(self):
        try:
            return self._file.read(1)
        except Exception as error:
            print(f'Error: {error}')
            return None

    def _check_format(self, package_format):
        if package_format not in self._supported_formats:
            raise RuntimeError(f"Unsupported package format: format {package_format} not in {self._supported_formats}")

    def _list_to_dict(self, buffer_list: list[bytes]):
        buffer_index = 0
        for i in range(len(self._titles)):

            if buffer_index > self._package_size:
                raise RuntimeError(f'Unsupported package size')

            key = self._titles[i]
            multiplier = self._coefficients[i]

            self._received_data[key] = np.append(
                self._received_data[key],
                self._mod_code(buffer_list[buffer_index], buffer_list[buffer_index + 1]) * multiplier
            )

            buffer_index += 2
