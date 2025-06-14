import os
from time import sleep
import binascii
import traceback
import enum

from threading import Thread
from multiprocessing import Process, Queue, Pipe
from multiprocessing.managers import BaseManager, NamespaceProxy
from multiprocessing.context import ProcessError

if os.name == 'nt':  # sys.platform == 'win32':
    from serial.tools.list_ports_windows import comports
elif os.name == 'posix':
    from serial.tools.list_ports_posix import comports
import serial
from serial.serialutil import SerialException

from PyQt5.QtCore import QObject, pyqtSignal

from printing import Printing


"""
Для корректной работы нескольких процессов и взаимодействий между ними создадим класс MyManager,
который создает служебный процесс, в котором размещается централизованная версия разделяемого объекта. 
Менеджер создает так называемый прокси‑объект для каждого процесса, и процессы обращаются именно к прокси‑объекту.
"""


def get_ComPorts() -> dir:
    iterator = comports(include_links=False)
    res = {'-----': {"desc": "Здесь будут отображаться дескриптор выбранного COM порта"}}
    for n, (_port, desc, hwid) in enumerate(iterator, 1):
        res[_port] = {"desc": desc, "hwid": hwid}

    return res


BAUDRATE = {"STM": 115200, "GPS": 4800}       # Скорость работы COM порта


class MyManager(BaseManager):
    pass


class COM_Port:
    # Формат команд: 2 байта - заголовок, 1 байт - формат посылки, 2 байта - команда, 1 байт - контрольная сумма
    commands = {
        "start_InitialSetting":    bytes([0x7e, 0xe7, 0xff, 0xab, 0xba, 0xc9]),
        "start_Measuring":         bytes([0x7e, 0xe7, 0xff, 0xbc, 0xcb, 0xeb]),
        "stop_Measuring":          bytes([0x7e, 0xe7, 0xff, 0xcd, 0xdc, 0x0d]),
        "stop_CollectingData":     bytes([0x7e, 0xe7, 0xff, 0xde, 0xed, 0x2f])
    }

    received_msg = {
        "confirmation_Message":    bytes([0x7e, 0xe7, 0xff, 0xaa, 0xaa, 0xb8, 0, 0]),
        "end_of_InitialSetting":   bytes([0x7e, 0xe7, 0xff, 0xba, 0xab, 0xc9, 0, 0])
    }

    def __init__(self):
        self.port = serial.Serial()         # COM порт, с которым ведётся работа в данном модуле

    def __del__(self):
        self.port.close()

    def startMeasuring(self, com_port_name: str, baudrate: int,
                       data_queue: Queue, command_pipe: Pipe, msg_queue: Queue,
                       command = ''):

        # При возникновении любого неучтённого исключения перенаправим его в self.msg_queue
        try:
            # Откроем COM порт
            try:
                self.port = serial.Serial(port=com_port_name, baudrate=baudrate, timeout=1)
            except serial.serialutil.SerialException:
                msg_queue.put(f'Warning__\n{traceback.format_exc()}')
                msg_queue.put(f'Error__Ошибка открытия {com_port_name}')
                return

            try:
                if command != '':
                    # Отправим команду по COM порту
                    if not self.decode_Command(command, msg_queue):
                        return

            except serial.serialutil.SerialException or RuntimeError:
                msg_queue.put(f'Warning__\n{traceback.format_exc()}')
                msg_queue.put(f'Error__Ошибка отправки команды по {com_port_name}')
                return

            # Начнём чтение данных
            msg_queue.put(f'Info__Начало чтения данных из {self.port.port}')
            try:
                self.reading_ComPort(data_queue, command_pipe, msg_queue)
            except SerialException:
                msg_queue.put(f'Warning__{traceback.format_exc()}')
                msg_queue.put(f'Error__Ошибка чтения порта {self.port.port}')

        except Exception as error:
            msg_queue.put(f'Critical__\n{error}\n{traceback.format_exc()}')

    def reading_ComPort(self, data_queue: Queue, command_pipe: Pipe, msg_queue: Queue):
        while True:
            if not command_pipe.poll():
                # Если нет поступивших команд, то читаем данные из СOM порта
                data_queue.put(self.port.read(1))
            else:
                _ = self.decode_Command(str(command_pipe.recv()), msg_queue)
                break   # Остановим чтение из com порта


    def decode_Command(self, command: str, msg_queue: Queue):
        try:
            receive_command = command.split('__')[1]
            if receive_command in self.commands:
                return self.send_Command(receive_command, msg_queue)
            else:
                msg_queue.put(f'Warning__Команда не распознана')

        except Exception:
            msg_queue.put(f'Warning__Неправильно передана команда {command}')
            raise RuntimeError('Неправильно передана команда')
        return False    # Если произошла ошибка, то вернём False

    def send_Command(self, command: str, msg_queue):
        msg_queue.put(f'Info__Отправка команды {command} по {self.port.port}')
        status = True       # Статус отправления команды
        try:
            self.port.reset_input_buffer()
            self.port.write(self.commands[command])
            msg = self.port.read(size=len(self.received_msg['confirmation_Message']))
            if msg == self.received_msg['confirmation_Message']:
                msg_queue.put('Info__Команда успешно принята устройством')
            else:
                msg_queue.put(f'Warning__Ошибка чтения команды устройством\n{msg}')
                status = False
        except Exception:
            msg_queue.put(f'Warning__{traceback.format_exc()}')
            msg_queue.put(f'Error__Ошибка отправки команды по {self.port.port}')
            status = False

        return status


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
                msg_queue.put(f'Warning__{traceback.format_exc()}')
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

