# System imports
from typing import Protocol, TypeVar
from pathlib import Path

# External imports

# User imports
from .command import Command

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
    input_command: list[Command]

    @property
    def data_len(self) -> int: ...

    def byte_processing(self, bt: bytes) -> None: ...

    def save_received_data(self, filename: str | Path, sep: str = ',') -> None: ...
