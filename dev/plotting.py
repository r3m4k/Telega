# System imports
import os
import json
from enum import Enum
import binascii
from typing import BinaryIO, Tuple, Sequence, Union, cast, Any
from pprint import pprint

# External imports
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes

# User imports
from consts import CWD, JSON_FILE, color_scheme
import filterpy.kalman
import filterpy.common

##########################################################

class Canvas:
    """
    Класс для создания графиков и для работы с ними.
    Пример использования:

        import numpy as np
        import matplotlib.pyplot as plt
        from reading_data import Canvas

        x_data = np.linspace(0, 2 * np.pi)
        x_data_x2 = np.linspace(0, 4 * np.pi)

        canvas_1 = Canvas()
        canvas_1.plot(x_data, [np.sin(x_data), np.cos(x_data)], label=['sin(x)', 'cos(x)'])
        canvas_1.suptitle('sin(x) and cos(x)', weight='bold', fontsize=16)

        canvas_2 = Canvas(n_cols=2)
        canvas_2.plot([x_data,  x_data_x2], [np.sin(x_data), np.cos(x_data_x2)], label=['sin(x)', 'cos(x)'])
        canvas_2.plot([x_data_x2,  x_data], [1 + np.sin(x_data_x2), 1 + np.cos(x_data)], label=['sin(x)', 'cos(x)'])
        canvas_2.set_axis_labels(x_label=['x_value', None], y_label=['sin(x)', 'cos(x)'])
        canvas_2.axis_titles(['sin(x)', 'cos(x)'])

        canvas_3 = Canvas(n_rows=2, n_cols=2)
        canvas_3.plot(x_data,
                      [[np.sin(x_data), np.cos(x_data)],
                       [np.sinh(x_data), np.cosh(x_data)]],
                      label=[['sin(x)', 'cos(x)'],
                             ['sinh(x)', 'cosh(x)']],
                      color_names=[['tab:blue', 'tab:red'],
                                   ['tab:orange', 'tab:green']])
        canvas_3.grid_all_axes()
        canvas_3.suptitle('Trigonometric and hyperbolic functions', style='italic', fontsize=12)
        canvas_3.axis_titles([['sin(x)', 'cos(x)'],
                              ['sinh(x)', 'cosh(x)']])

        canvas_4 = Canvas(n_rows=2)
        canvas_4.plot(x_data,
                      [np.sin(x_data + np.pi / 2), [None for _ in range(len(x_data))]],
                      label=['sin(x)', None])
        canvas_4.plot(x_data,
                      [[None for _ in range(len(x_data))], np.cos(x_data + np.pi / 2)],
                      label=[None, 'cos(x)'])

        plt.show()

    """

    def __init__(self, fig_height=9, fig_width=16, n_rows=1, n_cols=1, **ax_kwargs):
        # Специально оставил fig и ax публичными, чтобы в дальнейшем использовании была возможность индивидуальной настройки
        self.fig: Figure = plt.figure(figsize=(fig_width, fig_height))
        self.ax: np.typing.NDArray[Axes] = self.fig.subplots(nrows=n_rows, ncols=n_cols, **ax_kwargs)

        self._nrows = n_rows
        self._ncols = n_cols

    def __del__(self):
        self.fig.clf()
        plt.close()

    def save_figure(self, saving_path: str):
        self.fig.savefig(saving_path)

    @staticmethod
    def show():
        plt.show(block=True)

    def suptitle(self, text, **kwargs):
        self.fig.suptitle(text, **kwargs)

    def set_axis_titles(self, titles: str | list, **text_kwargs):
        for n_row in range(self._nrows):
            for n_col in range(self._ncols):

                # Если только один график
                if (self._nrows == 1) and (self._ncols == 1):
                    ax = cast(Axes, self.ax)
                    title = titles

                # Если только одна колонка графиков
                elif self._ncols == 1:
                    ax = cast(Axes, self.ax[n_row])
                    title = titles[n_row]

                # Если только один ряд графиков
                elif self._nrows == 1:
                    ax = cast(Axes, self.ax[n_col])
                    title = titles[n_col]

                # Если несколько рядов и колонок графиков
                else:
                    ax = cast(Axes, self.ax[n_row, n_col])
                    title = titles[n_row][n_col]

                ax.set_title(label=title, **text_kwargs)

    def tight_layout(self, *args, **kwargs):
        self.fig.tight_layout(*args, **kwargs)

    def grid_all_axes(self, **kwargs):
        for n_row in range(self._nrows):
            for n_col in range(self._ncols):

                # Если только один график
                if (self._nrows == 1) and (self._ncols == 1):
                    ax = cast(Axes, self.ax)

                # Если только одна колонка графиков
                elif self._ncols == 1:
                    ax = cast(Axes, self.ax[n_row])

                # Если только один ряд графиков
                elif self._nrows == 1:
                    ax = cast(Axes, self.ax[n_col])

                # Если несколько рядов и колонок графиков
                else:
                    ax = cast(Axes, self.ax[n_row, n_col])

                ax.grid(**kwargs)

    def set_axis_labels(self,
                        x_label: str | list[str] | list[list[str]] = None,
                        y_label: str | list[str] | list[list[str]] = None,
                        **text_kwargs):

        for n_row in range(self._nrows):
            for n_col in range(self._ncols):

                # Если только один график
                if (self._nrows == 1) and (self._ncols == 1):
                    ax = cast(Axes, self.ax)
                    if x_label:
                        ax.set_xlabel(x_label, **text_kwargs)
                    if y_label:
                        ax.set_ylabel(y_label, **text_kwargs)

                # Если только один ряд графиков
                elif self._nrows == 1:
                    ax = cast(Axes, self.ax[n_col])
                    if x_label:
                        ax.set_xlabel(x_label[n_col], **text_kwargs)
                    if y_label:
                        ax.set_ylabel(y_label[n_col], **text_kwargs)

                # Если только одна колонка графиков
                elif self._ncols == 1:
                    ax = cast(Axes, self.ax[n_row])
                    if x_label:
                        # Если передали только одно значение x_label, то подпишем только нижнюю ось
                        if isinstance(x_label, str):
                            if n_row == self._nrows - 1:
                                ax.set_xlabel(x_label, **text_kwargs)
                        else:
                            ax.set_xlabel(x_label[n_row], **text_kwargs)
                    if y_label:
                        ax.set_ylabel(y_label[n_row], **text_kwargs)

                # Если несколько рядов и колонок графиков
                else:
                    ax = cast(Axes, self.ax[n_row, n_col])
                    if x_label:
                        # Если передали для каждой колонки одну подпись к оси x, то подпишем только нижнюю ось в каждой колонке
                        if len(x_label) == self._ncols:
                            if n_row == self._nrows - 1:
                                ax.set_xlabel(x_label[n_col], **text_kwargs)
                        else:
                            ax.set_xlabel(x_label[n_row][n_col], **text_kwargs)
                    if y_label:
                        ax.set_ylabel(y_label[n_row][n_col], **text_kwargs)

    def plot(self,
             x_axis: np.typing.NDArray | np.typing.ArrayLike | list,
             plot_data: np.typing.NDArray | np.typing.ArrayLike | list,
             color_names: str | list = None,
             label: str | list = None,
             **line_kwargs):
        """
        Метод для построения графиков с гибкой настройкой содержимого.
        """

        _x_axis_array = np.array(x_axis)
        _plot_data_array = np.array(plot_data)

        for n_row in range(self._nrows):
            for n_col in range(self._ncols):
                axis_kwargs = {}

                # Если только один график
                if (self._nrows == 1) and (self._ncols == 1):
                    ax = cast(Axes, self.ax)
                    if _plot_data_array.ndim == 1:
                        if color_names:
                            axis_kwargs["color"] = color_names
                        if label:
                            axis_kwargs["label"] = label
                        ax.plot(_x_axis_array, _plot_data_array, **axis_kwargs, **line_kwargs)

                    else:
                        for i in range(_plot_data_array.ndim):
                            if color_names:
                                axis_kwargs["color"] = color_names[i]
                            if label:
                                axis_kwargs["label"] = label[i]
                            ax.plot(_x_axis_array, _plot_data_array[i], **axis_kwargs, **line_kwargs)

                # Если только один ряд графиков
                elif self._nrows == 1:
                    ax = cast(Axes, self.ax[n_col])

                    if color_names:
                        axis_kwargs["color"] = color_names[n_col]
                    if label:
                        axis_kwargs["label"] = label[n_col]

                    # Если данные _x_axis_array общие для всех графиков
                    if _x_axis_array.ndim == 1:
                        ax.plot(_x_axis_array, _plot_data_array[n_col], **axis_kwargs, **line_kwargs)
                    else:
                        ax.plot(_x_axis_array[n_col], _plot_data_array[n_col], **axis_kwargs, **line_kwargs)

                # Если только одна колонка графиков
                elif self._ncols == 1:
                    ax = cast(Axes, self.ax[n_row])

                    if color_names:
                        axis_kwargs["color"] = color_names[n_row]
                    if label:
                        axis_kwargs["label"] = label[n_row]

                    # Если данные _x_axis_array общие для всех графиков
                    if _x_axis_array.ndim == 1:
                        ax.plot(_x_axis_array, _plot_data_array[n_row], **axis_kwargs, **line_kwargs)
                    # Если разные
                    else:
                        ax.plot(_x_axis_array[n_row], _plot_data_array[n_row], **axis_kwargs, **line_kwargs)

                # Если несколько рядов и колонок графиков
                else:
                    ax = cast(Axes, self.ax[n_row, n_col])

                    if color_names:
                        axis_kwargs["color"] = color_names[n_row][n_col]
                    if label:
                        axis_kwargs["label"] = label[n_row][n_col]

                    # Если данные _x_axis_array общие для всех графиков
                    if _x_axis_array.ndim == 1:
                        ax.plot(_x_axis_array, _plot_data_array[n_row, n_col], **axis_kwargs, **line_kwargs)
                    # Если разные
                    else:
                        ax.plot(_x_axis_array[n_row, n_col], _plot_data_array[n_row, n_col], **axis_kwargs,
                                **line_kwargs)

                if "label" in axis_kwargs.keys():
                    if axis_kwargs["label"]:
                        ax.legend()


