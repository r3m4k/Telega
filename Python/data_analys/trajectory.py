"""Расчет скорости и перемещения по ускорениям в ENU."""

# External imports
import numpy as np

# User imports
from .data_loader import array_to_vectors, vectors_to_array
from .math_tools import Vector

##########################################################


def compute_trajectory(
    time: np.ndarray,
    acceleration_nav: list[Vector],
    p_end: Vector,
) -> tuple[list[Vector], list[Vector]]:
    """Вычисляет скорость и перемещение с коррекцией конечных условий."""

    velocity = integrate_vectors(time, acceleration_nav)
    velocity = correct_by_endpoint(time, velocity, Vector([0.0, 0.0, 0.0]))
    position = integrate_vectors(time, velocity)
    position = correct_by_endpoint(time, position, p_end)
    return velocity, position


def integrate_vectors(time: np.ndarray, vectors: list[Vector]) -> list[Vector]:
    """Интегрирует массив векторов методом трапеций."""

    if len(time) != len(vectors):
        raise ValueError("time and vectors must have the same length")
    if len(time) == 0:
        return []

    values = vectors_to_array(vectors)
    result = np.zeros_like(values, dtype=float)
    for index in range(1, len(time)):
        dt = float(time[index] - time[index - 1])
        if dt < 0:
            raise ValueError("time must be monotonic non-decreasing")
        result[index] = result[index - 1] + 0.5 * (values[index - 1] + values[index]) * dt
    return array_to_vectors(result)


def correct_by_endpoint(
    time: np.ndarray,
    vectors: list[Vector],
    end_value: Vector,
) -> list[Vector]:
    """Линейно корректирует накопленную ошибку по известному концу."""

    if len(time) != len(vectors):
        raise ValueError("time and vectors must have the same length")
    if len(time) == 0:
        return []

    duration = float(time[-1] - time[0])
    if duration <= 0:
        return vectors.copy()

    values = vectors_to_array(vectors)
    end = end_value.to_numpy()
    error = values[-1] - end
    scale = ((time - time[0]) / duration).reshape(-1, 1)
    corrected = values - error * scale
    return array_to_vectors(corrected)
