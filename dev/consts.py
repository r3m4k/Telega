# Файл для хранения константных значений

import os
from typing import NamedTuple


# -------------------------------
# Рабочая директория
# -------------------------------
if os.name == 'nt':  # sys.platform == 'win32':
    CWD = "D:/Job/Telega"
elif os.name == 'posix':
    CWD = os.getcwd()
else:
    raise RuntimeError('Unsupported OS')


# -------------------------------
# Json файл с настройками
# -------------------------------
JSON_FILE = f'{CWD}/dev/settings.json'


# -------------------------------
# Цветовые схемы для графиков
# -------------------------------
color_scheme = {
            'RGB_classic': {'X': 'tab:blue', 'Y': 'tab:red', 'Z': 'tab:green'},
            'RGB_dark': {'X': 'navy', 'Y': 'maroon', 'Z': 'darkgreen'},
            'RGB_light': {'X': 'skyblue', 'Y': 'coral', 'Z': 'yellowgreen'},

            'COP_classic': {'X': 'tab:cyan', 'Y': 'tab:orange', 'Z': 'tab:purple'},
            'COP_dark': {'X': 'steelblue', 'Y': 'goldenrod', 'Z': 'purple'},
            'COP_light': {'X': 'lightblue', 'Y': 'orange', 'Z': 'hotpink'},

            'ABS_values': {'Acc': 'goldenrod', 'Gyro': 'tab:purple', 'Temp': 'cyan'}
        }


# -------------------------------
# Необходимые координаты
# -------------------------------
class Coordinates(NamedTuple):
    """
    Класс для хранения данных одного проезда.
    В поле buffer хранится имя файла с буферными данными, записанные перед началом проезда.
    В поле data хранится имя файла с данными самого проезда.
    """
    latitude: float
    longitude: float

Moscow_coordinates = Coordinates(latitude=55.753960, longitude=37.620393)