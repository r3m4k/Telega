import numpy as np

##########################################################

class Matrix:
    """
    Класс, предназначенный для работы с матрицами поворота в трёхмерном пространстве
    """
    def __init__(self):
        self._matrix = np.eye(3)

    # -------------------------------
    # Математические операторы
    # -------------------------------
    def __mul__(self, multiplier):
        if isinstance(multiplier, Matrix):
            self._matrix = np.dot(self._matrix, multiplier._matrix)
            return None

        elif isinstance(multiplier, Vector):
            return Vector(
                list(self._matrix @ np.array(multiplier.to_list()))
            )
        else:
            raise ValueError('In-place multiplication for Matrix is only supported with Matrix')

    def __imul__(self, matrix):
        if isinstance(matrix, Matrix):
            self._matrix = np.dot(self._matrix, matrix._matrix)
        else:
            raise ValueError('In-place multiplication for Matrix is only supported with Matrix')

    # -------------------------------
    # Стандартные операции
    # -------------------------------
    def __getitem__(self, index):
        return self._matrix[index]

    def __str__(self):
        return ('Matrix:\n'
                f'{self._matrix.__str__()}')

    # -------------------------------
    # Дополнительный функционал
    # -------------------------------
    def set_rotation_to_angles(self, X_angle: float, Y_angle: float, Z_angle: float):
        """
        Заполняет матрицу поворота 3x3 для углов Эйлера в порядке X → Y → Z.
        Углы задаются в градусах.

        Параметры:
            x_angle (float): Угол поворота вокруг оси X (крен) в градусах
            y_angle (float): Угол поворота вокруг оси Y (тангаж) в градусах
            z_angle (float): Угол поворота вокруг оси Z (рысканье) в градусах

        Матрица поворота: R = Rz * Ry * Rx
        """
        x_angle = np.radians(X_angle)
        y_angle = np.radians(Y_angle)
        z_angle = np.radians(Z_angle)

        sin_x, cos_x = np.sin(x_angle), np.cos(x_angle)
        sin_y, cos_y = np.sin(y_angle), np.cos(y_angle)
        sin_z, cos_z = np.sin(z_angle), np.cos(z_angle)

        self._matrix[0, 0] = cos_y * cos_z
        self._matrix[0, 1] = sin_x * sin_y * cos_z - cos_x * sin_z
        self._matrix[0, 2] = cos_x * sin_y * cos_z + sin_x * sin_z

        self._matrix[1, 0] = cos_y * sin_z
        self._matrix[1, 1] = sin_x * sin_y * sin_z + cos_x * cos_z
        self._matrix[1, 2] = cos_x * sin_y * sin_z - sin_x * cos_z

        self._matrix[2, 0] = -sin_y
        self._matrix[2, 1] = sin_x * cos_y
        self._matrix[2, 2] = cos_x * cos_y

    def set_rotation_to_Earth(self, acc, gyro, latitude_degree):
        """
        Заполнение матрицы поворота в СК Земли по проекциям
        ускорения свободного падения и угловой скорости.
        :parameter acc: Vector - вектор ускорения свободного падения
        :parameter gyro: Vector - вектор угловой скорости
        :parameter latitude_degree: float - значение широты в градусах
        """
        if (not isinstance(acc, Vector)) or (not isinstance(gyro, Vector)):
            raise TypeError('Acc and Gyro must be of type Vector')

        latitude = np.radians(latitude_degree)

        # Абсолютное значение ускорения свободного падения. Вектор имеет проекцию только на ось OZ
        G = np.sqrt(acc['X']**2 + acc['Y']**2 + acc['Z']**2)

        # Абсолютное значение угловой скорости Земли. Вектор имеет проекции на ось OY - W_Y и на ось OZ - W_Z
        W = np.sqrt(gyro['X']**2 + gyro['Y']**2 + gyro['Z']**2)
        W_Y = W * np.sin(latitude)
        W_Z = W * np.cos(latitude)

        # Вспомогательный вектор А, который является векторным произведением векторов G и W
        A: float = G * W * np.sin(latitude)

        # Найдём координаты вектора А в СК датчика
        a_x = gyro['Y'] * acc['Z'] - gyro['Z'] * acc['Y']
        a_y = gyro['Z'] * acc['X'] - gyro['X'] * acc['Z']
        a_z = gyro['X'] * acc['Y'] - gyro['Y'] * acc['X']

        # Заполним матрицу перехода по столбцам
        self._matrix[0, 0] = a_x / A
        self._matrix[1, 0] = a_y / A
        self._matrix[2, 0] = a_z / A

        self._matrix[0, 1] = (gyro['X'] - W_Z * acc['X'] / G) / W_Y
        self._matrix[1, 1] = (gyro['Y'] - W_Z * acc['Y'] / G) / W_Y
        self._matrix[2, 1] = (gyro['Z'] - W_Z * acc['Z'] / G) / W_Y

        self._matrix[0, 2] = acc['X'] / G
        self._matrix[1, 2] = acc['Y'] / G
        self._matrix[2, 2] = acc['Z'] / G

        # Получили марицу перехода из СК Земли в СК датчика. Поэтому исходная матрица будет обратной к построенной
        self._matrix = np.linalg.inv(self._matrix)

##########################################################