########## Прокси классы ##########
"""
По умолчанию NamespaceProxy позволяет нам обращаться ко всем публичным функциям
и читать и изменять все публичные поля класса, поэтому ничего не изменяем.
Фактически, добавили эти классы для читаемости кода.
"""
class COM_PortProxy(NamespaceProxy):
    pass

class DecodeProxy(NamespaceProxy):
    pass

###################################

class COM_Port_GUI(QObject):
    """
    Базовый класс для управления COM портом из GUI
    """
    MyManager.register('ComPort', COM_Port, COM_PortProxy)
    MyManager.register('Decoder', Decoder, DecodeProxy)

    NewData_Signal = pyqtSignal(dict)
    Error_ComPort = pyqtSignal(dict)

    def __init__(self, printer: Printing, type_port: str):
        super().__init__()
        self.printer = printer              # Объект, с помощью которого будем выводить информацию в GUI, stdout и logger
        self.type_port = type_port          # Тип подключённого датчика по данному порту: STM или GPS
        self.processingFlag = False         # Флаг необходимости анализировать данные. Равен True после self.startMeasuring
                                            # И равен False после self.stopMeasuring
        self.portName = ''                  # Имя COM порта
        self.savingFileName = ''            # Имя файла, куда будут сохраняться данные из COM порта
        self.isProcessesActive = False      # Флаг работы процессов

        self.manager = MyManager()
        try:
            self.manager.start()
        except ProcessError as error:
            self.printer.printing(error)


        self.ComPort_Data = Queue()     # Очередь, куда будет записываться все данные, полученные из self.port
        self.Decoded_Data = Queue()     # Очередь, куда будет записываться декодированные данные из ComPort_Data
        self.Duplicate_Queue= Queue()   # Очередь, куда будет дублироваться данные из self.ComPort_Data для записи данных в log файл
        self.MessageQueue = Queue()     # Очередь сообщений, полученных из различных процессов

        # Создадим односторонний канал связи между процессами
        self.hardware_connection, self.gui_connection = Pipe(duplex=False)

        self.ComPort = self.manager.ComPort()
        self.Decoder = self.manager.Decoder()

        self.ComPort_ReadingProcess = Process()
        self.ComPort_DecodingProcess = Process()
        self.Decoded_Data_Checking = Thread()

    def __del__(self):
        self._stop_Processes()
        self.gui_connection.close()

    ##############################################

    def _start_Processes(self, command=''):
        """
        Запуск процессов
        """
        self.processingFlag = True

        if not self.isProcessesActive:
            self.isProcessesActive = True

            # По новой инициализируем все процессы для корректного запуска при повторном вызове функции
            self.ComPort_ReadingProcess = Process(target=self.ComPort.startMeasuring,
                                                  args=(self.portName, BAUDRATE[self.type_port], self.ComPort_Data, self.hardware_connection, self.MessageQueue, command, ),
                                                  daemon=True)
            self.ComPort_DecodingProcess = Process(target=self.Decoder.decoding,
                                                   args=(self.type_port, self.ComPort_Data, self.Decoded_Data, self.Duplicate_Queue, self.MessageQueue,),
                                                   daemon=True)
            self.Decoded_Data_Checking = Thread(target=self._queue_checking, args=(), daemon=True)

            self.ComPort_ReadingProcess.start()

            sleep(0.5)    # Время на отрытие COM порта

            self.ComPort_DecodingProcess.start()
            self.Decoded_Data_Checking.start()

    def _stop_Processes(self):
        """
        Остановка процессов
        """
        if self.isProcessesActive:
            # Если процессы активны
            self.isProcessesActive = False
            try:

                self.ComPort_ReadingProcess.terminate()
                self.ComPort_ReadingProcess.join()
                sleep(0.5)    # Для гарантии завершения обработки данных из очереди self.ComPort_Data

                self.ComPort_DecodingProcess.terminate()
                self.ComPort_DecodingProcess.join()

                self.processingFlag = False
                self.Decoded_Data_Checking.join()

            except Exception as error:
                self.Error_ComPort.emit({"type_port": self.type_port, "message": '!!! Критическая ошибка. Проверьте log файл !!!'})
                self.printer.printing(text='!!! Критическая ошибка. Проверьте log файл !!!', log_text=error, log_level='Critical')

    ##############################################

    def _queue_checking(self):
        savingFile = open(self.savingFileName, 'wb')
        # print(self.savingFileName)
        while self.processingFlag or not self.__all_queue_empty():
            if not self.Decoded_Data.empty():
                self._checking_DecodedData()

            if not self.MessageQueue.empty():
                self.__checking_MessageQueue()

            if not self.Duplicate_Queue.empty():
                savingFile.write(self.Duplicate_Queue.get())

        savingFile.close()

    def __all_queue_empty(self) -> bool:
        return self.Duplicate_Queue.empty() and self.Decoded_Data.empty() and self.MessageQueue.empty()

    def _checking_DecodedData(self):
        pass

    def __checking_MessageQueue(self):
        msg = str(self.MessageQueue.get())
        msg_type = msg.split('__')[0]
        msg_text = msg.split('__')[1]

        match msg_type:
            case 'Info':
                self.printer.printing(text=msg_text, log_text=msg_text, log_level=msg_type)
            case 'Warning':
                self.printer.printing(log_text=f'\n{msg_text}', log_level=msg_type)
            case 'Error':
                self.Error_ComPort.emit({"type_port": self.type_port, "message": msg_text})
                self.printer.printing(text=f'Внимание!!! {msg_text}', log_text=msg_text, log_level=msg_type)
            case 'Critical':
                self.Error_ComPort.emit({"type_port": self.type_port, "message": '!!! Критическая ошибка. Проверьте log файл !!!'})
                self.printer.printing(text='!!! Критическая ошибка. Проверьте log файл !!!', log_text=msg_text, log_level=msg_type)
            case 'Command':
                self._command_execution(msg_text)
            case _:
                pass

    def _command_execution(self, command):
        pass

