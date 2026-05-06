# -*- coding: utf-8 -*-
"""Модуль конфигурации калибровки для пакета ADCAnalysis.

Содержит модель `CalibrationConfig` на основе Pydantic, которая определяет
настройки, используемые при загрузке калибровочных данных и создании
объектов калибровки датчиков.
"""

# System imports
from typing import Literal

# External imports
from pydantic import BaseModel, Field, field_validator

# User imports

#############################################

class CalibrationConfig(BaseModel):
    """Настройки калибровки датчиков.

    Определяет список идентификаторов датчиков, тип калибровки и тип загрузчика данных.

    Attributes:
        sensor_id_list (list[int]): Список идентификаторов датчиков, для которых
            будут создаваться объекты калибровки. По умолчанию [1, 2].

        calibration_type (str): Тип калибровки.

        loader_type (str): Тип загрузчика калибровочных данных.
            Допустимые значения:
                - `'FooLinearLoader'` – отладочный генератор линейной зависимости.
                - `'CalibrationDataLoader'` – загрузчик из файла (в разработке).

    Raises:
        ValidationError: Если список датчиков пуст или указан неподдерживаемый тип.
    """

    sensor_id_list: list[int] = Field(
        default=[1, 2],
        description="Список идентификаторов датчиков"
    )

    calibration_type: Literal['CubicSplineCalibration'] = Field(
        default='CubicSplineCalibration',
        description="Тип калибровки"
    )

    loader_type: Literal['FooLinearLoader', 'CalibrationDataLoader'] = Field(
        default='FooLinearLoader',
        description="Тип загрузчика данных"
    )

    @field_validator('sensor_id_list')
    @classmethod
    def not_empty(cls, v: list[int]) -> list[int]:
        """Проверка списка датчиков."""
        if not v:
            raise ValueError('Список датчиков не может быть пустым')
        return v