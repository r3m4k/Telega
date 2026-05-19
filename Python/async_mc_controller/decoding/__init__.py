# -*- coding: utf-8 -*-
"""Пакет для декодирования данных от IMU.

Пакет предоставляет набор классов для приёма байтового потока, выделения пакетов,
проверки контрольной суммы и преобразования сырых данных в структурированные объекты
(данные IMU или команды).

Доступные модули и классы:
    - decoder_protocol.DecoderProtocol: Протокол декодера.
    - base_decoder.BaseDecoder:         Базовый класс декодера.
    - imu_decoder.ImuDecoder:           Основной класс-декодер с конечным автоматом.
    - imu_data_description.ImuData:     Класс для хранения распакованных данных датчика.
"""

__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from async_mc_controller.decoding.base_decoder import BaseDecoder
from async_mc_controller.decoding.device_decoder import DeviceDecoder
from async_mc_controller.decoding.common_data_description import TriaxialData
from async_mc_controller.decoding.utils import (
    bytes_to_uint32,
    bytes_to_int32,
    bytes_to_uint8,
    bytes_to_triaxial,
    bytes_to_float,
)


# --------------------------------------------------------

__all__ = [
    'BaseDecoder',
    'DeviceDecoder',
    'TriaxialData',
    'bytes_to_uint32',
    'bytes_to_int32',
    'bytes_to_uint8',
    'bytes_to_triaxial',
    'bytes_to_float',
]

# --------------------------------------------------------