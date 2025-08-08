# System imports
import os
import json
from enum import Enum
import binascii
from typing import BinaryIO, Tuple, Sequence, Union, cast, Any
from pprint import pprint

# External imports
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes

# User imports
from consts import CWD, JSON_FILE, color_scheme
import filterpy.kalman
import filterpy.common
from plotting import *


##########################################################

def name_of_file(path, extension):
    """
    Получение название файла из его абсолютного или относительного пути без его расширения.
    :param path: Путь к файлу.
    :param extension: Расширение файла. Пример: ".log".
    :return: Имя файла без расширения и пути расположения.
    """
    file = path
    for i in range(0, file.count('/')):
        file = file[file.find('/') + 1:]

    return file[:file.find(extension)]

def integration(x_value, y_value):
    """
    Интегрирование с помощью метода трапеции.
    """

    result = 0
    integrated_array = np.zeros_like(x_value)

    for index in range(len(x_value) - 1):
        result += (x_value[index + 1] - x_value[index]) * (y_value[index] + y_value[index + 1]) / 2
        integrated_array[index + 1] = result

    return integrated_array

# Интегрирование с помощью метода трапеций
def trapezoid_integration(array, h):
    return np.sum(array[:-1] + array[1:]) * h / 2

def linear_subtraction(array: np.typing.NDArray, final_value: float):
    """
    Вычитание линейного сдвига
    """
    line_coefficient = (array[-1] - final_value) / len(array)
    return array - line_coefficient * np.arange(len(array))


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


##########################################################

class KalmanFilter:
    """
    Класс для фильтрации данных с помощью фильтра Калмана
    """

    def __init__(self, data: np.typing.NDArray, initial_state: float):
        self._data = data
        self._initial_state = initial_state
        self._filtered_data: np.typing.NDArray = None

    def get_filtered_data(self):
        self._filtering()
        return self._filtered_data

    def _filtering(self):
        # Создаём объект KalmanFilter
        flt = filterpy.kalman.KalmanFilter(dim_x=1,  # Размер вектора состояния
                                           dim_z=1)  # Размер вектора измерений

        processNoise = 1e-4  # Погрешность модели
        measurementSigma = np.std(self._data)  # Среднеквадратичное отклонение

        # F - матрица процесса - размер dim_x на dim_x - 1х1
        flt.F = np.array([[1.0]])

        # Матрица наблюдения - dim_z на dim_x - 1x1
        flt.H = np.array([[1.0]])

        # Ковариационная матрица ошибки модели
        flt.Q = processNoise

        # Ковариационная матрица ошибки измерения - 1х1
        flt.R = np.array([[measurementSigma * measurementSigma]])

        # Начальное состояние.
        flt.x = np.array([self._initial_state])

        # Ковариационная матрица для начального состояния
        flt.P = np.array([[8.0]])

        filteredState = []
        # stateCovarianceHistory = []

        # Обработка данных
        for i in range(len(self._data)):
            z = [self._data[i]]  # Вектор измерений
            flt.predict()  # Этап предсказания
            flt.update(z)  # Этап коррекции

            filteredState.append(flt.x)
            # stateCovarianceHistory.append(flt.P)

        self._filtered_data = np.array(filteredState)
        # stateCovarianceHistory = np.array(stateCovarianceHistory)


