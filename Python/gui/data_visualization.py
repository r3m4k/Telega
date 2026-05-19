# -*- coding: utf-8 -*-
"""Модуль отображения пакетов данных тележки в GUI."""

# External imports
from PyQt5.QtWidgets import QLCDNumber

# User imports
from telega_session import TelegaData

##########################################################


class DataVisualizer:
    """Отображение пакетов TelegaData в LCD-индикаторах."""

    def __init__(self,
                 value_acc_x: QLCDNumber,
                 value_acc_y: QLCDNumber,
                 value_acc_z: QLCDNumber,
                 value_gyro_x: QLCDNumber,
                 value_gyro_y: QLCDNumber,
                 value_gyro_z: QLCDNumber,
                 dpp_code_value: QLCDNumber):
        """Инициализирует визуализатор LCD-индикаторами."""
        super().__init__()

        widgets = {
            "value_acc_x": value_acc_x,
            "value_acc_y": value_acc_y,
            "value_acc_z": value_acc_z,
            "value_gyro_x": value_gyro_x,
            "value_gyro_y": value_gyro_y,
            "value_gyro_z": value_gyro_z,
            "dpp_code_value": dpp_code_value,
        }
        invalid_widgets = {
            name: type(widget)
            for name, widget in widgets.items()
            if not isinstance(widget, QLCDNumber)
        }
        if invalid_widgets:
            raise TypeError(
                "Ожидаются виджеты QLCDNumber. "
                f"Получены некорректные виджеты: {invalid_widgets}"
            )

        self._value_acc_x: QLCDNumber = value_acc_x
        self._value_acc_y: QLCDNumber = value_acc_y
        self._value_acc_z: QLCDNumber = value_acc_z
        self._value_gyro_x: QLCDNumber = value_gyro_x
        self._value_gyro_y: QLCDNumber = value_gyro_y
        self._value_gyro_z: QLCDNumber = value_gyro_z
        self._dpp_code_value: QLCDNumber = dpp_code_value

    def reset(self) -> None:
        """Сбрасывает отображаемые значения."""
        self._value_acc_x.display(0)
        self._value_acc_y.display(0)
        self._value_acc_z.display(0)

        self._value_gyro_x.display(0)
        self._value_gyro_y.display(0)
        self._value_gyro_z.display(0)

        self._dpp_code_value.display(0)

    def visualize_package(self, package: TelegaData) -> None:
        """Отображает полученный пакет данных."""
        if not isinstance(package, TelegaData):
            raise TypeError(f"Ожидается package типа TelegaData, получен {type(package)}")

        self._value_acc_x.display(package.acc.x_coord)
        self._value_acc_y.display(package.acc.y_coord)
        self._value_acc_z.display(package.acc.z_coord)

        self._value_gyro_x.display(package.gyro.x_coord)
        self._value_gyro_y.display(package.gyro.y_coord)
        self._value_gyro_z.display(package.gyro.z_coord)

        self._dpp_code_value.display(package.dpp_code)
