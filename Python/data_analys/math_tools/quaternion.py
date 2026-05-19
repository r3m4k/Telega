# System imports

# External imports
import numpy as np

# User imports
from dev.data_analys.math_tools.vector_3d import Vector

##########################################################

class Quaternion:
    """
    Класс для использования кватернионов.
    """

    def __init__(self, w: float = 1.0, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        """
        Инициализация кватерниона с заданными компонентами и последующая нормализация.
        """
        self.w = w
        self.x = x
        self.y = y
        self.z = z

    def normalize(self) -> None:
        """Нормализация кватерниона."""
        norm = self.norm
        if norm > 0:
            self.w /= norm
            self.x /= norm
            self.y /= norm
            self.z /= norm

    @property
    def norm(self) -> float:
        """Возвращает евклидову норму кватерниона."""
        return np.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)

    def copy(self) -> 'Quaternion':
        """Создаёт глубокую копию кватерниона."""
        return Quaternion(self.w, self.x, self.y, self.z)

    def conjugate(self) -> 'Quaternion':
        """Возвращает сопряжённый кватернион (обратный для единичного)."""
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def __mul__(self, other: 'Quaternion') -> 'Quaternion':
        """
        Умножение кватернионов (self * other).
        """
        if not isinstance(other, Quaternion):
            raise TypeError("Умножение определено только между кватернионами")
        return Quaternion(
            self.w * other.w - self.x * other.x - self.y * other.y - self.z * other.z,
            self.w * other.x + self.x * other.w + self.y * other.z - self.z * other.y,
            self.w * other.y - self.x * other.z + self.y * other.w + self.z * other.x,
            self.w * other.z + self.x * other.y - self.y * other.x + self.z * other.w
        )

    def rotate_vector(self, vec: Vector) -> Vector:
        """
        Поворачивает вектор v с помощью кватерниона.

        Аргументы:
            v: объект Vector.

        Возвращает:
            Повёрнутый вектор (объект Vector).
        """
        if not isinstance(vec, Vector):
            TypeError("Поворот с помощью кватерниона определён только для типа Vector")

        self.normalize()    # Нормируем кватернион

        # Реализуем поворот вектора
        p = Quaternion(0, vec[0], vec[1], vec[2])
        rotated = self * p * self.conjugate()

        return Vector([rotated.x, rotated.y, rotated.z])

    def to_matrix(self) -> np.ndarray:
        """
        Преобразует кватернион в матрицу поворота 3x3 (numpy-массив).
        """
        w, x, y, z = self.w, self.x, self.y, self.z
        return np.array([
            [1 - 2*y*y - 2*z*z,   2*x*y - 2*z*w,     2*x*z + 2*y*w],
            [2*x*y + 2*z*w,       1 - 2*x*x - 2*z*z, 2*y*z - 2*x*w],
            [2*x*z - 2*y*w,       2*y*z + 2*x*w,     1 - 2*x*x - 2*y*y]
        ])

    @classmethod
    def from_axis_angle(cls, axis: Vector, angle: float) -> 'Quaternion':
        """
        Создаёт кватернион из оси вращения и угла.

        Аргументы:
            axis: объект Vector, представляющий ось.
            angle: угол поворота в радианах.

        Возвращает:
            Объект Quaternion.
        """
        # Преобразуем ось в numpy-массив
        axis_np = np.array(axis.to_list())
        axis_np = axis_np / np.linalg.norm(axis_np)
        half_angle = angle * 0.5
        sin_half = np.sin(half_angle)
        return cls(
            np.cos(half_angle),
            axis_np[0] * sin_half,
            axis_np[1] * sin_half,
            axis_np[2] * sin_half
        )

    @classmethod
    def from_gyro(cls, gyro: Vector, dt: float) -> 'Quaternion':
        """
        Создаёт инкрементальный кватернион поворота из вектора угловой скорости.

        Аргументы:
            gyro: объект Vector, представляющий угловую скорость (рад/с).
            dt: шаг по времени в секундах.

        Возвращает:
            Кватернион, соответствующий повороту за время dt (в предположении постоянной угловой скорости).
        """
        omega = gyro.norm
        axis = gyro / omega
        angle = omega * dt
        return cls.from_axis_angle(axis, angle)

    @classmethod
    def from_matrix(cls, R: np.ndarray) -> 'Quaternion':
        """
        Преобразует матрицу поворота 3x3 в кватернион, используя устойчивый алгоритм.

        Аргументы:
            R: numpy массив 3x3, представляющий матрицу поворота.

        Возвращает:
            Объект Quaternion.
        """
        R = np.asarray(R, dtype=float)
        q = np.empty(4)
        t = np.trace(R)
        if t > 0:
            t = np.sqrt(t + 1.0)
            q[0] = 0.5 * t
            t = 0.5 / t
            q[1] = (R[2, 1] - R[1, 2]) * t
            q[2] = (R[0, 2] - R[2, 0]) * t
            q[3] = (R[1, 0] - R[0, 1]) * t
        else:
            i, j, k = 0, 1, 2
            if R[1, 1] > R[0, 0]:
                i, j, k = 1, 2, 0
            if R[2, 2] > R[i, i]:
                i, j, k = 2, 0, 1
            t = np.sqrt(R[i, i] - R[j, j] - R[k, k] + 1.0)
            q[i + 1] = 0.5 * t
            t = 0.5 / t
            q[0] = (R[k, j] - R[j, k]) * t
            q[j + 1] = (R[j, i] + R[i, j]) * t
            q[k + 1] = (R[k, i] + R[i, k]) * t
        return cls(q[0], q[1], q[2], q[3])

    def __repr__(self) -> str:
        return f"Quaternion(w={self.w:.6f}, x={self.x:.6f}, y={self.y:.6f}, z={self.z:.6f})"