class MyFilter:
    """
    Собственный фильтр. Его алгоритм:
    Берутся n_flt точек, они линейно аппроксимируются.
    И вместо старых данных записываются данные на этой прямой в той же точке.
    """
    def __init__(self, data: np.typing.NDArray[float], n_flt: int = 5):
        self._data = data
        self._n_flt = n_flt     # Лучше использовать нечётное число
        self._flt_data: np.typing.NDArray = np.zeros_like(self._data)

    def get_filtered_data(self):
        self._filtering_data()
        return self._flt_data

    def _filtering_data(self):
        index = 0   # Номер обрабатываемого индекса
        data = np.zeros_like(self._data)    # Массив сглаженных значений

        # Для начала сгладим первые n_flt // 2 точек
        line = np.polyfit(np.arange(index, index + self._n_flt + 1), self._data[index: index + self._n_flt + 1], deg=1)
        for index in range(self._n_flt // 2 + 1):
            data[index] = np.polyval(line, index)

        # Теперь сгладим точки с индексом от (n_flt // 2) до (len(self._data) - n_flt // 2 - 1)
        for index in range(self._n_flt // 2 + 1, len(self._data) - self._n_flt // 2):
            line = np.polyfit(np.arange(index - self._n_flt // 2, index + self._n_flt // 2 + 1),
                              self._data[index - self._n_flt // 2: index + self._n_flt // 2 + 1],
                              deg=1)
            data[index] = np.polyval(line, index)

        # В конце обработаем индексы от (len(self._data) - n_flt // 2 - 1) до конца
        for index in range(len(self._data) - self._n_flt // 2, len(self._data)):
            data[index] = np.polyval(line, index)

        self._flt_data = data


class Filter:
    """
    Класс для фильтрации данных
    """
    def __init__(self, data: np.typing.NDArray[float]):
        self._data = data

    def get_filtered_data(self):
        # return KalmanFilter(self._data, self._data[0]).get_filtered_data()
        return MyFilter(self._data, 15).get_filtered_data()

##########################################################

class RotatedValues:
    """
    Класс для перевода данных акселерометра из СК датчика в СК Земли.
    Параметры СК Земли: OX - на восток, OY - на север, OZ - вертикально вверх.
    """
    def __init__(self,
                 acc_dict: dict[str, np.typing.NDArray], acc_dict_buffer: dict[str, np.typing.NDArray],
                 gyro_dict: dict[str, np.typing.NDArray], gyro_dict_buffer: dict[str, np.typing.NDArray],
                 longitude: float):

        self._coords = ['X', 'Y', 'Z']
        dicts = [acc_dict, acc_dict_buffer, gyro_dict, gyro_dict_buffer]
        if not all(list(d.keys()) == self._coords for d in dicts):
            raise KeyError('Ключи в переданных словарях не совпадают с ["X", "Y", "Z"]')

        self._acc: dict[str, np.typing.NDArray] = acc_dict
        self._acc_buffer: dict[str, np.typing.NDArray] = acc_dict_buffer

        self._gyro: dict[str, np.typing.NDArray] = gyro_dict
        self._gyro_buffer: dict[str, np.typing.NDArray] = gyro_dict_buffer

        self._longitude: float = longitude      # Широта, на которой проводились измерения

        self._R_to_prev = np.eye(3)             # Матрица перехода к предыдущему состоянию
        self._R_to_Earth = np.eye(3)            # Матрица перехода из исходного состояния в СК Земли, в которой ось ОУ направлена на север

        self.R_det = []         # Список значений определителей матрицы перехода, нужен для контроля корректности алгоритма


    def _start(self):
        pass

    def _fill_R_to_Earth(self):
        """
        Заполнение матрицы self._R_to_Earth по данным из self._gyro_buffer. Подробнее см в документации
        """
        acc_buffer_mean: dict[str, float] = {coord: np.mean(self._acc_buffer[coord]) for coord in self._coords}
        gyro_buffer_mean: dict[str, float] = {coord: np.mean(self._gyro_buffer[coord]) for coord in self._coords}

        # Абсолютное значение ускорения свободного падения. Вектор имеет проекцию только на ось OZ
        G = np.sqrt(acc_buffer_mean['X']**2 + acc_buffer_mean['Y']**2 + acc_buffer_mean['Z']**2)

        # Абсолютное значение угловой скорости Земли. Вектор имеет проекции на ось OY - W_Y и на ось OZ - W_Z
        W = np.sqrt(gyro_buffer_mean['X']**2 + gyro_buffer_mean['Y']**2 + gyro_buffer_mean['Z']**2)
        W_Y = W * np.sin(self._longitude)
        W_Z = W * np.cos(self._longitude)

        # Вспомогательный вектор А, который является векторным произведением векторов G и W
        A: float = G * W * np.sin(self._longitude)

        # Найдём координаты вектора А в СК датчика
        a_x = gyro_buffer_mean['Y'] * acc_buffer_mean['Z'] - gyro_buffer_mean['Z'] * acc_buffer_mean['Y']
        a_y = gyro_buffer_mean['Z'] * acc_buffer_mean['X'] - gyro_buffer_mean['X'] * acc_buffer_mean['Z']
        a_z = gyro_buffer_mean['X'] * acc_buffer_mean['Y'] - gyro_buffer_mean['Y'] * acc_buffer_mean['X']

        # Заполним матрицу перехода по столбцам
        self._R_to_Earth[0, 0] = a_x / A
        self._R_to_Earth[1, 0] = a_y / A
        self._R_to_Earth[2, 0] = a_z / A

        self._R_to_Earth[0, 1] = (gyro_buffer_mean['X'] - W_Z * acc_buffer_mean['X'] / G) / W_Y
        self._R_to_Earth[1, 1] = (gyro_buffer_mean['Y'] - W_Z * acc_buffer_mean['Y'] / G) / W_Y
        self._R_to_Earth[2, 1] = (gyro_buffer_mean['Z'] - W_Z * acc_buffer_mean['Z'] / G) / W_Y

        self._R_to_Earth[0, 1] = acc_buffer_mean['X'] / G
        self._R_to_Earth[1, 1] = acc_buffer_mean['Y'] / G
        self._R_to_Earth[2, 1] = acc_buffer_mean['Z'] / G

        # Получили марицу перехода из СК Земли в СК датчика. Поэтому исходная матрица будет обратной к построенной
        self._R_to_Earth = np.linalg.inv(self._R_to_Earth)
        print(f'Матрица перехода из начального состояния в СК Земли построена. Её определитель равен = {np.linalg.det(self._R_to_Earth)}')

##########################################################
