"""Идентификаторы событий межпроцессорного протокола сессии МК и GUI."""

# System imports
from enum import StrEnum

# External imports

# User imports

#############################################


class SessionEventName(StrEnum):
    """Допустимые события, передаваемые через response_queue."""

    HANDSHAKE_INIT_RESULT = 'HANDSHAKE_INIT_RESULT'
    SET_SAVING_FILE_RESULT = 'SET_SAVING_FILE_RESULT'
    START_STATIC_INIT_RESULT = 'START_STATIC_INIT_RESULT'
    START_MEASURING_RESULT = 'START_MEASURING_RESULT'
    STOP_MEASURING_RESULT = 'STOP_MEASURING_RESULT'

    STATIC_INIT_COMPLETED = 'STATIC_INIT_COMPLETED'
    SESSION_ERROR = 'SESSION_ERROR'
    SESSION_STOPPED = 'SESSION_STOPPED'
