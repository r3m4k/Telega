"""
Модуль с различными фильтрами данных
"""

# System imports
import os
from enum import Enum
import binascii
from typing import BinaryIO

# External imports
import numpy as np

# User imports
import filterpy.kalman
import filterpy.common

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

# --------------------------------------------------------

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

# --------------------------------------------------------

class Filter:
    """
    Класс для фильтрации данных
    """
    def __init__(self, data: np.typing.NDArray[float]):
        self._data = data

    def get_filtered_data(self):
        # return KalmanFilter(self._data, self._data[0]).get_filtered_data()
        return MyFilter(self._data, 15).get_filtered_data()

# --------------------------------------------------------
