"""
Пакет для работы с COM-портом, связанный с системой автономной навигации.
Реализуется с помощью мультипроцессорного подхода.
"""

__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from .utils import get_ComPorts

from .decoder import (
    Decoder
)

from .proxy import (
    MyManager,
    COM_PortProxy,
    DecodeProxy
)

from .com_port import COM_Port

from .com_port_gui import (
    STM_ComPort,
    GPS_ComPort
)

# --------------------------------------------------------

__all__ = [
    'get_ComPorts',
    'Decoder',
    'STM_ComPort',
    'GPS_ComPort'
]

# --------------------------------------------------------