class STM_ComPort(COM_Port_GUI):
    """
    Класс для управления платой STM32 через COM порт
    """
    EndOfInitialSettings = pyqtSignal()

    def __init__(self, printer: Printing):
        super().__init__(printer, "STM")

    ##### Методы, напрямую вызываемые из GUI #####
    def startInitialSettings(self, com_port_name: str, saving_path: str, template_name: str):
        self.portName = com_port_name
        self.savingFileName = f'{saving_path}/{template_name}_{self.type_port}_Init.bin'
        self.processingFlag = True
        self._start_Processes('Command__start_InitialSetting')

    def stopInitialSettings(self):
        self._stop_Processes()
        self.printer.printing('Конец выставки датчиков\n'
                              '#######################')

    def startMeasuring(self, com_port_name: str, saving_path: str, template_name: str, data_type: str):
        self.portName = com_port_name
        self.savingFileName = f'{saving_path}/{template_name}_{self.type_port}_{data_type}.bin'
        self.processingFlag = True
        self._start_Processes('Command__start_Measuring')

    def stopMeasuring(self):
        # Пошлём команду завершения чтения данных на плату
        self.gui_connection.send('Command__stop_Measuring')
        sleep(0.5)  # Для корректного завершения процесса

        self._stop_Processes()
        self.printer.printing('Конец чтения данных\n'
                              '#######################')

    ##############################################
    def _checking_DecodedData(self):
        values = self.Decoded_Data.get()
        # print(values)
        if self.type_port == 'STM':
            self.NewData_Signal.emit({"type_port": self.type_port, "values": values})

    def _command_execution(self, command):
        if command == 'stop_InitialSetting':
            self.EndOfInitialSettings.emit()


