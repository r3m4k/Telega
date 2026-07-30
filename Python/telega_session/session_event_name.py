"""Идентификаторы событий межпроцессорного протокола сессии МК и GUI."""

# System imports
from enum import StrEnum

# External imports

# User imports

#############################################


class SessionEventName(StrEnum):
    """Допустимые события, передаваемые через response_queue."""

    HANDSHAKE_DONE = 'HANDSHAKE_DONE'
    HANDSHAKE_FAILED = 'HANDSHAKE_FAILED'
    STOP_STATIC_INIT = 'STOP_STATIC_INIT'
    UNKNOWN_ERROR = 'UNKNOWN_ERROR'
    READ_ERROR = 'READ_ERROR'
    DEVICE_LOST = 'DEVICE_LOST'
    COMMAND_ACK_TIMEOUT = 'COMMAND_ACK_TIMEOUT'
    COMMAND_REJECTED = 'COMMAND_REJECTED'
    CONNECTION_FAILED = 'CONNECTION_FAILED'
