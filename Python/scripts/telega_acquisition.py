# System imports
import os
from datetime import datetime
from pathlib import Path
from pprint import pprint

# External imports
import numpy as np

# User imports
from dev.decoding import DecoderProtocol, TelegaDecoder, TelegaData
from byte_source import BytesSource, ReadError
from byte_source.com_port import ComPortSetting
from byte_source.file_source import FileSourceSetting
from scripts.utils import confirm_from_console


#############################################
# Константы для работы программы
#############################################

# Количество пакетов данных, по которым будет построен график
N = 100

# Директория для сохранения полученных графиков
save_dir = Path(__file__).resolve().parent / 'results' / str(datetime.now().date())
save_dir.mkdir(parents=True, exist_ok=True)


#############################################
# Перенаправление данных в декодер
#############################################

print('# -----------------------------------------')

bytes_source: BytesSource
bytes_source_num = int(input('Выберите тип источника данных:\n'
                             '| 1. COM-порт\n'
                             '| 2. Записанный log файл\n'
                             '--> '))
print()
if bytes_source_num == 1:
    bytes_source = ComPortSetting().get_bytes_source()
elif bytes_source_num == 2:
    bytes_source = FileSourceSetting().get_bytes_source()
else:
    print('❌ Ошибка ввода')
    exit(1)


decoder: DecoderProtocol[list[TelegaData]] = TelegaDecoder()

with bytes_source as bt_src:
    try:
        while decoder.data_len != N:
            decoder.byte_processing(bt_src.read_byte())
            print(f'\r⏳ Чтение данных...    #{decoder.data_len}/{N}', end="", flush=True)
        print()
        print('✅ Чтение данных завершено\n')

    except ReadError as err:
        print(f'\nОшибка чтения пакета #{decoder.data_len}\n'
              f'{err}\n')
        print(f'Проводить анализ прочитанных данных?')

        if not confirm_from_console():
            exit(1)

print(decoder)
exit(0)


# print('Полученные данные:\n')
# pprint(decoder.received_data)

#############################################
# Построение графиков величин и их распределение
#############################################

SENSOR_1_ID = 1;    DATA_LEN_SENSOR_1 = len(decoder.received_data[SENSOR_1_ID])
SENSOR_2_ID = 2;    DATA_LEN_SENSOR_2 = len(decoder.received_data[SENSOR_2_ID])

canvas_config = CanvasConfig()

canvas_config.n_rows = 2; canvas_config.n_cols = 2
canvas_config.ax_kwargs['width_ratios'] = [3, 1]

canvas_config.x_data = [
    np.array([decoder.received_data[SENSOR_1_ID][i].time for i in range(DATA_LEN_SENSOR_1)]),
    np.array([decoder.received_data[SENSOR_2_ID][i].time for i in range(DATA_LEN_SENSOR_2)])
]

adc_values = {
    SENSOR_1_ID: np.array([decoder.received_data[SENSOR_1_ID][i].adc_value * int(decoder.received_data[SENSOR_1_ID][i].gain)
                           for i in range(DATA_LEN_SENSOR_1)]),
    SENSOR_2_ID: np.array([decoder.received_data[SENSOR_2_ID][i].adc_value * int(decoder.received_data[SENSOR_2_ID][i].gain)
                           for i in range(DATA_LEN_SENSOR_2)])
}

canvas_config.y_data = np.array([adc_values[SENSOR_1_ID], adc_values[SENSOR_2_ID]])

canvas_config.color_names = [color_scheme['RGB_classic']['X'],
                             color_scheme['RGB_classic']['Y']]

canvas_config.dark_color_names = [color_scheme['RGB_dark']['X'],
                                  color_scheme['RGB_dark']['Y']]

canvas_config.y_label = [f'HX711_{SENSOR_1_ID}', f'HX711_{SENSOR_2_ID}']

canvas_config.annotation = [
    f'Mean ADC_Sensor1 = {np.mean(adc_values[SENSOR_1_ID]).round(6)}',
    f'Mean ADC_Sensor2 = {np.mean(adc_values[SENSOR_2_ID]).round(6)}'
]

plotter_ADC = Plotter(canvas_config)
plotter_ADC.plotting_Ndim_static(dim=2)

# -------------------------------------

print('💾 Сохранение графиков...')

plotter_ADC.save(f'{save_dir}/adc_values.png')


#############################################
# Сохранение данных в csv файл
#############################################

print('📥 Сохранение данных в csv файл')

csv_file = save_dir / 'Записанные данные.csv'
decoder.save_received_data(csv_file)

#############################################
# Завершение программы
#############################################

print('🎯 Успешное завершение программы')

# Откроем директорию сохранения в проводнике
os.startfile(save_dir)