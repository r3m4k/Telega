# System imports
import os

# External imports
import numpy as np

# User imports


##########################################################

__all__ = [
    'name_of_file',
    'cumulative_trapezoidal_integral',
    'trapezoidal_integration',
    'linear_subtraction',
    'writing_to_csv_file'
]

##########################################################


def name_of_file(path, extension):
    """
    Получение название файла из его абсолютного или относительного пути без его расширения.
    :param path: Путь к файлу.
    :param extension: Расширение файла. Пример: ".log".
    :return: Имя файла без расширения и пути расположения.
    """
    file = path
    for i in range(0, file.count('/')):
        file = file[file.find('/') + 1:]

    return file[:file.find(extension)]

# --------------------------------------------------------

def cumulative_trapezoidal_integral(x_value, y_value):
    """
    Вычисление кумулятивного интеграла методом трапеций.
    """
    result = 0
    integrated_array = np.zeros_like(x_value)

    for index in range(len(x_value) - 1):
        result += (x_value[index + 1] - x_value[index]) * (y_value[index] + y_value[index + 1]) / 2
        integrated_array[index + 1] = result

    return integrated_array

# --------------------------------------------------------

def trapezoidal_integration(array, h):
    """
    Интегрирование функции, заданной точками, методом трапеций.
    """
    return np.sum(array[:-1] + array[1:]) * h / 2

# --------------------------------------------------------

def linear_subtraction(array: np.typing.NDArray, final_value: float):
    """
    Вычитание линейного сдвига
    """
    line_coefficient = (array[-1] - final_value) / len(array)
    return array - line_coefficient * np.arange(len(array))

# --------------------------------------------------------

def float_to_csv_format(value):
    """
    Перевод числа с плавающей точкой в строку для csv файла.
    """
    return str(round(value, 8)).replace(".", ",")

# --------------------------------------------------------

def writing_to_csv_file(titles: list[str], array_list: list[np.typing.NDArray], saving_dir: str, saving_name: str):
    """
    Сохранение данных в csv файл.
    :param titles: список заголовков
    :param array_list: список массивов с данными
    :param saving_dir: директория сохранения итогового файла
    :param saving_name: имя итогового файла
    """
    if len(titles) != len(array_list):
        raise ValueError('titles and array_list have different number of elements!\n'
                         f'len(titles) = {len(titles)}, len(array_list) = {len(array_list)}')

    if not os.path.isdir(saving_dir):
        raise FileNotFoundError(f'No such directory: {saving_dir}')

    if '.csv' not in saving_name:
        saving_name += '.csv'

    csv_file = open(f'{saving_dir}/{saving_name}', 'w')

    # Запишем заголовки
    csv_file.write(titles[0])
    for title in titles[1:]:
        csv_file.write(f' {title}')
    csv_file.write('\n')

    # Запишем данные
    for row in range(len(array_list[0])):
        for col in range(len(array_list)):
            if col == 0:
                csv_file.write(float_to_csv_format(array_list[col][row]))
            else:
                csv_file.write(f' {float_to_csv_format(array_list[col][row])}')
        csv_file.write('\n')

    csv_file.close()

# --------------------------------------------------------
