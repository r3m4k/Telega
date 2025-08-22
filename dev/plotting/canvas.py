# System imports
from typing import cast

# External imports
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes

# User imports


##########################################################

class Canvas:
    """
    Класс для создания графиков и для работы с ними.
    Пример использования:

        import numpy as np
        import matplotlib.pyplot as plt
        from plotting import Canvas

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
        # Специально оставляем fig и ax публичными, чтобы в дальнейшем использовании была возможность их индивидуального использования
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
