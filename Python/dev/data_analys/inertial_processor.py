# System imports
from typing import Optional

# External imports
import numpy as np

# User imports
from dev.data_analys.math_tools.vector_3d import Vector
from dev.data_analys.math_tools import Quaternion

##########################################################

class InertialProcessor:
    """
    Обработчик инерциальных данных для путеизмерительной телеги.

    Выполняет:
      - Инициализацию по статическому буферу: определение bias акселерометра и гироскопа,
        начальной ориентации тела относительно навигационной системы (ENU) с учётом вращения Земли.
      - Циклическую обработку измерений: коррекция смещений, учёт Earth rate,
        обновление ориентации, перевод ускорений в навигационную систему и вычитание гравитации.

    Выход: массив ускорений движения в навигационной системе (a_motion_nav) для каждого момента времени.
    """

    def __init__(self, latitude_deg: float):
        """
        Параметры:
            latitude_deg: широта места проведения измерений в градусах.
        """
        self.lat = np.radians(latitude_deg)

        # Вектор угловой скорости вращения Земли в навигационной системе ENU
        self.omega_e = 7.292115e-5  # рад/с
        self.omega_earth_nav = Vector([
            0.0,
            self.omega_e * np.cos(self.lat),
            self.omega_e * np.sin(self.lat)
        ])

        # Вектор гравитации в навигационной системе
        self.g_nav = Vector([0.0, 0.0, 9.80665])

        # Параметры, определяемые при инициализации
        self.bias_acc: Optional[Vector] = None              # смещение акселерометра в теле
        self.bias_gyro: Optional[Vector] = None             # смещение гироскопа в теле
        self.q_body_to_nav: Optional[Quaternion] = None     # кватернион ориентации

    def initialize(self, acc_buffer: np.typing.NDArray[Vector], gyro_buffer: np.typing.NDArray[Vector]) -> None:
        """
        Инициализация по статическому буферу.

        Параметры:
            acc_buffer: массив объектов Vector (измерения акселерометра)
            gyro_buffer: массив объектов Vector (измерения гироскопа)
        """
        # Получим средние значения массивов
        acc_mean = np.mean(np.array([v.to_list() for v in acc_buffer], dtype=float), axis=0)
        gyro_mean = np.mean(np.array([v.to_list() for v in gyro_buffer], dtype=float), axis=0)

        # Получим абсолютные значения
        G = np.linalg.norm(acc_mean)
        W = np.linalg.norm(gyro_mean)

        W_Y = W * np.cos(self.lat)
        W_Z = W * np.sin(self.lat)
        A = G * W * np.sin(self.lat)

        a_vec = np.cross(gyro_mean, acc_mean)

        # Столбцы матрицы перехода из навигации в тело
        col0 = a_vec / A
        col1 = (gyro_mean - (W_Z / G) * acc_mean) / W_Y
        col2 = acc_mean / G

        R_nav_to_body = np.column_stack((col0, col1, col2))
        self.q_body_to_nav = Quaternion.from_matrix(R_nav_to_body).conjugate()
        self.q_body_to_nav.normalize()

        # Вычисляем bias гироскопа
        q_nav_to_body = self.q_body_to_nav.conjugate()
        omega_earth_body = q_nav_to_body.rotate_vector(self.omega_earth_nav)
        self.bias_gyro = Vector(gyro_mean.tolist()) - omega_earth_body

        # Вычисляем bias акселерометра
        g_body = q_nav_to_body.rotate_vector(self.g_nav)
        self.bias_acc = Vector(acc_mean.tolist()) - g_body

    def process(self,
                time: np.ndarray,
                acc_data: np.ndarray,
                gyro_data: np.ndarray) -> np.ndarray:
        """
        Обработка измерений за проезд.

        Параметры:
            time: одномерный массив временных меток.
            acc_data: массив объектов Vector длины N (акселерометр в теле).
            gyro_data: массив объектов Vector длины N (гироскоп в теле).

        Возвращает:
            Массив объектов Vector длины N — ускорения движения в навигационной системе.
        """
        if any(x is None for x in (self.bias_acc, self.bias_gyro, self.q_body_to_nav)):
            raise RuntimeError("Процессор не инициализирован. Вызовите initialize().")

        if not (isinstance(acc_data[0], Vector) and isinstance(gyro_data[0], Vector)):
            raise TypeError("Переданные массивы не соответствуют документации")

        N = len(time)
        if not (len(acc_data) == len(gyro_data) == N):
            raise ValueError("Размеры входных массивов не совпадают")

        a_motion_nav = np.empty(N, dtype=object)

        for i in range(N):
            acc: Vector = acc_data[i]
            gyro: Vector = gyro_data[i]

            # Коррекция гироскопа
            gyro_corrected = gyro - self.bias_gyro

            # Учёт вращения Земли
            q_nav_to_body = self.q_body_to_nav.conjugate()
            omega_earth_body = q_nav_to_body.rotate_vector(self.omega_earth_nav)
            omega_body = gyro_corrected - omega_earth_body

            if i != 0:
                # Обновление ориентации
                dt: float = time[i] - time[i-1]
                q_delta = Quaternion.from_gyro(omega_body, dt)
                self.q_body_to_nav = q_delta * self.q_body_to_nav
                self.q_body_to_nav.normalize()

            # Коррекция акселерометра и поворот в навигацию
            acc_corrected = acc - self.bias_acc
            a_nav = self.q_body_to_nav.rotate_vector(acc_corrected)
            a_motion_nav[i] = a_nav - self.g_nav

        return a_motion_nav