class CanvasConfig:
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

class Plotter:
    """
    Класс-обёртка над Canvas для построения графиков, необходимых в ходе обработки данных
    """
    def __init__(self, canvas_config: CanvasConfig):
        self.canvas: Canvas = Canvas(n_rows = canvas_config.n_rows,
                                     n_cols = canvas_config.n_cols,
                                     **canvas_config.ax_kwargs)

        self.canvas_config: CanvasConfig = canvas_config

    def update_config(self, new_canvas_config: CanvasConfig):
        self.canvas_config = new_canvas_config

    def save(self, path: str):
        self.canvas.save_figure(saving_path=path)

    def plotting_3d(self):
        """
        Построение графиков величин, имеющие три компоненты
        """
        if (self.canvas_config.n_rows != 3) and (self.canvas_config.n_cols != 1):
            raise RuntimeError('Неправильная сетка фигуры!\n'
                               'Должно быть: n_rows = 3, n_cols = 1\n'
                               f'Передано: n_rows = {self.canvas_config.n_rows}, n_cols = {self.canvas_config.n_cols}')

        self.canvas.plot(
            self.canvas_config.x_data,
            self.canvas_config.y_data,
            color_names=self.canvas_config.color_names,
            label=self.canvas_config.label,
            **self.canvas_config.line_kwargs
        )
        self.canvas.set_axis_labels(x_label=self.canvas_config.x_label,
                                    y_label=self.canvas_config.y_label)
        self.canvas.suptitle(self.canvas_config.suptitle, **self.canvas_config.suptitle_kwargs)
        self.canvas.grid_all_axes()
        self.canvas.tight_layout()

    def plotting_3d_static(self):
        """
        Построение графиков статических величин, имеющие три компоненты, а также гистограммы их распределений
        """
        if (self.canvas_config.n_rows != 3) and (self.canvas_config.n_cols != 2):
            raise RuntimeError('Неправильная сетка фигуры!\n'
                               'Должно быть: n_rows = 3, n_cols = 2\n'
                               f'Передано: n_rows = {self.canvas_config.n_rows}, n_cols = {self.canvas_config.n_cols}')

        self.canvas.plot(
            [[self.canvas_config.x_data, np.full(self.canvas_config.x_data.shape, np.nan, dtype=float)] for _ in range(3)],
            [[self.canvas_config.y_data[i], np.full(self.canvas_config.y_data[i].shape, np.nan, dtype=float)] for i in range(3)],
            color_names=[[self.canvas_config.color_names[i], None] for i in range(3)]
        )
        self.canvas.suptitle(self.canvas_config.suptitle, **self.canvas_config.suptitle_kwargs)

        if isinstance(self.canvas_config.x_label, str):
            self.canvas.set_axis_labels(x_label=[self.canvas_config.x_label, None],
                                        y_label=[[self.canvas_config.y_label[i], None] for i in range(3)])
        elif isinstance(self.canvas_config.x_label, list):
            self.canvas.set_axis_labels(x_label=[[self.canvas_config.x_label[i], None] for i in range(3)],
                                        y_label=[[self.canvas_config.y_label[i], None] for i in range(3)])
        else:
            raise RuntimeError('Unknown x_label type.')

        if self.canvas_config.annotation:
            for n_row in range(3):
                ax = cast(Axes, self.canvas.ax[n_row, 0])
                ax.axhline(np.mean(self.canvas_config.y_data[n_row]),
                           color=self.canvas_config.dark_color_names[n_row],
                           linestyle='--', linewidth=2.5)
                ax.annotate(self.canvas_config.annotation[n_row],
                            xy=(0.64, 0.88), xycoords='axes fraction', size=10,
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=2))
                ax.grid()

        # Гистограммы
        n_bins = 100
        for n_row in range(3):
            ax = cast(Axes, self.canvas.ax[n_row, 1])
            ax.hist(self.canvas_config.y_data[n_row], bins=n_bins, color='gray')
            ax.set_yticks([])
            ax.set_facecolor('whitesmoke')
            ax.annotate(f'σ = {np.round(np.std(self.canvas_config.y_data[n_row]), 6)}', xy=(0.64, 0.88),
                        xycoords='axes fraction', size=10,
                        bbox=dict(boxstyle="round,pad=0.3", fc="lightgray", ec="gray", lw=2))

        self.canvas.tight_layout()
