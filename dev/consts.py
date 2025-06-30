# Файл для хранения константных значений

import os

if os.name == 'nt':  # sys.platform == 'win32':
    CWD = "D:/Job/Telega"
elif os.name == 'posix':
    CWD = os.getcwd()
else:
    raise RuntimeError('Unsupported OS')

JSON_FILE = f'{CWD}/dev/settings.json'
