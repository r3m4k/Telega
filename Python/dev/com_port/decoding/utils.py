# System imports
import struct

# External imports

# User imports
from .data_description import TriaxialData

#############################################


def bytes_to_float(byte_list: list[bytes]) -> float:
    """ Перевод четырёх байтов в float """
    data_bytes = b''.join(byte_list)
    return struct.unpack('f', data_bytes)[0]


def bytes_to_uint32(byte_list: list[bytes]) -> int:
    """ Перевод четырёх байтов в целое число """
    data_bytes = b''.join(byte_list)
    return struct.unpack('<I', data_bytes)[0]


def bytes_to_triaxial(byte_list: list[bytes]) -> TriaxialData:
    """ Перевод списка байтов в TriaxialData """

    if len(byte_list) != 12:
        raise RuntimeError('The length of the byte_list must be 12 to convert to TriaxialData')

    return TriaxialData(
        x_coord=bytes_to_float(byte_list[0:4]),
        y_coord=bytes_to_float(byte_list[4:8]),
        z_coord=bytes_to_float(byte_list[8:12])
    )


#############################################


if __name__ == '__main__':

    # ---------------------------------------
    # Проверка bytes_to_uint32
    print('Проверка bytes_to_uint32')

    bytes_list = [
        [b'\x7a', b'\x28', b'\x00', b'\x00'],
        [b'\x7b', b'\x28', b'\x00', b'\x00']
    ]

    for i in range(len(bytes_list)):
        print(f'{bytes_list[i]} = {bytes_to_uint32(bytes_list[i])}')

    # ---------------------------------------
    # Проверка bytes_to_triaxial
    print('Проверка bytes_to_triaxial')

    bytes_list = [
        [b'\xd0', b'\x0f', b'\x49', b'\x40'] * 3
    ]

    for i in range(len(bytes_list)):
        print(f'{bytes_list[i]} = {bytes_to_triaxial(bytes_list[i])}')

    # ---------------------------------------
