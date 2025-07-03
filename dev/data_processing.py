# System imports
import os
import json
from enum import Enum
import binascii
from typing import BinaryIO, Tuple, Sequence, Union, cast, Any
from pprint import pprint
from pathlib import Path

from collections import namedtuple
from typing import NamedTuple

# External imports
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes

# User imports
from consts import CWD, JSON_FILE, color_scheme
from data_analys import name_of_file, Decoder, Canvas, KalmanFilter

##########################################################

class MeasuringPair(NamedTuple):
    """
    Класс для хранения данных одного проезда.
    В поле buffer хранится имя файла с буферными данными, записанные перед началом проезда.
    В поле data хранится имя файла с данными самого проезда.
    """
    buffer: str
    data: str

##########################################################

class DataProcessing:
    """
    Класс для обработки данных из файлов, собранных во время поезди с телегой
    """
    def __init__(self, data_dir: str, file_list: list[str], parameters: dict):
        self._data_dir: str = data_dir              # Директория, в которой находятся файлы

        # Можно объединить все _file_init и _files_measuring
        self._file_list: list[str] = file_list      # Список обрабатываемых файлов
        self._parameters: dict = parameters         # Словарь с параметрами обработки данных

        self._received_data = {}                    # Переменная для хранения прочитанных данных

        self._file_init: str = str()                            # Файл с данными выставки датчиков
        self._files_measuring: list[MeasuringPair] = list()     # Список именованных кортежей с файлами с данными проездов

        # Словарь в котором будет храниться детальная конфигурация этапов обработки файлов.
        # Шаги обработки данных будут выполняться в соответствии с self._parameters, которые задаются при инициализации
        self._config = {
            'File_Classification': {
                'manual_file_classification': self._manual_file_classification,
                'auto_file_classification': self._auto_file_classification
            },
            'Raw_Data': {
                'plotting_raw_data': self.plotting_raw_data,
                'plotting_static_data': self.plotting_static_data
            }
        }

    # -------------------------------
    # Getters
    # -------------------------------
    def get_data(self):
        return self._received_data

    # ---------------------------------
    # Основная функция обработки данных
    # ---------------------------------
    def start(self):
        self._decoding()
        self._file_classification()
        self.raw_data_analys()

    # -------------------------------
    # Чтение данных из файлов
    # -------------------------------
    def _decoding(self):
        for filename in self._file_list:
            decoder = Decoder(f'{self._data_dir}/{filename}')
            decoder.decoding()
            self._received_data[filename] = decoder.get_data()

    # -------------------------------
    # Классификация файлов
    # -------------------------------
    def _file_classification(self):
        class_params: dir = self._config['File_Classification']
        user_params: dir = self._parameters['File_Classification']

        selected_func = class_params[user_params['mode']]
        selected_func(**user_params['kwargs'])

        # print(self._file_init)
        # pprint([file_measuring._asdict() for file_measuring in self._files_measuring])

    def _manual_file_classification(self, file_init: str, files_measuring: list[dict]):
        self._file_init = file_init
        for file_measuring in files_measuring:
            self._files_measuring.append(MeasuringPair(**file_measuring))

    def _auto_file_classification(self):
        pass

    # -------------------------------
    # Обработка исходных данных
    # -------------------------------
    def raw_data_analys(self):
        class_params: dir = self._config['Raw_Data']
        user_params: dir = self._parameters['Raw_Data']

        for key, value in user_params.items():
            if value:
                class_params[key]()

    def plotting_raw_data(self):
        """
        Создание графиков исходных данных, прочитанных из файлов self._files_measuring[_].data
        """
        for measuring_pair in self._files_measuring:
            filename = measuring_pair.data
            file_data = self._received_data[filename]

            # Построение графиков температуры и абсолютных величин ускорения и угловых скоростей
            canvas_Abs = Canvas(n_rows=3, n_cols=1)
            canvas_Abs.suptitle(f'Величины температуры и абсолютных величин ускорения и угловых скоростей из файла {filename}', weight='bold')
            canvas_Abs.plot(file_data['Time'] / 60,
                            [np.sqrt(file_data[f'Acc_X'] ** 2 + file_data[f'Acc_Y'] ** 2 + file_data[f'Acc_Z'] ** 2),
                             np.sqrt(file_data[f'Gyro_X'] ** 2 + file_data[f'Gyro_Y'] ** 2 + file_data[f'Gyro_Z'] ** 2),
                             file_data['Temp']],
                            color_names=[color_scheme['ABS_values']['Acc'],
                                         color_scheme['ABS_values']['Gyro'],
                                         color_scheme['ABS_values']['Temp']])
            canvas_Abs.grid_all_axes()
            canvas_Abs.set_axis_labels(x_label='Time, minutes',
                                       y_label=['acceleration, m / c**2', 'angular velocity, mgps', 'temperature, ---'])
            canvas_Abs.tight_layout()

            # Построение графиков ускорений
            canvas_Acc = Canvas(n_rows=3, n_cols=1)
            canvas_Acc.suptitle(f'Величины ускорений из файла {filename}', weight='bold')
            canvas_Acc.plot(file_data['Time'] / 60,
                            [file_data[f'Acc_{coord}'] for coord in ['X', 'Y', 'Z']],
                            label=['raw_data1', None, 'raw_data2'],
                            color_names=[color_scheme['RGB_classic']['X'],
                                         color_scheme['RGB_classic']['Y'],
                                         color_scheme['RGB_classic']['Z']])
            canvas_Acc.plot(file_data['Time'] / 60,
                            [KalmanFilter(file_data[f'Acc_{coord}'], file_data[f'Acc_{coord}'][0]).get_filtered_data()
                            for coord in ['X', 'Y', 'Z']],
                            label=['filtered_data1', None, 'filtered_data2'],
                            color_names=[color_scheme['RGB_dark']['X'],
                                         color_scheme['RGB_dark']['Y'],
                                         color_scheme['RGB_dark']['Z']],
                            linewidth=2.5)
            canvas_Acc.grid_all_axes()
            canvas_Acc.set_axis_labels(x_label='Time, minutes',
                                       y_label=[f'Acc_{coord}, m / c**2' for coord in ['X', 'Y', 'Z']])
            canvas_Acc.tight_layout()

            # Построение графиков угловых скоростей
            canvas_Gyro = Canvas(n_rows=3, n_cols=1)
            canvas_Gyro.suptitle(f'Величины угловых скоростей из файла {filename}', weight='bold')
            canvas_Gyro.plot(file_data['Time'] / 60,
                            [file_data[f'Gyro_{coord}'] for coord in ['X', 'Y', 'Z']],
                             color_names=[color_scheme['COP_classic']['X'],
                                          color_scheme['COP_classic']['Y'],
                                          color_scheme['COP_classic']['Z']])

            canvas_Gyro.grid_all_axes()
            canvas_Gyro.set_axis_labels(x_label='Time, minutes',
                                        y_label=[f'Gyro_{coord}, mgps'  for coord in ['X', 'Y', 'Z']])
            canvas_Gyro.tight_layout()

    def plotting_static_data(self, saving_path: str = None):
        """
        Создание графиков и распределений нулевых значений из файла self._file_init
        """
        filename = self._file_init
        file_data: np.typing.NDArray[float] = self._received_data[self._file_init]
        coords = ['X', 'Y', 'Z']

        # Ускорения
        canvas_Acc = Canvas(n_rows=3, n_cols=2, width_ratios=[3, 1])
        canvas_Acc.plot([[file_data['Time'] / 60, np.full(file_data["Time"].shape, np.nan, dtype=float)] for _ in range(3)],
                        [[file_data[f'Acc_{coord}'], np.full(file_data["Time"].shape, np.nan, dtype=float)] for coord in ['X', 'Y', 'Z']],
                        color_names=[[color_scheme['RGB_classic']['X'], None],
                                     [color_scheme['RGB_classic']['Y'], None],
                                     [color_scheme['RGB_classic']['Z'], None]])

        canvas_Acc.suptitle(f'Анализ ускорений по осям из файла {filename}', weight='bold')
        canvas_Acc.set_axis_labels(x_label=['Time, minutes', None],
                                   y_label=[['Acc_X, m / c**2', None],
                                            ['Acc_Y, m / c**2', None],
                                            ['Acc_Z, m / c**2', None]])
        for n_row in range(3):
            ax = cast(Axes, canvas_Acc.ax[n_row, 0])
            ax.axhline(np.mean(file_data[f'Acc_{coords[n_row]}']),
                       color=color_scheme['RGB_dark'][coords[n_row]],
                       linestyle='--', linewidth=2.5)
            ax.annotate(f'Mean Acc_{coords[n_row]} = {np.mean(file_data[f'Acc_{coords[n_row]}']).round(3)}',
                          xy=(0.64, 0.88), xycoords='axes fraction', size=10,
                          bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=2))
            ax.grid()

        # Угловые скорости
        canvas_Gyro = Canvas(n_rows=3, n_cols=2, width_ratios=[3, 1])
        canvas_Gyro.plot([[file_data['Time'] / 60, np.full(file_data["Time"].shape, np.nan, dtype=float)] for _ in range(3)],
                        [[file_data[f'Gyro_{coord}'], np.full(file_data["Time"].shape, np.nan, dtype=float)] for coord in ['X', 'Y', 'Z']],
                        color_names=[[color_scheme['COP_classic']['X'], None],
                                     [color_scheme['COP_classic']['Y'], None],
                                     [color_scheme['COP_classic']['Z'], None]])

        canvas_Gyro.suptitle(f'Анализ ускорений по осям из файла {filename}', weight='bold')
        canvas_Gyro.set_axis_labels(x_label=['Time, minutes', None],
                                   y_label=[['Gyro_X, m / c**2', None],
                                            ['Gyro_Y, m / c**2', None],
                                            ['Gyro_Z, m / c**2', None]])
        for n_row in range(3):
            ax = cast(Axes, canvas_Gyro.ax[n_row, 0])
            ax.axhline(np.mean(file_data[f'Gyro_{coords[n_row]}']),
                       color=color_scheme['COP_dark'][coords[n_row]],
                       linestyle='--', linewidth=2.5)
            ax.annotate(f'Mean Gyro_{coords[n_row]} = {np.mean(file_data[f'Gyro_{coords[n_row]}']).round(3)}',
                          xy=(0.64, 0.88), xycoords='axes fraction', size=10,
                          bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", lw=2))
            ax.grid()

        # Гистограммы
        n_bins = 100
        for n_row in range(3):
            ax = cast(Axes, canvas_Acc.ax[n_row, 1])
            ax.hist(file_data[f'Acc_{coords[n_row]}'], bins=n_bins, color='gray')
            ax.set_yticks([])
            ax.set_facecolor('whitesmoke')
            ax.annotate(f'σ = {np.round(np.std(file_data[f'Acc_{coords[n_row]}']), 6)}', xy=(0.64, 0.88),
                        xycoords='axes fraction', size=10,
                        bbox=dict(boxstyle="round,pad=0.3", fc="lightgray", ec="gray", lw=2))

            ax = cast(Axes, canvas_Gyro.ax[n_row, 1])
            ax.hist(file_data[f'Gyro_{coords[n_row]}'], bins=n_bins, color='gray')
            ax.set_yticks([])
            ax.set_facecolor('whitesmoke')
            ax.annotate(f'σ = {np.round(np.std(file_data[f'Gyro_{coords[n_row]}']), 6)}', xy=(0.64, 0.88),
                        xycoords='axes fraction', size=10,
                        bbox=dict(boxstyle="round,pad=0.3", fc="lightgray", ec="gray", lw=2))


        canvas_Acc.tight_layout()
        canvas_Gyro.tight_layout()

        if saving_path:
            canvas_Acc.save_figure(f'{saving_path}/{name_of_file(filename, ".bin")}_Acc.png')
            canvas_Acc.save_figure(f'{saving_path}/{name_of_file(filename, ".bin")}_Gyro.png')

    # -------------------------------

##########################################################

if __name__ == '__main__':
    processing_params = {
        'File_Classification': {

            # 'mode': 'auto_file_classification',
            # 'kwargs': {}

            'mode': 'manual_file_classification',
            'kwargs': {
                'file_init': 'telega_2025-06-10_STM_Init.bin',
                'files_measuring': [
                   {'buffer': 'telega_2025-06-10_STM_RawData_2.bin', 'data': 'telega_2025-06-10_STM_RawData_3.bin'},
                   {'buffer': 'telega_2025-06-10_STM_RawData_4.bin', 'data': 'telega_2025-06-10_STM_RawData_5.bin'}
                ]
            }
        },
        'Raw_Data': {
            'plotting_raw_data': True,
            'plotting_static_data': True
        }
    }
    dir_path = f'{CWD}/10.06.25'
    files = [f for f in os.listdir(dir_path) if (os.path.isfile(os.path.join(dir_path, f)) and ('.bin' in f))]

    analyser = DataProcessing(f'{CWD}/10.06.25', files, processing_params)
    analyser.start()
    # analyser.plotting_raw_data()
    # analyser.plotting_zero_data('telega_2025-06-10_STM_Init.bin')
    plt.show()
