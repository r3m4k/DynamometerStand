# System imports
from typing import NamedTuple

# External imports

# User imports

#############################################

class TriaxialData(NamedTuple):
    x_coord: float = 0.0
    y_coord: float = 0.0
    z_coord: float = 0.0

# ------------------------------------------

class GyronavtData(NamedTuple):
    time: int
    acc: TriaxialData
    gyro: TriaxialData
    mag: TriaxialData
    bar: float

    def __str__(self):
        return (f'Time: {self.time}\n\n'
                
                f'Acc:  {self.acc.x_coord}\n'
                f'      {self.acc.y_coord}\n'
                f'      {self.acc.z_coord}\n\n'
                
                f'Gyro: {self.gyro.x_coord}\n'
                f'      {self.gyro.y_coord}\n'
                f'      {self.gyro.z_coord}\n\n'
                
                f'Mag:  {self.mag.x_coord}\n'
                f'      {self.mag.y_coord}\n'
                f'      {self.mag.z_coord}\n\n'
                
                f'Bar:  {self.bar}\n')

# ------------------------------------------

# Описание начала индексов данных внутри посылки
class GyronavtDataIndexes:
    time_index = 4
    acc_index = 12
    gyro_index = 24
    mag_index = 36
    bar_index = 48