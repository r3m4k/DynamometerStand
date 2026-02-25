# System imports
from typing import NamedTuple

# External imports

# User imports

#############################################

class HX711Data(NamedTuple):
    time: int
    id: int
    adc_value: int
    gain: int

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
