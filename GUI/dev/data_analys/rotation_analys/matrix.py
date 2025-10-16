import numpy as np


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
        from .vector_3d import Vector

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
            return self
        elif isinstance(matrix, np.ndarray):
            self._matrix = np.dot(self._matrix, matrix)
            return self
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
    def inv(self):
        return np.linalg.inv(self._matrix)

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
        from .vector_3d import Vector

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
