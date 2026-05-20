"""Простой трехмерный вектор для наглядной записи алгоритма."""

# System imports
from collections.abc import Iterable
from typing import Union

# External imports
import numpy as np

##########################################################


class Vector:
    """
    Класс, предназначенный для работы с вектором, имеющий три компоненты
    """
    def __init__(self, coords: Iterable[Union[np.floating, float]]):
        coords = list(coords)
        if len(coords) != 3:
            raise RuntimeError('Incorrect dimension of the vector.'
                               f'The Vector type have 3 dimensions, but given {len(coords)}')

        self._X_coord: float = float(coords[0])
        self._Y_coord: float = float(coords[1])
        self._Z_coord: float = float(coords[2])

    # -------------------------------
    # Математические операции
    # -------------------------------
    @property
    def norm(self):
        return np.sqrt(self._X_coord**2 + self._Y_coord**2 + self._Z_coord**2)

    # -------------------------------
    # Математические операторы
    # -------------------------------
    def __add__(self, other):
        if isinstance(other, Vector):
            return Vector([
                self._X_coord + other._X_coord,
                self._Y_coord + other._Y_coord,
                self._Z_coord + other._Z_coord
            ])
        else:
            raise ValueError('Both terms must be Vector')

    def __iadd__(self, other):
        if isinstance(other, Vector):
            self._X_coord += other._X_coord
            self._Y_coord += other._Y_coord
            self._Z_coord += other._Z_coord

            return self

        else:
            raise ValueError('Term must be Vector')

    def __sub__(self, other):
        if isinstance(other, Vector):
            return Vector([
                self._X_coord - other._X_coord,
                self._Y_coord - other._Y_coord,
                self._Z_coord - other._Z_coord
            ])
        else:
            raise ValueError('Reduced and subtracted must be Vector')

    def __isub__(self, other):
        if isinstance(other, Vector):
            self._X_coord -= other._X_coord
            self._Y_coord -= other._Y_coord
            self._Z_coord -= other._Z_coord

            return self
        else:
            raise ValueError('Term must be Vector')

    def __mul__(self, multiplier):
        try:
            _multiplier = float(multiplier)
        except ValueError:
            raise ValueError('The multiplier cannot be converted to the float type')

        return Vector([
            self._X_coord * _multiplier,
            self._Y_coord * _multiplier,
            self._Z_coord * _multiplier
        ])

    __rmul__ = __mul__

    def __imul__(self, multiplier):
        try:
            _multiplier = float(multiplier)
        except ValueError:
            raise ValueError('The multiplier cannot be converted to the float type')

        self._X_coord *= _multiplier
        self._Y_coord *= _multiplier
        self._Z_coord *= _multiplier

        return self

    def __truediv__(self, divisor):
        """
        Реализует истинное деление вектора на скаляр (/).
        """
        try:
            _divisor = float(divisor)
        except ValueError:
            raise ValueError('The divisor cannot be converted to the float type')

        if _divisor == 0:
            raise ZeroDivisionError('Division by zero')

        return Vector([
            self._X_coord / _divisor,
            self._Y_coord / _divisor,
            self._Z_coord / _divisor
        ])

    # -------------------------------
    # Работа с коллекциями
    # -------------------------------
    def __len__(self):
        return 3

    def __getitem__(self, item: Union[int, str]):
        if isinstance(item, int):
            return self.to_list()[item]

        elif isinstance(item, str):
            return  self.to_dict()[item]

        else:
            raise KeyError('Vector supports __getitem__ with int or str')

    def __setitem__(self, key, value):
        if isinstance(key, int):
            match key:
                case 0:
                    self._X_coord = value
                case 1:
                    self._Y_coord = value
                case 2:
                    self._Z_coord = value

                case _:
                    raise ValueError('Wrong index. Index must be in [0, 1, 2]')

        elif isinstance(key, str):
            match key:
                case 'X':
                    self._X_coord = value
                case 'Y':
                    self._Y_coord = value
                case 'Z':
                    self._Z_coord = value

                case _:
                    raise ValueError('Wrong key. Key must be in ["X", "Y", "Z"]')

        else:
            raise KeyError('Vector supports __setitem__ with int or str')

    def __str__(self):
        return f"X_coord = {round(self._X_coord, 6)}, Y_coord = {round(self._Y_coord, 6)}, Z_coord = {round(self._Z_coord, 6)}"

    def __repr__(self):
        return f"Vector([{self._X_coord:.6f}, {self._Y_coord:.6f}, {self._Z_coord:.6f}])"

    # -------------------------------
    # Метод для приведения к dict
    def to_dict(self):
        return {
            "X": self._X_coord,
            "Y": self._Y_coord,
            "Z": self._Z_coord
        }

    # Метод для приведения к list
    def to_list(self):
        return [self._X_coord, self._Y_coord, self._Z_coord]

    def to_numpy(self) -> np.ndarray:
        return np.array(self.to_list(), dtype=float)
