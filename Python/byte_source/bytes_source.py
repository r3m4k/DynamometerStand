# System imports
import serial
from abc import ABC, abstractmethod

# External imports

# User imports

#########################

# Источник данных с использованием контекстного менеджера
class BytesSource(ABC):

    @abstractmethod
    def setup(self):
        pass

    @abstractmethod
    def cleanup(self):
        pass

    @abstractmethod
    def read_byte(self) -> bytes:
        pass

    def __enter__(self):
        self.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False    # Пробрасываем возможное исключение дальше