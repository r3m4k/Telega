import numpy as np
import numpy.typing as npt
from dev.data_analys.math_tools import Vector

class TrajectoryCalculator:
    """
    Класс для расчёта траектории по ускорениям движения в навигационной системе.
    Выполняет двукратное интегрирование методом трапеций.
    Применяет коррекцию:
      - по конечной остановке (ZUPT) — обнуление скорости в конце,
      - по известным координатам конца — линейная коррекция положения.
    """

    def __init__(self):
        # Никаких параметров по умолчанию
        pass

    # --------------------------------------------------------------------------
    # Вспомогательные методы для преобразования типов
    # --------------------------------------------------------------------------
    def _vectors_to_numpy(self, vec_array: npt.NDArray[Vector]) -> np.ndarray:
        """
        Преобразует массив объектов Vector в numpy-массив формы (N,3).
        """
        return np.array([v.to_list() for v in vec_array], dtype=float)

    def _numpy_to_vectors(self, arr: np.ndarray) -> npt.NDArray[Vector]:
        """
        Преобразует numpy-массив формы (N,3) в массив объектов Vector.
        """
        N = arr.shape[0]
        result = np.empty(N, dtype=object)
        for i in range(N):
            result[i] = Vector(arr[i].tolist())
        return result

    # --------------------------------------------------------------------------
    # Основные методы расчёта
    # --------------------------------------------------------------------------
    def integrate(self,
                  time: npt.NDArray[float],
                  a_motion_nav: npt.NDArray[Vector],
                  v0: Vector = None,
                  p0: Vector = None) -> tuple[npt.NDArray[Vector], npt.NDArray[Vector]]:
        """
        Интегрирование ускорения для получения скорости и положения.

        Параметры:
            time: массив временных меток длины N.
            a_motion_nav: массив ускорений движения (объекты Vector) длины N.
            v0: начальная скорость (Vector). Если None, принимается (0,0,0).
            p0: начальное положение (Vector). Если None, принимается (0,0,0).

        Возвращает:
            v, p: массивы скорости и положения (объекты Vector) длины N.
        """
        N = len(time)
        if v0 is None:
            v0 = Vector([0.0, 0.0, 0.0])
        if p0 is None:
            p0 = Vector([0.0, 0.0, 0.0])

        # Преобразуем входные данные в numpy для удобства
        a_np = self._vectors_to_numpy(a_motion_nav)
        v_np = np.zeros((N, 3), dtype=float)
        p_np = np.zeros((N, 3), dtype=float)

        v_np[0] = np.array(v0.to_list())
        p_np[0] = np.array(p0.to_list())

        for i in range(1, N):
            dt = time[i] - time[i-1]
            # Скорость методом трапеций
            v_np[i] = v_np[i-1] + (a_np[i-1] + a_np[i]) * 0.5 * dt
            # Положение методом трапеций от скорости
            p_np[i] = p_np[i-1] + (v_np[i-1] + v_np[i]) * 0.5 * dt

        # Преобразуем обратно в Vector
        v = self._numpy_to_vectors(v_np)
        p = self._numpy_to_vectors(p_np)
        return v, p

    def correct_by_endpoint(self,
                            time: npt.NDArray[float],
                            v: npt.NDArray[Vector],
                            p: npt.NDArray[Vector],
                            p_end_real: Vector,
                            v_end_real: Vector = None) -> tuple[npt.NDArray[Vector], npt.NDArray[Vector]]:
        """
        Коррекция скорости и положения по известным конечным условиям.
        Предполагается, что в конце проезда телега остановлена, поэтому v_end_real обычно (0,0,0).
        Коррекция выполняется линейно по времени.

        Параметры:
            time: массив времени.
            v, p: рассчитанные скорость и положение (массивы Vector).
            p_end_real: известное конечное положение (Vector).
            v_end_real: известная конечная скорость (Vector). По умолчанию (0,0,0).

        Возвращает:
            v_corrected, p_corrected — скорректированные массивы Vector.
        """
        if v_end_real is None:
            v_end_real = Vector([0.0, 0.0, 0.0])

        # Преобразуем в numpy
        v_np = self._vectors_to_numpy(v)
        p_np = self._vectors_to_numpy(p)
        v_end_np = np.array(v_end_real.to_list())
        p_end_np = np.array(p_end_real.to_list())

        T = time[-1] - time[0]
        if T == 0:
            return v, p

        # Ошибка в конце
        v_err = v_np[-1] - v_end_np
        p_err = p_np[-1] - p_end_np

        # Линейная интерполяция ошибки
        alpha = (time - time[0]) / T
        v_corr_np = v_np - np.outer(alpha, v_err)
        p_corr_np = p_np - np.outer(alpha, p_err)

        # Преобразуем обратно в Vector
        v_corr = self._numpy_to_vectors(v_corr_np)
        p_corr = self._numpy_to_vectors(p_corr_np)
        return v_corr, p_corr

    def detect_stops(self,
                     a_motion_nav: npt.NDArray[Vector],
                     threshold: float = 0.05,
                     window: int = 5) -> np.ndarray:
        """
        Детектор остановок на основе скользящей дисперсии модуля ускорения.

        Параметры:
            a_motion_nav: массив ускорений движения (объекты Vector).
            threshold: максимальное СКО модуля ускорения, при котором считается остановка.
            window: размер окна в отсчётах (нечётный для симметрии).

        Возвращает:
            Булев массив длины N, True для моментов, относящихся к остановке.
        """
        a_np = self._vectors_to_numpy(a_motion_nav)
        acc_mag = np.linalg.norm(a_np, axis=1)
        N = len(acc_mag)
        mask = np.zeros(N, dtype=bool)

        # Полуокно
        half = window // 2
        for i in range(N):
            left = max(0, i - half)
            right = min(N, i + half + 1)
            if np.std(acc_mag[left:right]) < threshold:
                mask[i] = True
        return mask

    def correct_by_zupt(self,
                        time: npt.NDArray[float],
                        v: npt.NDArray[Vector],
                        p: npt.NDArray[Vector],
                        stop_mask: np.ndarray) -> tuple[npt.NDArray[Vector], npt.NDArray[Vector]]:
        """
        Коррекция скорости на участках остановок (принудительное обнуление скорости)
        и пересчёт положения.

        Параметры:
            time: массив времени.
            v, p: рассчитанные скорость и положение (массивы Vector).
            stop_mask: булев массив, True для моментов остановки.

        Возвращает:
            v_corrected, p_corrected — скорректированные массивы Vector.
        """
        v_np = self._vectors_to_numpy(v)
        p_np = self._vectors_to_numpy(p)

        # Обнуляем скорость на остановках
        v_corr_np = v_np.copy()
        v_corr_np[stop_mask] = 0.0

        # Пересчитываем положение с новой скоростью
        p_corr_np = np.zeros_like(p_np)
        p_corr_np[0] = p_np[0]
        for i in range(1, len(time)):
            dt = time[i] - time[i-1]
            p_corr_np[i] = p_corr_np[i-1] + (v_corr_np[i-1] + v_corr_np[i]) * 0.5 * dt

        v_corr = self._numpy_to_vectors(v_corr_np)
        p_corr = self._numpy_to_vectors(p_corr_np)
        return v_corr, p_corr

    def compute(self,
                time: npt.NDArray[float],
                a_motion_nav: npt.NDArray[Vector],
                p_start: Vector,
                p_end: Vector,
                v_start: Vector = None,
                v_end: Vector = None,
                zupt_threshold: float = None,
                zupt_window: int = 5) -> tuple[npt.NDArray[Vector], npt.NDArray[Vector]]:
        """
        Полный расчёт траектории с коррекцией.

        Параметры:
            time: массив времени длины N.
            a_motion_nav: массив ускорений движения (объекты Vector) длины N.
            p_start: начальное положение (Vector).
            p_end: конечное положение (Vector).
            v_start: начальная скорость (Vector). Если None, принимается (0,0,0).
            v_end: конечная скорость (Vector). Если None, принимается (0,0,0).
            zupt_threshold: если задан, включает детектор остановок с данным порогом.
            zupt_window: размер окна для детектора.

        Возвращает:
            v, p — скорректированные скорость и положение (массивы Vector).
        """
        # Интегрирование
        v, p = self.integrate(time, a_motion_nav, v0=v_start, p0=p_start)

        # Если включен ZUPT
        if zupt_threshold is not None:
            stop_mask = self.detect_stops(a_motion_nav, threshold=zupt_threshold, window=zupt_window)
            v, p = self.correct_by_zupt(time, v, p, stop_mask)

        # Коррекция по конечным условиям
        v_corr, p_corr = self.correct_by_endpoint(time, v, p, p_end, v_end)
        return v_corr, p_corr