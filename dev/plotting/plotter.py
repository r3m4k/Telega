# System imports
from typing import cast

# External imports
import numpy as np
from matplotlib.axes import Axes

# User imports
from .canvas import Canvas
from .canvas_config import CanvasConfig

##########################################################

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

        self.plotting_hline(values=[np.mean(self.canvas_config.y_data[n_row]) for n_row in range(3)],
                            colors=[self.canvas_config.dark_color_names[n_row] for n_row in range(3)],
                            annotations=self.canvas_config.annotation)

        # Создадим сетку на графиках
        for n_row in range(3):
            ax = cast(Axes, self.canvas.ax[n_row, 0])
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

    def plotting_hline(self, values: list[float],  colors: list[str], annotations: list[str]=None):
        for n_row in range(3):
            try:
                ax = cast(Axes, self.canvas.ax[n_row, 0])
            except IndexError:
                ax = cast(Axes, self.canvas.ax[n_row])

            ax.axhline(values[n_row],
                       color=colors[n_row],
                       linestyle='--', linewidth=2.5)
            if annotations[n_row]:
                ax.annotate(annotations[n_row],
                            xy=(0.64, 0.88), xycoords='axes fraction', size=10,
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=2))
