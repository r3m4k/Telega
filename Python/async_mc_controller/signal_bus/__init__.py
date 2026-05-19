"""
Пакет асинхронной сигнальной шины
"""

__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from .signals import Signals
from .signal_bus import SignalBus, Subscriber
from .subscribers import (
    NewByteSubscriber,
    PackageReadySubscriber,
    StopExecutingSubscriber,
    StartMeasuringSubscriber,
    StopMeasuringSubscriber,
    StartCalibrationSubscriber,
    StopCalibrationSubscriber,
    StartStaticInitSubscriber,
    StopStaticInitSubscriber,
    InterruptMeasuringSubscriber,
    ReadErrorSubscriber,
    HandshakeInitSubscriber,
    HandshakeDoneSubscriber,
    HeartbeatSentSubscriber,
    HeartbeatAckSubscriber,
    HandshakeFailedSubscriber,
    DeviceLostSubscriber,
    CommandSentSubscriber,
    CommandAckSubscriber,
    CommandAckTimeoutSubscriber,
    CommandRejectedSubscriber,
)
from .mc_bus import McBus

# --------------------------------------------------------

__all__ = [
    # Универсальный механизм
    'SignalBus',
    'Subscriber',
    'Signals',

    # Типизированная обёртка
    'McBus',

    # Протоколы подписчиков
    'NewByteSubscriber',
    'PackageReadySubscriber',
    'StopExecutingSubscriber',
    'StartMeasuringSubscriber',
    'StopMeasuringSubscriber',
    'StartCalibrationSubscriber',
    'StopCalibrationSubscriber',
    'StartStaticInitSubscriber',
    'StopStaticInitSubscriber',
    'InterruptMeasuringSubscriber',
    'ReadErrorSubscriber',
    'HandshakeInitSubscriber',
    'HandshakeDoneSubscriber',
    'HeartbeatSentSubscriber',
    'HeartbeatAckSubscriber',
    'HandshakeFailedSubscriber',
    'DeviceLostSubscriber',
    'CommandSentSubscriber',
    'CommandAckSubscriber',
    'CommandAckTimeoutSubscriber',
    'CommandRejectedSubscriber',
]

# --------------------------------------------------------