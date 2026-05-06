# -*- coding: utf-8 -*-
"""Модуль конфигурации главного окна.

Содержит модель `MainWindowConfig` для настройки параметров
главного окна графического интерфейса программы.
"""

# System imports
from typing import Dict, Any

# External imports
from pydantic import BaseModel, Field, field_validator

# User imports

#############################################

class MainWindowConfig(BaseModel):
    """Настройки параметров главного окна.

    Attributes:
        pen_params (dict[int, dict[str, Union[str, float]]]): Параметры пера
            для каждого датчика. Ключ – ID датчика, значение – словарь с полями:
                color (str): цвет линии (HEX или название),
                width (float): толщина линии.
    """

    pen_params: Dict[int, Dict[str, Any]] = Field(
        default_factory=lambda: {
            1: {"color": "#ff003b", "width": 2.5},
            2: {"color": "#ff4400", "width": 2.5},
        },
        description="Параметры отрисовки линий графика для каждого датчика"
    )