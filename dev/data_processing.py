# System imports
import os
import json
import re
import shutil
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
from data_analys import *

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
        self._data_dir: str = data_dir                              # Директория, в которой находятся файлы
        self._saving_dir: str = f'{data_dir}/Обработка данных'      # Директория сохранения результатов обработки данных

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
                'plotting_raw_data': self._plotting_raw_data,
                'plotting_init_data': self._plotting_init_data,
                'plotting_buffers_data': self._plotting_buffers_data
            }
        }

        if os.path.exists(self._saving_dir):
            shutil.rmtree(self._saving_dir)
            os.mkdir(self._saving_dir)

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
        self._raw_data_analys()

    # -------------------------------
    # Чтение данных из файлов
    # -------------------------------
    def _decoding(self):
        print('# -------------------------------')
        for filename in self._file_list:
            print(f'Чтение данных из файла: {filename}')

            decoder = Decoder(f'{self._data_dir}/{filename}')
            decoder.decoding()
            self._received_data[filename] = decoder.get_data()

    # -------------------------------
    # Классификация файлов
    # -------------------------------
    def _file_classification(self):
        print('# -------------------------------')
        print('Классификация данных')
        class_params: dir = self._config['File_Classification']
        user_params: dir = self._parameters['File_Classification']

        selected_func = class_params[user_params['mode']]
        selected_func(**user_params['kwargs'])

        print(f'Файл выставки: {self._file_init}')

        print('Файлы проездов:')
        pprint([self._files_measuring[i].data for i in range(len(self._files_measuring))])

        print('Файлы буферов:')
        pprint([self._files_measuring[i].buffer for i in range(len(self._files_measuring))])

    def _manual_file_classification(self, file_init: str, files_measuring: list[dict]):
        self._file_init = file_init
        for file_measuring in files_measuring:
            self._files_measuring.append(MeasuringPair(**file_measuring))

    def _auto_file_classification(self,
                                  template_init_filename: str,
                                  template_measurement_filename: str,
                                  template_measurement_buffer_filename: str):
        file_init: str = None
        files_measurement: list[str] = []
        files_measurement_buffer: list[str] = []
        measurement_pairs: list[dict] = []

        for filename in self._file_list:
            if template_init_filename in filename:
                file_init = filename
            elif template_measurement_buffer_filename in filename:
                files_measurement_buffer.append(filename)
            elif template_measurement_filename in filename:
                files_measurement.append(filename)

        if not file_init:
            raise RuntimeError('Не найден файл с выставкой данных по переданному шаблонному названию')

        if not len(files_measurement):
            raise RuntimeError('Не найдено ни одного файла с измерениями, соответствующие переданному шаблонному имени.')

        if len(files_measurement) != len(files_measurement_buffer):
            raise RuntimeError('Количество файлов измерений не совпадает с количеством файлов с буферными данными.\n'
                               'Необходима ручная классификация файлов!')

        for filename in files_measurement:
            pattern = re.compile(f"{template_measurement_filename}_(.*?).bin")
            file_index = pattern.search(filename).group(1)

            for filename_buffer in files_measurement_buffer:
                if file_index in filename_buffer[filename_buffer.find(template_measurement_filename):]:
                    measurement_pairs.append({'buffer': filename_buffer, 'data': filename})

        self._manual_file_classification(file_init, measurement_pairs)


    # -------------------------------
    # Обработка исходных данных
    # -------------------------------
    def _raw_data_analys(self):
        print('# -------------------------------')
        class_params: dir = self._config['Raw_Data']
        user_params: dir = self._parameters['Raw_Data']

        for key, value in user_params.items():
            if value:
                class_params[key](**user_params['kwargs'])

    def _plotting_init_data(self):
        print('Построение графиков данных выставки')
        self._plotting_static_data(self._file_init, f'{self._saving_dir}/Данные выставки датчиков')

    def _plotting_buffers_data(self):
        for i in range(len(self._files_measuring)):
            print(f'Построение графиков буферных данных из файла {self._files_measuring[i].buffer}')

            # Создадим директорию {self._saving_dir}/Данные проездов/<название файла с данными проезда>
            saving_path = f'{self._saving_dir}/Данные проездов'
            if not os.path.exists(saving_path):
                os.mkdir(saving_path)

            saving_path += f'/{name_of_file(self._files_measuring[i].data, ".bin")}'
            if not os.path.exists(saving_path):
                os.mkdir(saving_path)

            # Построим графики
            self._plotting_static_data(self._files_measuring[i].buffer, saving_path)

    def _plotting_raw_data(self):
        """
        Создание графиков исходных данных, прочитанных из файлов self._files_measuring[_].data
        """
        for measuring_pair in self._files_measuring:
            filename = measuring_pair.data
            print(f'Построение данных из файла {filename}')
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
                            color_names=[color_scheme['RGB_classic']['X'],
                                         color_scheme['RGB_classic']['Y'],
                                         color_scheme['RGB_classic']['Z']])
            canvas_Acc.plot(file_data['Time'] / 60,
                            [KalmanFilter(file_data[f'Acc_{coord}'], file_data[f'Acc_{coord}'][0]).get_filtered_data()
                            for coord in ['X', 'Y', 'Z']],
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
            canvas_Gyro.plot(file_data['Time'] / 60,
                            [KalmanFilter(file_data[f'Gyro_{coord}'], file_data[f'Gyro_{coord}'][0]).get_filtered_data()
                            for coord in ['X', 'Y', 'Z']],
                            color_names=[color_scheme['COP_dark']['X'],
                                         color_scheme['COP_dark']['Y'],
                                         color_scheme['COP_dark']['Z']],
                            linewidth=2.5)

            canvas_Gyro.grid_all_axes()
            canvas_Gyro.set_axis_labels(x_label='Time, minutes',
                                        y_label=[f'Gyro_{coord}, mgps'  for coord in ['X', 'Y', 'Z']])
            canvas_Gyro.tight_layout()

            # Сохраним полученные графики
            saving_path = f'{self._saving_dir}/Данные проездов'
            if not os.path.exists(saving_path):
                os.mkdir(saving_path)

            saving_path += f'/{name_of_file(filename, ".bin")}'
            if not os.path.exists(saving_path):
                os.mkdir(saving_path)

            canvas_Abs.save_figure(f'{saving_path}/{name_of_file(filename, ".bin")}_Abs.png')
            canvas_Acc.save_figure(f'{saving_path}/{name_of_file(filename, ".bin")}_Acc.png')
            canvas_Gyro.save_figure(f'{saving_path}/{name_of_file(filename, ".bin")}_Gyro.png')

    def _plotting_static_data(self, filename: str, saving_path: str = None):
        """
        Создание графиков и распределений величин из filename
        """
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
            if not os.path.exists(saving_path):
                os.mkdir(saving_path)
            canvas_Acc.save_figure(f'{saving_path}/{name_of_file(filename, ".bin")}_Acc.png')
            canvas_Gyro.save_figure(f'{saving_path}/{name_of_file(filename, ".bin")}_Gyro.png')

    # -------------------------------

##########################################################

if __name__ == '__main__':
    processing_params = {
        'File_Classification': {

            'mode': 'auto_file_classification',
            'kwargs': {
                'template_init_filename': 'Init',
                'template_measurement_filename': 'Measurement',
                'template_measurement_buffer_filename': 'Measurement_Buffer'
            }

            # 'mode': 'manual_file_classification',
            # 'kwargs': {
            #     'file_init': 'telega_2025-06-10_STM_Init.bin',
            #     'files_measuring': [
            #        {'buffer': 'telega_2025-06-10_STM_RawData_2.bin', 'data': 'telega_2025-06-10_STM_RawData_3.bin'},
            #        {'buffer': 'telega_2025-06-10_STM_RawData_4.bin', 'data': 'telega_2025-06-10_STM_RawData_5.bin'}
            #     ]
            # }
        },
        'Raw_Data': {
            'plotting_init_data': True,
            'plotting_buffers_data': True,
            'plotting_raw_data': True,
            'kwargs': {}
        }
    }
    dir_path = f'{CWD}/10.06.25_copy'
    files_ = [f for f in os.listdir(dir_path) if (os.path.isfile(os.path.join(dir_path, f)) and ('.bin' in f))]

    analyser = DataProcessing(dir_path, files_, processing_params)
    analyser.start()

    # plt.show()
