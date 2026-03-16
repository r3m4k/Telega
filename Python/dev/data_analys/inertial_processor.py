# System imports
from typing import Union

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

        # Вектор угловой скорости вращения Земли в навигационной системе ENU.
        self.omega_e = 7.292115e-5
        self.omega_earth_nav = Vector([
            0.0,
            self.omega_e * np.cos(self.lat),
            self.omega_e * np.sin(self.lat)
        ])

        # Вектор гравитации в навигационной системе.
        self.g_nav = Vector([0.0, 0.0, 9.80665])

        # Параметры, которые будут определены при инициализации
        self.bias_acc: Union[Vector | None] = None           # смещение акселерометра в теле (постоянное)
        self.bias_gyro: Union[Vector | None] = None          # смещение гироскопа в теле (постоянное)
        self.q_body_to_nav: Union[Quaternion | None] = None  # кватернион ориентации тела относительно ENU СК

    def initialize(self, acc_buffer: np.typing.NDArray[Vector], gyro_buffer: np.typing.NDArray[Vector]) -> None:
        """
        Инициализация по статическому буферу, который записан перед началом проезда.

        Параметры:
            acc_buffer: массив объектов Vector длины N с измерениями акселерометра за буфер.
            gyro_buffer: массив объектов Vector длины M с измерениями гироскопа за буфер.

        Метод вычисляет:
            - bias_acc = среднее(acc_buffer) - проекция гравитации на тело в начальный момент.
            - bias_gyro = среднее(gyro_buffer) - проекция Earth rate на тело.
            - начальный кватернион q_body_to_nav, переводящий из первоначальной СК в глобальную СК.
        """
        # Преобразуем массивы объектов Vector в numpy-массивы чисел формы (N,3)
        acc_np = np.array([v.to_list() for v in acc_buffer], dtype=float)
        gyro_np = np.array([v.to_list() for v in gyro_buffer], dtype=float)

        # Усредняем буферы
        acc_mean = np.mean(acc_np, axis=0)
        gyro_mean = np.mean(gyro_np, axis=0)

        G = np.linalg.norm(acc_mean)    # Норма измеренного ускорения
        W = np.linalg.norm(gyro_mean)   # Норма измеренной угловой скорости

        # Вычисляем вспомогательные величины
        sin_lat = np.sin(self.lat)
        cos_lat = np.cos(self.lat)

        W_Y = W * cos_lat   # северная компонента Earth rate (в теле)
        W_Z = W * sin_lat   # вертикальная компонента Earth rate (в теле)

        # Вспомогательный вектор А, который является векторным произведением векторов G и W
        A = G * W * sin_lat

        # Вектор a = cross(gyro_mean, acc_mean)
        a_vec = np.cross(gyro_mean, acc_mean)

        # Столбцы матрицы перехода из тела в навигацию (R_body_to_nav)
        col0 = a_vec / A
        col1 = (gyro_mean - (W_Z / G) * acc_mean) / W_Y
        col2 = acc_mean / G

        # Составляем матрицу 3x3
        R_body_to_nav = np.column_stack((col0, col1, col2))

        # Преобразуем матрицу в кватернион
        self.q_body_to_nav = Quaternion.from_matrix(R_body_to_nav)

        # Теперь вычислим bias_gyro: из измеренного среднего вычтем проекцию Earth rate на оси тела
        # Проекция Earth rate на тело: omega_earth_body = q_body_to_nav.conjugate().rotate_vector(self.omega_earth_nav)
        q_nav_to_body = self.q_body_to_nav.conjugate()
        omega_earth_body = q_nav_to_body.rotate_vector(self.omega_earth_nav)  # возвращает Vector

        # Преобразуем Vector в numpy для вычитания
        omega_earth_body_np = np.array(omega_earth_body.to_list())
        self.bias_gyro = gyro_mean - omega_earth_body_np

        # Для акселерометра: g_body = проекция g_nav на тело
        g_body_vec = q_nav_to_body.rotate_vector(self.g_nav)  # Vector
        g_body_np = np.array(g_body_vec.to_list())
        self.bias_acc = acc_mean - g_body_np

    def process(self,
                time: np.typing.NDArray[float],
                acc_data: np.typing.NDArray[Vector],
                gyro_data: np.typing.NDArray[Vector]) -> np.typing.NDArray[Vector]:
        """
        Обработка массива измерений за проезд.

        Параметры:
            time: одномерный массив временных меток (в секундах) длины N.
            acc_data: массив объектов Vector длины N с измерениями акселерометра (в теле).
            gyro_data: массив объектов Vector длины N с измерениями гироскопа (в теле).

        Возвращает:
            a_motion_nav: массив объектов Vector длины N с ускорениями движения
                          в навигационной системе (уже без гравитации и bias).
        """
        if self.bias_acc is None or self.bias_gyro is None or self.q_body_to_nav is None:
            raise RuntimeError("Процессор не инициализирован. Вызовите initialize() сначала.")

        N = len(time)
        if len(acc_data) != N or len(gyro_data) != N:
            raise ValueError("Длины входных массивов time, acc_data и gyro_data должны совпадать.")

        # Выходной массив объектов Vector
        a_motion_nav = np.empty(N, dtype=Vector)

        # Копируем текущий кватернион для обновления
        q = self.q_body_to_nav.copy()

        # Преобразуем g_nav в numpy для вычитания (один раз)
        g_nav_np = np.array(self.g_nav.to_list())

        for i in range(N):
            # Преобразуем текущие измерения из Vector в numpy
            acc = np.array(acc_data[i].to_list())
            gyro = np.array(gyro_data[i].to_list())

            # 1. Коррекция гироскопа: вычитаем bias
            gyro_corrected = gyro - self.bias_gyro

            # 2. Проекция Earth rate на оси тела в текущей ориентации
            q_nav_to_body = q.conjugate()
            omega_earth_body_vec = q_nav_to_body.rotate_vector(self.omega_earth_nav)  # Vector
            omega_earth_body_np = np.array(omega_earth_body_vec.to_list())

            # 3. Угловая скорость тела относительно навигационной системы
            omega_body_nav = gyro_corrected - omega_earth_body_np

            # 4. Обновление ориентации (кроме последнего отсчёта)
            if i < N - 1:
                dt = time[i+1] - time[i]
                # Кватернион приращения (постоянная угловая скорость на интервале)
                q_delta = Quaternion.from_gyro(omega_body_nav, dt)
                # Обновляем глобальный кватернион: новый = q_delta * старый
                q = q_delta * q

            # 5. Коррекция акселерометра: вычитаем bias
            acc_corrected = acc - self.bias_acc

            # 6. Перевод ускорения в навигационную систему
            a_nav = q.rotate_vector(acc_corrected)  # возвращает numpy, т.к. acc_corrected - numpy

            # 7. Вычитание гравитации, получаем ускорение движения
            a_motion = a_nav - g_nav_np

            # Сохраняем результат как объект Vector
            a_motion_nav[i] = Vector(a_motion.tolist())

        return a_motion_nav