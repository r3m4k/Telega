# Файл для хранения константных значений

import os

if os.name == 'nt':  # sys.platform == 'win32':
    CWD = "D:/Job/Telega"
elif os.name == 'posix':
    CWD = os.getcwd()
else:
    raise RuntimeError('Unsupported OS')

JSON_FILE = f'{CWD}/dev/settings.json'

color_scheme = {
            'RGB_classic': {'x': 'tab:blue', 'y': 'tab:red', 'z': 'tab:green'},
            'RGB_dark': {'x': 'navy', 'y': 'maroon', 'z': 'darkgreen'},
            'RGB_light': {'x': 'skyblue', 'y': 'coral', 'z': 'yellowgreen'},

            'COP_classic': {'x': 'tab:cyan', 'y': 'tab:orange', 'z': 'tab:purple'},
            'COP_dark': {'x': 'steelblue', 'y': 'goldenrod', 'z': 'purple'},
            'COP_light': {'x': 'lightblue', 'y': 'orange', 'z': 'hotpink'},
        }
