# System imports
from typing import Optional

# External imports
import numpy as np

# User imports
from dev.data_analys.math_tools.vector_3d import Vector

##########################################################

class TrajectoryCalculator:
    """
    Класс для расчёта траектории по ускорениям движения в навигационной системе.

    Шаги расчёта:
      - интегрирование ускорений для получения скоростей
      - корректировка скорости из предположения полной остановки в конце проезда
      - интегрирование скорости для получения перемещения
      - корректировка перемещения по априорной информации
    """

    def __init__(self, time: np.typing.NDArray[np.floating], a_motion_nav: np.typing.NDArray[Vector], p_end: Vector):
        self._time = time
        self._a_motion_nav = a_motion_nav
        self._p_end = p_end

    def compute_trajectory(self) -> tuple[np.ndarray, np.ndarray]:
        # Интегрирование ускорений для расчёта скорости движения
        v: np.typing.NDArray[Vector] = self._integration(self._time, self._a_motion_nav)

        # Корректировка скорости из предположения полной остановки в конце проезда
        v = self._correct_by_endpoint(self._time, v, Vector([0, 0, 0]))

        # Интегрирование скорректированной скорости для расчёта перемещения
        p = self._integration(self._time, v)

        # Корректировка перемещения по априорной информации
        p = self._correct_by_endpoint(self._time, p, self._p_end)

        return v, p

    @staticmethod
    def _integration(time: np.typing.NDArray[np.floating],
                     vectors: np.typing.NDArray[Vector]) -> np.ndarray:

        if len(time) != len(vectors):
            raise RuntimeError('Переданны массивы разной длины!\n'
                               f'len(time) = {len(time)}; len(vectors) = {len(vectors)}')

        N = len(time)

        # Преобразуем массив векторов в np.array для удобства вычислений
        vec_np = np.array([v.to_list() for v in vectors], dtype=float)

        # Проинтегрируем переданный массив методом трапеции
        res_np = np.zeros((N, 3), dtype=float)
        for i in range(1, N):
            res_np[i] = res_np[i-1] + (vec_np[i-1] + vec_np[i]) * 0.5 * (time[i] - time[i-1])

        return np.array([Vector(res_np[i].tolist()) for i in range(N)])

    @staticmethod
    def _correct_by_endpoint(time: np.typing.NDArray[np.floating],
                             vectors: np.typing.NDArray[Vector],
                             end_value: Vector) -> np.ndarray:

        if len(time) != len(vectors):
            raise RuntimeError('Переданны массивы разной длины!\n'
                               f'len(time) = {len(time)}; len(vectors) = {len(vectors)}')

        N = len(time)
        v_np = np.array([v.to_list() for v in vectors], dtype=float)
        v_end_np = np.array(end_value.to_list())

        T = time[-1] - time[0]

        # Ошибка в конце
        v_err = v_np[-1] - v_end_np

        # Линейная интерполяция ошибки по времени
        v_corr_np = np.zeros_like(v_np)
        for i in range(N):
            v_corr_np[i] = v_np[i] - v_err * (time[i] - time[0]) / T

        return np.array([Vector(v_corr_np[i].tolist()) for i in range(N)])
