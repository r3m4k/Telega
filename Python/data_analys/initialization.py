"""Начальная выставка тележки по статическому буферу."""

# External imports
import numpy as np

# User imports
from .data_loader import vectors_to_array
from .math_tools import Quaternion, Vector
from .models import InitializationResult, ProcessingConfig

##########################################################


OMEGA_EARTH_RAD_S = 7.292115e-5

##########################################################


def initialize_from_static_buffer(
    acc_buffer: list[Vector],
    gyro_buffer_rad_s: list[Vector],
    config: ProcessingConfig,
) -> InitializationResult:
    """Вычисляет начальный кватернион и смещения датчиков по статике."""

    acc_mean = vectors_to_array(acc_buffer).mean(axis=0)
    gyro_mean = vectors_to_array(gyro_buffer_rad_s).mean(axis=0)

    gravity_nav = Vector([0.0, 0.0, config.gravity_acceleration])
    omega_earth_nav = earth_rotation_vector_enu(config.latitude_deg)

    q_body_to_nav = _initial_orientation_from_static_vectors(
        acc_mean=acc_mean,
        gyro_mean=gyro_mean,
        latitude_deg=config.latitude_deg,
    )

    q_nav_to_body = q_body_to_nav.conjugate()
    omega_earth_body = q_nav_to_body.rotate_vector(omega_earth_nav)
    gravity_body = q_nav_to_body.rotate_vector(gravity_nav)

    return InitializationResult(
        q_body_to_nav=q_body_to_nav,
        bias_acc=Vector(acc_mean) - gravity_body,
        bias_gyro=Vector(gyro_mean) - omega_earth_body,
        omega_earth_nav=omega_earth_nav,
        gravity_nav=gravity_nav,
    )


def earth_rotation_vector_enu(latitude_deg: float) -> Vector:
    """Возвращает вектор угловой скорости вращения Земли в ENU."""

    latitude_rad = np.radians(latitude_deg)
    return Vector(
        [
            0.0,
            OMEGA_EARTH_RAD_S * np.cos(latitude_rad),
            OMEGA_EARTH_RAD_S * np.sin(latitude_rad),
        ]
    )


##########################################################


def _initial_orientation_from_static_vectors(
    acc_mean: np.ndarray,
    gyro_mean: np.ndarray,
    latitude_deg: float,
) -> Quaternion:
    """Строит начальную ориентацию по векторам g и omega_earth в body."""

    latitude_rad = np.radians(latitude_deg)
    gravity_norm = np.linalg.norm(acc_mean)
    earth_rate_north = OMEGA_EARTH_RAD_S * np.cos(latitude_rad)
    cross_norm = gravity_norm * earth_rate_north

    if gravity_norm <= 0:
        raise ValueError("Static accelerometer norm must be positive")
    if abs(earth_rate_north) <= 0:
        raise ValueError("Earth-rate north projection is too small for alignment")

    cross_body = np.cross(gyro_mean, acc_mean)
    col_east = cross_body / cross_norm
    col_north = (
        gyro_mean
        - (OMEGA_EARTH_RAD_S * np.sin(latitude_rad) / gravity_norm) * acc_mean
    ) / earth_rate_north
    col_up = acc_mean / gravity_norm

    rotation_nav_to_body = np.column_stack((col_east, col_north, col_up))
    q_nav_to_body = Quaternion.from_matrix(rotation_nav_to_body)
    q_body_to_nav = q_nav_to_body.conjugate()
    q_body_to_nav.normalize()
    return q_body_to_nav
