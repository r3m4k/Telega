# System imports
import os
import json
from enum import Enum
import binascii
from operator import index
from typing import BinaryIO, Tuple, Sequence, Union, cast, Any
from pprint import pprint

# External imports
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes

# User imports
from consts import CWD, JSON_FILE

##########################################################

class DataProcessing:
    """
    Класс для чтения данных из файлов, собранных во время поезди с телегой
    """
    def __init__(self, data_dir: str, file_list: list):
        self._data_dir = data_dir        # Директория, в которой находятся файлы
        self._file_list = file_list      # Список обрабатываемых файлов

        self._received_data = {}         # Переменная для хранения прочитанных данных

    def get_data(self):
        return self._received_data

    def create_plots(self, filename):
        """
        Создание графиков данных, прочитанных из файла file_name
        """
        pass

    def _decoder(self):
        pass

    def _reading_file(self):
        pass

##########################################################

class Decoder:
    """
    Класс для декодировки данных из файла в формате:
    Заголовок - 4 байта
    Временная метка - 2 байта
    Ускорения по осям - 6 байт
    Угловые скорости по осям - 6 байт
    Температура - 2 байта
    Контрольная сумма - 1 байт
    """

    _Stages = Enum(
        value='STM_Stages',
        names=('WantHeader', 'WantPacketBody', 'WantConSum')
    )

    def __init__(self, filename: str):
        self._index = 0              # Индекс прочитанного символа в файле
        self._con_sum = 0            # Посчитанная контрольная сумма
        self._filename = filename    # Имя обрабатываемого файла
        self._file: BinaryIO = None  # Переменная для хранения файла

        with open(JSON_FILE, 'r')  as json_file:
            json_data = json.load(json_file)["Decoder"]
            self._header = json_data["header"]
            self._titles = json_data["titles"]
            self._coefficients = json_data["value_coefficients"]

        self._received_data = {key: np.array([], dtype=float) for key in self._titles}
        self._supported_formats = (0xc8, )
        self._package_size = 0

    def get_data(self):
        return self._received_data

    def decoding(self):

        self._file = open(self._filename, "rb")
        max_size = os.path.getsize(self._filename)

        bytes_buffer = []   # Буфер для байтов, прочитанных из очереди данных
        
        Stages = self._Stages
        stage = Stages.WantHeader

        while self._index < (max_size - self._package_size - 4):
            val = self._read_bin()
            match stage:
                case Stages.WantHeader:
                    if val == self._header[0]:
                        if self._read_bin() == self._header[1]:
                            self._check_format(self._read_bin())
                            self._package_size = self._read_bin()
                            stage = Stages.WantPacketBody

                case Stages.WantPacketBody:
                    bytes_buffer.append(val)
                    for i in range(self._package_size - 1):
                        bytes_buffer.append(self._read_bin())

                    stage = Stages.WantConSum

                case Stages.WantConSum:
                    # Тк мы высчитываем сумму при каждом чтении байта, то необходимо вычесть значение последнего байта,
                    # который несёт в себе значение контрольной суммы
                    self._con_sum -= val
                    # Сравним полученную контрольную сумму с посчитанной
                    if (self._con_sum & 255) == val:
                        self._list_to_dict(bytes_buffer)
                    else:
                        print(f'Received cs = {val}, calculated cs = {self._con_sum} & 255 = {self._con_sum & 255}')
                    stage = Stages.WantHeader
                    self._con_sum = 0
                    bytes_buffer = []

        self._file.close()

    @staticmethod
    def _mod_code(low_bit, high_bit):
        """
        Перевод числа high_bit << 8 + low_bit в модифицированном дополнительном коде в
        классическое с 15-ью значащими битами.
        :param low_bit: младшие 8 бит числа.
        :param high_bit: старшие 8 бит числа.
        :return: классическое знаковое число.
        """
        result = high_bit * 256 + low_bit
        sign_const = result >> 15
        if sign_const == 1:
            result &= 32767  # 32767 = 0111 1111 1111 1111
            # Обрежем старший бит
            result ^= 32767  # Инвертируем вс биты числа
            result *= -1

        return result

    def _read_bin(self):
        """
        Чтение бинарного числа в шестнадцатеричной системе исчисления.
        :param val: Шестнадцатеричное число.
        :return: Число в десятичной системе счисления.
        """
        try:
            res = int(binascii.hexlify(self._new_byte()), 16)
        except ValueError:
            # При достижении конца файла self._new_byte() вернёт b''.
            # ValueError: invalid literal for int() with base 16: b''
            raise EOFError

        self._index += 1
        self._con_sum += res
        return res

    def _new_byte(self):
        try:
            return self._file.read(1)
        except Exception as error:
            print(f'Error: {error}')
            return None

    def _check_format(self, package_format):
        if package_format not in self._supported_formats:
            raise RuntimeError(f"Unsupported package format: format {package_format} not in {self._supported_formats}")

    def _list_to_dict(self, buffer_list: list[bytes]):
        buffer_index = 0
        for index in range(len(self._titles)):

            if buffer_index > self._package_size:
                raise RuntimeError(f'Unsupported package size')

            key = self._titles[index]
            multiplier = self._coefficients[index]

            self._received_data[key] = np.append(
                self._received_data[key],
                self._mod_code(buffer_list[buffer_index], buffer_list[buffer_index + 1]) * multiplier
            )

            buffer_index += 2

##########################################################

class Canvas:
    """
    Класс для создания графиков и для работы с ними.
    Пример использования:
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

    def __init__(self, fig_height=9, fig_width=16, n_rows=1, n_cols=1, *ax_args, **ax_kwargs):
        # Специально оставил fig и ax публичными, чтобы в дальнейшем использовании была возможность индивидуальной настройки
        self.fig: Figure = plt.figure(figsize=(fig_width, fig_height))
        self.ax: np.typing.NDArray[Axes] = self.fig.subplots(nrows=n_rows, ncols=n_cols, *ax_args, **ax_kwargs)

        self._nrows = n_rows
        self._ncols = n_cols

    def save_figure(self, saving_path: str):
        self.fig.savefig(saving_path)

    @staticmethod
    def show():
        plt.show(block=True)

    def suptitle(self, text, **kwargs):
        self.fig.suptitle(text, **kwargs)

    def axis_titles(self, titles: str | list, **text_kwargs):
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
                       x_label: str | list[str] = None,
                       y_label: str | list[str] = None,
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
                        if len(x_label) == 1:
                            if n_col == self._ncols - 1:
                                ax.set_xlabel(x_label, **text_kwargs)
                        else:
                            ax.set_xlabel(x_label[n_col], **text_kwargs)
                    if y_label:
                        ax.set_ylabel(y_label, **text_kwargs)

                # Если несколько рядов и колонок графиков
                else:
                    ax = cast(Axes, self.ax[n_row, n_col])
                    if x_label:
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
        axis_kwargs = {}

        for n_row in range(self._nrows):
            for n_col in range(self._ncols):

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
                        ax.plot(_x_axis_array[n_row, n_col], _plot_data_array[n_row, n_col], **axis_kwargs, **line_kwargs)

                ax.legend()

class Plotting_3axes(Canvas):
    """
    Класс для создания графиков величин, имеющие 3 координаты
    """
    def __init__(self, *canvas_args, **canvas_kwargs):
        super().__init__(n_rows=3, n_cols=1, *canvas_args, **canvas_kwargs)

##########################################################

