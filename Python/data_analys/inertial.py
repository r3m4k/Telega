"""Инерциальная обработка: ориентация, Earth rate и ускорение в ENU."""

# System imports
from dataclasses import dataclass

# External imports
import numpy as np

# User imports
from .math_tools import Quaternion, Vector
from .models import InitializationResult

##########################################################


@dataclass
class InertialOutput:
    """Выход инерциальной части алгоритма для одного проезда."""

    acceleration_nav: list[Vector]
    quaternions: list[Quaternion]

##########################################################


def process_inertial_data(
    time: np.ndarray,
    acc_data: list[Vector],
    gyro_data_rad_s: list[Vector],
    initialization: InitializationResult,
) -> InertialOutput:
    """Считает кватернионы и линейные ускорения в навигационной системе."""

    if not (len(time) == len(acc_data) == len(gyro_data_rad_s)):
        raise ValueError("time, acc_data, and gyro_data_rad_s must have the same length")
    if len(time) == 0:
        return InertialOutput(acceleration_nav=[], quaternions=[])

    q_current = initialization.q_body_to_nav.copy()
    q_current.normalize()

    acceleration_nav: list[Vector] = []
    quaternions: list[Quaternion] = []

    for index in range(len(time)):
        quaternions.append(q_current.copy())

        acc_corrected = acc_data[index] - initialization.bias_acc
        acc_nav = q_current.rotate_vector(acc_corrected)
        acceleration_nav.append(acc_nav - initialization.gravity_nav)

        if index == len(time) - 1:
            continue

        dt = float(time[index + 1] - time[index])
        if dt < 0:
            raise ValueError("time must be monotonic non-decreasing")

        q_nav_to_body = q_current.conjugate()
        omega_earth_body = q_nav_to_body.rotate_vector(initialization.omega_earth_nav)
        omega_body = gyro_data_rad_s[index] - initialization.bias_gyro - omega_earth_body
        q_delta = Quaternion.from_gyro(omega_body, dt)
        q_current = q_delta * q_current
        q_current.normalize()

    return InertialOutput(acceleration_nav=acceleration_nav, quaternions=quaternions)
