# System imports
import logging
from typing import Protocol

# External imports

# User imports

#############################################

class LoggerProtocol(Protocol):

    def debug(self, msg: str, *args, **kwargs):
        ...

    def info(self, msg: str, *args, **kwargs):
        ...

    def warning(self, msg: str, *args, **kwargs):
        ...

    def error(self, msg: str, *args, **kwargs):
        ...

    def critical(self, msg: str, *args, **kwargs):
        ...

    def exception(self, msg: str, *args, **kwargs):
        ...
