# System imports
import os

# External imports
import numpy as np

# User imports
from data_processing import DataProcessing
from ..consts import CWD


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
            #     'file_init': 'telega_2025-08-12_STM_Init.bin',
            #     'files_measuring': [
            #        {'buffer': 'telega_2025-08-12_STM_Init.bin', 'data': 'telega_2025-08-12_STM_RawData_1.bin'}
            #     ]
            # }
        },
        'Raw_Data': {
            'plotting_init_data': True,
            'plotting_buffers_data': True,
            'plotting_raw_data': True,
            'kwargs': {'plot_filtered_data': True}
        },
        'Analysis': {
            'plotting_analysed_data': True,
            'kwargs': {}
        }

    }
    dir_path = f'{CWD}/10.06.25_copy'
    # dir_path = f'{CWD}/test_rotation'
    files_ = [f for f in os.listdir(dir_path) if (os.path.isfile(os.path.join(dir_path, f)) and ('.bin' in f))]

    analyser = DataProcessing(dir_path, files_, processing_params)
    analyser.start()
