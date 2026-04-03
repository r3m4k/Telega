# System imports
from typing import Protocol, TypeVar

# External imports

# User imports

#########################
# Протокол для описания декодера
# Объявление типа, который будет обозначать тип данных, хранящихся в received_data
T = TypeVar('T')

class DecoderProtocol(Protocol[T]):
    """
    Протокол, описывающий любой декодер, который принимает байты
    и накапливает декодированные объекты типа T.
    """
    received_data: T

    @property
    def data_len(self) -> int: ...

    def byte_processing(self, bt: bytes) -> None: ...

    def save_received_data(self, filename: str) -> None: ...