class GPS_ComPort(COM_Port_GUI):
    """
    Класс для управления GPS модулем через COM порт
    """
    EndOfCollectingCoordinates = pyqtSignal()
    DURATION_COORDINATES_COLLECTION = 5    # Время сбора координат в секундах

    def __init__(self, printer: Printing):
        super().__init__(printer, "GPS")
        self.timerFlag = False
        self.coordCollecting = Thread()
        self.counter = 0

    ##### Метод, напрямую вызываемый из GUI #####
    def gettingCoordinates(self, com_port_name: str, saving_path: str, template_name: str):
        self.timerFlag = True
        self.counter += 1
        self.portName = com_port_name
        self.savingFileName = f'{saving_path}/{template_name}_{self.type_port}_{self.counter}.txt'
        self.processingFlag = True
        self._start_Processes()
        self.coordCollecting = Thread(target=self._collecting_coordinates, args=(), daemon=True)
        self.coordCollecting.start()

    ##############################################
    def _collecting_coordinates(self):
        # Подождём указанное время, пока в другом процессе идёт сбор данных
        sleep(self.DURATION_COORDINATES_COLLECTION)

        # Закончим сбор координат
        self._stop_Processes()
        self.EndOfCollectingCoordinates.emit()

    ##############################################
    def _checking_DecodedData(self):
        values = self.Decoded_Data.get()
        # print(values)

        latitude_startIndex = values.find(",")
        latitude_endIndex = values.find(",", latitude_startIndex + 1)

        if (latitude_endIndex - latitude_startIndex) != 1:
            latitude = float(values[latitude_startIndex + 1: latitude_endIndex])

            longitude_startIndex = values.find(",", latitude_endIndex + 2)
            longitude_endIndex = values.find(",", longitude_startIndex + 1)

            longitude = float(values[longitude_startIndex + 1: longitude_endIndex])
            self.NewData_Signal.emit(
                {"type_port": self.type_port, "values": {"Latitude": latitude, "Longitude": longitude}})

        else:
            self.NewData_Signal.emit(
                {"type_port": self.type_port, "values": {"Latitude": 99.99, "Longitude": 99.99}})
