"""
Пакет для анализа вращения автономной системы навигации
"""

__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from .rotation import RotatingFrameAnalyzer
from .vector_3d import Vector
from .matrix import Matrix

# --------------------------------------------------------

__all__ = [
    'RotatingFrameAnalyzer',
    'Vector',
    'Matrix'
]