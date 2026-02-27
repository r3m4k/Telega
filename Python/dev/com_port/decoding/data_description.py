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

class TelegaData(NamedTuple):
    time: int
    acc: TriaxialData
    gyro: TriaxialData
    temp: float

    def __str__(self):
        return (f'Time: {self.time}\n\n'
                
                f'Acc:  {self.acc.x_coord}\n'
                f'      {self.acc.y_coord}\n'
                f'      {self.acc.z_coord}\n\n'
                
                f'Gyro: {self.gyro.x_coord}\n'
                f'      {self.gyro.y_coord}\n'
                f'      {self.gyro.z_coord}\n\n'
                

                f'Temp: {self.temp}\n')

    def to_dict(self) -> dict[str, ...]:
        return {
            'Time': self.time,
            'Acc_X': self.acc.x_coord,
            'Acc_Y': self.acc.y_coord,
            'Acc_Z': self.acc.z_coord,
            'Gyro_X': self.gyro.x_coord,
            'Gyro_Y': self.gyro.y_coord,
            'Gyro_Z': self.gyro.z_coord,
            'Temp': self.temp
        }

# ------------------------------------------

# Описание начала индексов данных внутри посылки
class TelegaDataIndexes:
    time_index = 4
    acc_index = 8
    gyro_index = 12
    temp_index = 16