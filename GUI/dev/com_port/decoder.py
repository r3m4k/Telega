# System imports
import enum
import traceback
import binascii

# External imports
from multiprocessing import Queue

# User imports


##########################################################

class Decoder:
    STM_Stages = enum.Enum(
        value='STM_Stages',
        names=('Want7E', 'WantE7', 'WantSize', 'WantFormat', 'WantPacketBody', 'WantConSum')
    )

    GPS_Stages = enum.Enum(
        value='GPS_Stages',
        names=('WantBegin', 'WantIdentifier', 'WantPacketBody', 'WantConSumFirst', 'WantConSumSecond')
    )

    def __init__(self):
        pass

    def decoding(self, type_name: str, source_queue: Queue, output_queue: Queue, duplicate_queue: Queue, msg_queue: Queue):
        try:
            if (type_name == "STM") or (type_name == "GPS"):
                self.decoding_STM(source_queue, output_queue, duplicate_queue, msg_queue)
            else:
                raise RuntimeError('Неправильно передан параметр type_name.\n'
                                   f'Он может принимать значения "STM" или "GPS", а передан type_name = {type_name}')
        except Exception as error:
            msg_queue.put(f'Critical__type_name = {type_name}\n{error}\n{traceback.format_exc()}')

    def decoding_STM(self, source_queue: Queue, output_queue: Queue, duplicate_queue: Queue, msg_queue: Queue):
        stages = self.STM_Stages    # Создадим новую переменную с перечислением self.STM_Stages для краткости дальнейшего кода
        stage = stages.Want7E
        titles = ['Time', 'Acc_X', 'Acc_Y', 'Acc_Z', 'Gyro_X', 'Gyro_Y', 'Gyro_Z', 'Temp']
        package_type: str = ''

        bytes_buffer = []   # Буфер для байтов, прочитанных из очереди данных
        data = {}           # Словарь, в который сохраним пакет полученных данных, с ключами titles
        size = 0            # Количество байтов данных в посылке
        index = 0           # Индекс байта в пакете данных
        con_sum = 0         # Посчитанная контрольная сумма
        Con_Sum = 0         # Полученная контрольная сумма

        while True:
            if source_queue.empty():
                continue

            bt = source_queue.get()
            duplicate_queue.put(bt)
            try:
                val = int(binascii.hexlify(bt), 16)
            except ValueError:
                # msg_queue.put(f'Warning__{traceback.format_exc()}')
                continue

            match stage:
                case stages.Want7E:
                    if val == 126:
                        stage = stages.WantE7
                        con_sum = val
                        # Обнулим накопленные значения
                        index = 0
                        data = {}
                        bytes_buffer = []
                    else:
                        stage = stages.Want7E

                case stages.WantE7:
                    if val == 231:
                        stage = stages.WantFormat
                        con_sum += val
                    else:
                        stage = stages.Want7E

                case stages.WantFormat:
                    package_format = val
                    con_sum += val

                    if package_format == 0xff:      # Формат команды из двух байтов
                        package_type = 'Command'
                        size = 2
                        stage = stages.WantPacketBody

                    elif package_format == 0xC8:    # Формат пакета данных
                        package_type = 'Data'
                        stage = stages.WantSize

                case stages.WantSize:
                    size = val
                    con_sum += val
                    stage = stages.WantPacketBody

                case stages.WantPacketBody:

                    if index < size:
                        index += 1
                        con_sum += val
                        bytes_buffer.append(val)

                    if index == size:
                        stage = stages.WantConSum

                case stages.WantConSum:
                    Con_Sum = val
                    # Сравним Con_Sum и младшие 8 бит con_sum
                    if Con_Sum == (con_sum & 255):
                        if package_type == 'Data':
                            for i in range(size // 2):
                                # Сохраним полученные данные, полученные в LittleEndianMode в словарь
                                value = self.mod_code(bytes_buffer[2 * i], bytes_buffer[2 * i + 1])
                                if i == 0:
                                    # Для Time
                                    data[titles[i]] = round(value * 0.25, 3)
                                elif i in range(1, size // 2 - 1):
                                    # Для Acc_XYZ и Gyro_XYZ
                                    data[titles[i]] = value / 1000
                                elif i == (size // 2) - 1:
                                    # Для Temp
                                    data[titles[i]] = value / 100
                            output_queue.put(data)

                        elif package_type == 'Command':
                            if bytes_buffer == [0xba, 0xab]:
                                msg_queue.put('Command__stop_InitialSetting')
                            break


                    else:
                        msg_queue.put('Warning__Контрольная сумма не сошлась')
                    stage = stages.Want7E

    @staticmethod
    def mod_code(low_bit, high_bit):
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

    @staticmethod
    def decoding_GPS(source_queue: Queue, output_queue: Queue, duplicate_queue: Queue, msg_queue: Queue):
        # Создадим список именованных констант, которые будут использоваться вместо Enum
        WantBegin: int = 0
        WantIdentifier: int = 1
        WantPacketBody: int = 2
        WantConSumFirst: int = 3
        WantConSumSecond: int = 4
        ####################
        # Список ASCII кодов используемых символов
        StartCode = 0x24
        SeparatorCode = 0x2A
        CRCode = 0x0D
        LFCode = 0x0A
        ####################

        stage: int = WantBegin
        data: str = ''      # Полученная строка
        header: str = ''    # 5-буквенный идентификатор сообщения. GPGLL — координаты, широта/долгота датчика
        index = 0           # Индекс байта в пакете данных
        con_sum = 0         # Посчитанная контрольная сумма
        Con_Sum = ''        # Полученная контрольная сумма

        while True:
            if source_queue.empty():
                continue

            bt = source_queue.get()
            duplicate_queue.put(bt)
            val = int(binascii.hexlify(bt), 16)

            if stage == WantBegin:
                if val == StartCode:
                    stage = WantIdentifier
                    index = 0
                    data = '$'

            elif stage == WantIdentifier:
                header += chr(val)
                if index < 5:   # 5-буквенный идентификатор сообщения
                    index += 1
                if index == 5:
                    if header == 'GPGLL':
                        # Рассматриваем только строки с данными текущих координат
                        stage = WantPacketBody
                        con_sum = 0x50      # XOR header
                        data += 'GPGLL'
                    else:
                        stage = WantBegin
                        data = ''
                        header = ''
                        con_sum = 0

            elif stage == WantPacketBody:
                data += chr(val)
                if val != SeparatorCode:
                    con_sum ^= val
                else:
                    stage = WantConSumFirst

            elif stage == WantConSumFirst:
                # Считаем первый символ контрольной суммы
                Con_Sum += chr(val)
                stage = WantConSumSecond

            elif stage == WantConSumSecond:
                # Считаем второй символ контрольной суммы
                Con_Sum += chr(val)
                if Con_Sum == f'{con_sum:02X}':
                    output_queue.put(data)
                else:
                    msg_queue.put(f'Warning__'
                                  f'{data}      '
                                  f'Контрольная сумма не сошлась: {Con_Sum} | {con_sum:02X}')
                stage = WantBegin
                Con_Sum = ''