"""Идентификаторы команд межпроцессорного протокола GUI и сессии МК."""

# System imports
from enum import StrEnum

# External imports

# User imports

#############################################


class CommandName(StrEnum):
    """Допустимые команды, передаваемые через command_queue."""

    STOP_RUNNING = 'STOP_RUNNING'
    HANDSHAKE_INIT = 'HANDSHAKE_INIT'
    START_CALIBRATION = 'START_CALIBRATION'
    START_STATIC_INIT = 'START_STATIC_INIT'
    START_MEASURING = 'START_MEASURING'
    STOP_MEASURING = 'STOP_MEASURING'
