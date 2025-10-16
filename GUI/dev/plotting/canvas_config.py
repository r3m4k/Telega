# System imports

# External imports
import numpy as np

# User imports


##########################################################

class CanvasConfig:
    """
    Класс, предназначенный для удобного формирования параметров для построения
    графиков с помощью Canvas
    """

    def __init__(self):
        # Параметры фигуры
        self.n_rows: int = 1
        self.n_cols: int = 1
        self.ax_kwargs = {}

        # Данные для построения графиков
        self.x_data: np.typing.NDArray | np.typing.ArrayLike | list = None
        self.y_data: np.typing.NDArray | np.typing.ArrayLike | list = None

        # Параметры заголовка
        self.suptitle: str = None
        self.suptitle_kwargs: dict = {
            'weight': 'bold',
            'fontsize': 14
        }

        # Параметры графиков
        self.color_names: str | list = None
        self.label: str | list = None
        self.line_kwargs = {
            'linewidth': 2.0
        }

        # Параметры осей
        self.ax_title: str | list = None
        self.ax_title_params = dict()

        self.x_label: str | list[str] | list[list[str]] = None
        self.y_label: str | list[str] | list[list[str]] = None

        # Дополнительные параметры
        self.annotation: list[str] = None
        self.dark_color_names: list[str] = None

