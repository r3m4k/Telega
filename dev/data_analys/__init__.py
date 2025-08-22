"""
Основной пакет для обработки данных с акселерометра и гироскопа
для системы автономной навигации
"""

__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from .utils import (
    name_of_file,
    cumulative_trapezoidal_integral,
    trapezoidal_integration,
    linear_subtraction,
    writing_to_csv_file
)

from .rotation_analys import (
    RotatingFrameAnalyzer,
    Vector,
    Matrix
)

from .filtering import Filter

# --------------------------------------------------------

__all__ = [
    # Из utils
    'name_of_file',
    'cumulative_trapezoidal_integral',
    'trapezoidal_integration',
    'linear_subtraction',
    'writing_to_csv_file',

    # Из rotation_analys
    'RotatingFrameAnalyzer',
    'Vector',
    'Matrix',

    # Из filtering
    'Filter'
]

# --------------------------------------------------------