class Vector:
    """
    Класс, предназначенный для работы с вектором, имеющий три компоненты
    """
    def __init__(self, coords: list[float | np.float64]):
        if len(coords) != 3:
            raise RuntimeError('Incorrect dimension of the vector.'
                               f'The Vector type have 3 dimensions, but given {len(coords)}')

        self._X_coord: float = float(coords[0])
        self._Y_coord: float = float(coords[1])
        self._Z_coord: float = float(coords[2])

    # -------------------------------
    # Математические операции
    # -------------------------------
    def rotate(self, rotation_matrix: Matrix):
        rotated_vector = rotation_matrix * self

        self._X_coord = rotated_vector['X']
        self._Y_coord = rotated_vector['Y']
        self._Z_coord = rotated_vector['Z']

    def norm(self):
        return np.sqrt(self._X_coord**2 + self._Y_coord**2 + self._Z_coord**2)

    # -------------------------------
    # Математические операторы
    # -------------------------------
    def __add__(self, other):
        if isinstance(other, Vector):
            return Vector([
                self._X_coord + other._X_coord,
                self._Y_coord + other._Y_coord,
                self._Z_coord + other._Z_coord
            ])
        else:
            raise ValueError('Both terms must be Vector')

    def __iadd__(self, other):
        if isinstance(other, Vector):
            self._X_coord += other._X_coord
            self._Y_coord += other._Y_coord
            self._Z_coord += other._Z_coord
        else:
            raise ValueError('Term must be Vector')

    def __sub__(self, other):
        if isinstance(other, Vector):
            return Vector([
                self._X_coord + other._X_coord,
                self._Y_coord + other._Y_coord,
                self._Z_coord + other._Z_coord
            ])
        else:
            raise ValueError('Reduced and subtracted must be Vector')

    def __isub__(self, other):
        if isinstance(other, Vector):
            self._X_coord -= other._X_coord
            self._Y_coord -= other._Y_coord
            self._Z_coord -= other._Z_coord
        else:
            raise ValueError('Term must be Vector')

    def __mul__(self, multiplier):
        try:
            _multiplier = float(multiplier)
        except ValueError:
            raise ValueError('The multiplier cannot be converted to the float type')

        return Vector([
            self._X_coord * _multiplier,
            self._Y_coord * _multiplier,
            self._Z_coord * _multiplier
        ])

    def __imul__(self, multiplier):
        try:
            _multiplier = float(multiplier)
        except ValueError:
            raise ValueError('The multiplier cannot be converted to the float type')

        self._X_coord *= _multiplier
        self._Y_coord *= _multiplier
        self._Z_coord *= _multiplier

    # -------------------------------
    # Работа с коллекциями
    # -------------------------------
    def __len__(self):
        return 3

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.to_list()[item]

        elif isinstance(item, str):
            return  self.to_dict()[item]

        else:
            raise KeyError('Vector supports __getitem__ with int or str')

    def __setitem__(self, key, value):
        if isinstance(key, int):
            match key:
                case 0:
                    self._X_coord = value
                case 1:
                    self._Y_coord = value
                case 2:
                    self._Z_coord = value

                case _:
                    raise ValueError('Wrong index. Index must be in [0, 1, 2]')

        elif isinstance(key, str):
            match key:
                case 'X':
                    self._X_coord = value
                case 'Y':
                    self._Y_coord = value
                case 'Z':
                    self._Z_coord = value

                case _:
                    raise ValueError('Wrong key. Key must be in ["X", "Y", "Z"]')

        else:
            raise KeyError('Vector supports __setitem__ with int or str')

    def __str__(self):
        return f"X_coord = {round(self._X_coord, 6)}, Y_coord = {round(self._Y_coord, 6)}, Z_coord = {round(self._Z_coord, 6)}"

    # -------------------------------
    # Метод для приведения к dict
    def to_dict(self):
        return {
            "X": self._X_coord,
            "Y": self._Y_coord,
            "Z": self._Z_coord
        }

    # Метод для приведения к list
    def to_list(self):
        return [self._X_coord, self._Y_coord, self._Z_coord]


##########################################################

class RotatedValues:
    """
    Класс для перевода данных акселерометра из СК датчика в СК Земли.
    Параметры СК Земли: OX - на восток, OY - на север, OZ - вертикально вверх.
    """
    def __init__(self,
                 acc_dict: dict[str, np.typing.NDArray], acc_dict_buffer: dict[str, np.typing.NDArray],
                 gyro_dict: dict[str, np.typing.NDArray], gyro_dict_buffer: dict[str, np.typing.NDArray],
                 latitude: float):

        self._coords = ['X', 'Y', 'Z']
        dicts = [acc_dict, acc_dict_buffer, gyro_dict, gyro_dict_buffer]
        if not all(list(d.keys()) == self._coords for d in dicts):
            raise KeyError('Ключи в переданных словарях не совпадают с ["X", "Y", "Z"]')

        self._acc: dict[str, np.typing.NDArray] = acc_dict
        self._acc_buffer: dict[str, np.typing.NDArray] = acc_dict_buffer

        self._gyro: dict[str, np.typing.NDArray] = gyro_dict
        self._gyro_buffer: dict[str, np.typing.NDArray] = gyro_dict_buffer

        self._latitude: float = latitude        # Широта, на которой проводились измерения

        self._R_to_prev = np.eye(3)             # Матрица перехода к предыдущему состоянию
        self._R_to_Earth = np.eye(3)            # Матрица перехода из исходного состояния в СК Земли, в которой ось ОУ направлена на север

        self.R_det = []         # Список значений определителей матрицы перехода, нужен для контроля корректности алгоритма


    def _start(self):
        pass


##########################################################
