"""
Пакет для работы с декодером данных в формате "Гиронавт"
"""

__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from .decoder_protocol import DecoderProtocol
from .data_description import TelegaData, TriaxialData
from .telega_decoder import TelegaDecoder

# --------------------------------------------------------

__all__ = [
    'DecoderProtocol',
    'TelegaDecoder',
    'TelegaData',
    'TriaxialData'
]

# --------------------------------------------------------
