import numpy as np

# User imports
from ..utils import trapezoidal_integration
from matrix import Matrix
from vector_3d import Vector


##########################################################


class RotatingFrameAnalyzer:
    """
    Класс для учёта нулевых значений полученных величин и вращения платы с помощью построения матриц поворота.
    Данные акселерометра переводятся в СК Земли, а из данных гироскопа вычитаются нулевые значения с учётом поворота
    платы относительно начального положения.
    Таким образом, получим абсолютные значения угловых скоростей на протяжении всего проезда.

    Параметры СК Земли: OX - на восток, OY - на север, OZ - вертикально вверх.
    """
    def __init__(self,
                 time: np.typing.NDArray,
                 acc_dict: dict[str, np.typing.NDArray[np.floating]],
                 acc_dict_buffer: dict[str, np.typing.NDArray[np.floating]],
                 gyro_dict: dict[str, np.typing.NDArray[np.floating]],
                 gyro_dict_buffer: dict[str, np.typing.NDArray[np.floating]],
                 latitude: float):

        self._coords = ['X', 'Y', 'Z']
        self._data_size = len(acc_dict['X'])

        dicts = [acc_dict, acc_dict_buffer, gyro_dict, gyro_dict_buffer]
        if not all(list(d.keys()) == self._coords for d in dicts):
            raise KeyError('Ключи в переданных словарях не совпадают с ["X", "Y", "Z"]')

        self._analyzed_values = {
            'Acc_X': list(), 'Acc_Y': list(), 'Acc_Z': list(),
            'Gyro_X': list(), 'Gyro_Y': list(), 'Gyro_Z': list(),
        }

        self._time_array = time

        self._acc_array: list[Vector] = [Vector([acc_dict[coord][i] for coord in self._coords]) for i in range(self._data_size)]
        self._acc_zero = Vector([np.mean(acc_dict_buffer[coord]) for coord in self._coords])

        self._gyro_array: list[Vector] = [Vector([gyro_dict[coord][i] for coord in self._coords]) for i in range(self._data_size)]
        self._gyro_zero = Vector([np.mean(gyro_dict_buffer[coord]) for coord in self._coords])

        self._latitude: float = latitude        # Широта, на которой проводились измерения

        self._R_to_next = Matrix()             # Матрица перехода к следующему состоянию
        self._R_to_begin = Matrix()            # Матрица перехода к исходному состоянию
        self._R_to_Earth = Matrix()            # Матрица перехода из исходного состояния в СК Земли, в которой ось ОУ направлена на север

    def get_analyzed_values(self):
        return {key: np.asarray(self._analyzed_values[key]) for key in self._analyzed_values.keys()}

    def start(self):
        """
        Принцип работы алгоритма:

        1) Вычисляем реальные значения ускорения и угловой скорости на (i-1)-ом и i-ом шаге, путём вычитания нулевого значения на (i-1)-ом шаге.
        2) По полученным значениям угловой скорости строим матрицу поворота от (i-1)-го состояния к i-му состоянию.
        3) Умножаем нулевые вектора величин на полученную матрицу перехода. Тем самым, мы получаем нулевые значения в новом положении платы.
        4) Данные угловой скорости оставляем в таком виде, а данные ускорения последовательно умножаем на матрицы R_to_begin и R_to_Earth.
            Таким образом мы получаем данные угловой скорости вдоль направления движения, а данные ускорений в СК Земли.
        """
        self._R_to_Earth.set_rotation_to_Earth(acc=self._acc_zero, gyro=self._gyro_zero, latitude_degree=self._latitude)

        # Первый кадр измерений сохраним с вычитанием нулевых значений, ускорения переведём в СК Земли
        acc = self._acc_array[0] - self._acc_zero
        acc = self._R_to_begin * acc
        acc = self._R_to_Earth * acc

        gyro = self._gyro_array[0] - self._gyro_zero

        for coord in self._coords:
            self._analyzed_values[f'Acc_{coord}'].append(acc[coord])
            self._analyzed_values[f'Gyro_{coord}'].append(gyro[coord])

        for i in range(1, self._data_size):
            # Вектора ускорения и угловой скорости на данной и предыдущей итерации
            acc = self._acc_array[i]

            gyro = self._gyro_array[i]
            gyro_prev = self._gyro_array[i-1]

            # Считаем, что между текущим и предыдущем измерениями плата повернулась на малый угол,
            # поэтому нулевые значения векторов не изменятся на одном шаге
            acc -= self._acc_zero

            gyro -= self._gyro_zero
            gyro_prev -= self._gyro_zero

            # Вычислим матрицу поворота от состояния i-1 к состоянию i
            # Углы поворота
            angles = {key: trapezoidal_integration(np.array([gyro_prev[key] / 1000, gyro[key] / 1000]), self._time_array[i] - self._time_array[i-1])
                      for key in self._coords}

            # Вычислим матрицу поворота к следующему состоянию
            self._R_to_next.set_rotation_to_angles(X_angle=angles['X'], Y_angle=angles['Y'], Z_angle=angles['Z'])

            # Вычислим матрицу поворота к первоначальному состоянию.
            # Умножаем на обратную матрицу тк это матрица циклического поворота из i-го состояния в состояние i-1, и так далее до нулевого состояния
            self._R_to_begin *= self._R_to_next.inv()

            # Переведём нулевые величины в новое состояние
            self._acc_zero = self._R_to_next * self._acc_zero
            self._gyro_zero = self._R_to_next * self._gyro_zero

            # Переведём значение ускорения в СК Земли
            acc = self._R_to_begin * acc
            acc = self._R_to_Earth * acc

            # Сохраним полученные значения
            for coord in self._coords:
                self._analyzed_values[f'Acc_{coord}'].append(acc[coord])
                self._analyzed_values[f'Gyro_{coord}'].append(gyro[coord])
