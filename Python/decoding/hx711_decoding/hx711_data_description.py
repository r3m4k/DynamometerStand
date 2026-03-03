# System imports
from typing import NamedTuple
from enum import IntEnum

# External imports

# User imports

#############################################


class HX711Gain(IntEnum):
    GAIN_128_A = 1   # Channel A, gain 128
    GAIN_32_B  = 2   # Channel B, gain 32
    GAIN_64_A  = 3   # Channel A, gain 64

    @classmethod
    def from_string(cls, name: str) -> 'HX711Gain':
        """
        Создаёт элемент перечисления по его имени (например, 'GAIN_128_A').
        Регистр должен совпадать с объявлением.
        Если имя не найдено, выбрасывает ValueError.
        """
        try:
            return cls[name]
        except KeyError:
            valid_names = ', '.join(cls.__members__.keys())
            raise ValueError(f"'{name}' не является допустимым именем HX711Gain. "
                             f"Допустимые имена: {valid_names}")

    def to_string(self) -> str:
        """Возвращает имя элемента (например, 'GAIN_128_A')"""
        return self.name

    @property
    def channel(self) -> str:
        """Возвращает канал ('A' или 'B')"""
        return 'A' if self in (self.GAIN_128_A, self.GAIN_64_A) else 'B'

    @property
    def gain_value(self) -> int:
        """Числовое значение коэффициента усиления (128, 32 или 64)"""
        return {1: 128, 2: 32, 3: 64}[self]

    def __str__(self) -> str:
        return f"{self.name} (gain={self.gain_value}, channel={self.channel})"

# ------------------------------------------

class HX711Data(NamedTuple):
    time: int           # uint32_t
    id: int             # uint8_t
    adc_value: int      # int32_t
    gain: HX711Gain     # uint8_t

    def __str__(self):
        return (f'Time:         {self.time}\n'
                f'Sensor id:    {self.id}\n'
                f'ADC value:    {self.adc_value}\n'
                f'Gain:         {self.gain}\n')

# ------------------------------------------

# Описание начала индексов данных внутри посылки
class HX711DataIndexes:
    time_index = 4
    id_index = 8
    adc_index = 9
    gain_index = 13
