import os
import _io
from time import sleep
import binascii

from threading import Thread
from multiprocessing import Process, Queue
from multiprocessing.managers import BaseManager, NamespaceProxy
from multiprocessing.context import ProcessError

from numpy.ma.core import indices

if os.name == 'nt':  # sys.platform == 'win32':
    from serial.tools.list_ports_windows import comports
elif os.name == 'posix':
    from serial.tools.list_ports_posix import comports
import serial
from serial.serialutil import SerialException

from PyQt5.QtCore import QObject, pyqtSignal

from message import message
from printing import Printing


"""
Для корректной работы нескольких процессов и взаимодействий между ними создадим класс MyManager,
который создает служебный процесс, в котором размещается централизованная версия разделяемого объекта. 
Менеджер создает так называемый прокси‑объект для каждого процесса, и процессы обращаются именно к прокси‑объекту.
"""

BAUDRATE = 115200       # Скорость работы COM порта


class MyManager(BaseManager):
    pass


class COM_Port:
    def __init__(self):
        self.port = serial.Serial()         # COM порт, с которым ведётся работа в данном модуле

    def __del__(self):
        self.port.close()

    def startMeasuring(self, com_port_name: str, data_queue: Queue, msg_queue: Queue):
        # Откроем COM порт
        try:
            self.port = serial.Serial(port=com_port_name, baudrate=BAUDRATE)
        except serial.serialutil.SerialException as error:
            msg_queue.put(f'Error__{error}')
            return

        if not self.port.is_open:
            try:
                self.port.open()
            except SerialException as error:
                msg_queue.put(f'Error__{error}')

        # Начнём чтение данных
        msg_queue.put(f'Начало чтения данных из {self.port.port}')
        try:
            self.reading_ComPort(data_queue)
        except SerialException as error:
            msg_queue.put(f'Error__{error}')
            msg_queue.put('Warning__Ошибка чтения порта')

    def reading_ComPort(self, data_queue: Queue):
        while True:
            data_queue.put(self.port.read(1))


class Decoder:
    def __init__(self):
        pass

    def decoding(self, type_name: str, source_queue: Queue, output_queue: Queue, duplicate_queue: Queue, msg_queue: Queue):
        if type_name == "STM":
            self.decoding_STM(source_queue, output_queue, duplicate_queue,msg_queue)
        elif type_name == "GPS":
            self.decoding_GPS()
        else:
            raise RuntimeError('Неправильно передан параметр type_name.\n'
                               f'Он может принимать значения "STM" или "GPS", а передан type_name = {type_name}')

    def decoding_STM(self, source_queue: Queue, output_queue: Queue, duplicate_queue: Queue, msg_queue: Queue):
        # Создадим список именованных констант, которые будут использоваться вместо Enum
        Want7E: int = 0
        WantE7: int = 1
        WantSize: int = 2
        WantFormat: int = 3
        WantPacketBody: int = 4
        WantConSum: int = 5
        ####################

        stage = Want7E
        titles = ['Time', 'Acc_X', 'Acc_Y', 'Acc_Z', 'Gyro_X', 'Gyro_Y', 'Gyro_Z', 'Temp']

        bytes_buffer = []   # Буфер для байтов, прочитанных из очереди данных
        data = {}           # Словарь, в который сохраним пакет полученных данных, с ключами titles
        size = 0            # Количество байтов данных в посылке
        index = 0           # Индекс байта в пакете данных
        con_sum = 0         # Посчитанная контрольная сумма
        Con_Sum = 0         # Полученная контрольная сумма

        msg_queue.put('Начало декодирования данных')

        while True:
            if source_queue.empty():
                continue

            val = source_queue.get()
            bt = int(binascii.hexlify(val), 16)
            duplicate_queue.put(val)
            # msg_queue.put(f'{stage} -- {val}')
            if stage == Want7E:
                if bt == 126:
                    stage = WantE7
                    con_sum = bt
                    # Обнулим накопленные значения
                    index = 0
                    data = {}
                    bytes_buffer = []
                else:
                    stage = Want7E

            elif stage == WantE7:
                if bt == 231:
                    stage = WantSize
                    con_sum += bt
                else:
                    stage = Want7E

            elif stage == WantSize:
                size = bt
                con_sum += bt
                stage = WantFormat

            elif stage == WantFormat:
                _ = bt
                con_sum += bt
                stage = WantPacketBody

            elif stage == WantPacketBody:
                if index < size:
                    index += 1
                    con_sum += bt
                    bytes_buffer.append(bt)

                if index == size:
                    stage = WantConSum

            elif stage == WantConSum:
                Con_Sum = bt
                # msg_queue.put(f'Полученная контрольная сумма: {Con_Sum} || Посчитанная контрольная сумма: {con_sum & 255}')
                # Сравним Con_Sum и младшие 8 бит con_sum
                if Con_Sum == (con_sum & 255):
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
                    # msg_queue.put('Контрольная сумма сошлась')

                else:
                    msg_queue.put('Контрольная сумма не сошлась')
                stage = Want7E

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

    def decoding_GPS(self):
        pass

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
    Класс для управления COM портом из GUI
    """
    MyManager.register('ComPort', COM_Port, COM_PortProxy)
    MyManager.register('Decoder', Decoder, DecodeProxy)
    NewData_Signal = pyqtSignal(dict)

    def __init__(self, printer: Printing, decoder_type: str):
        super().__init__()
        self.printer = printer              # Объект, с помощью которого будем выводить информацию в GUI, stdout и logger
        self.decoder_type = decoder_type    # Тип подключённого датчика по данному порту: STM или GPS
        self.processingFlag = False         # Флаг необходимости анализировать данные. Равен True после self.startMeasuring
                                            # И равен False после self.stopMeasuring
        self.portName = ''                  # Имя COM порта
        self.savingFileName = ''            # Имя файла, куда будут сохраняться данные из COM порта

        self.manager = MyManager()
        try:
            self.manager.start()
        except ProcessError as error:
            self.printer.printing(error)


        self.ComPort_Data = Queue()     # Очередь, куда будет записываться все данные, полученные из self.port
        self.Decoded_Data = Queue()     # Очередь, куда будет записываться декодированные данные из ComPort_Data
        self.Duplicate_Queue= Queue()   # Очередь, куда будет дублироваться данные из self.ComPort_Data для записи данных в log файл
        self.MessageQueue = Queue()     # Очередь сообщений, полученных из различных процессов

        self.ComPort = self.manager.ComPort()
        self.Decoder = self.manager.Decoder()

        self.ComPort_ReadingProcess = Process()
        self.ComPort_DecodingProcess = Process(target=self.Decoder.decoding, args=(self.decoder_type, self.ComPort_Data, self.Decoded_Data, self.Duplicate_Queue, self.MessageQueue, ), daemon=True)
        self.Decoded_Data_Checking = Thread(target=self.queue_checking, args=(), daemon=True)

    def __del__(self):
        pass

    @staticmethod
    def get_ComPorts() -> dir:
        iterator = comports(include_links=False)
        res = {'-----': {"desc": "Здесь будут отображаться дескриптор выбранного COM порта"}}
        for n, (_port, desc, hwid) in enumerate(iterator, 1):
            res[_port] = {"desc": desc, "hwid": hwid}

        return res

    ##### Методы, напрямую вызываемые из GUI #####

    def startMeasuring(self, com_port_name: str, saving_path: str, template_name: str):
        self.portName = com_port_name
        self.savingFileName = f'{saving_path}/{template_name}_{self.decoder_type}_RawData.bin'
        self.processingFlag = True

        # По новой инициализируем self.ComPort_ReadingProcess, чтобы передать не пустой параметр self.portName.
        # Это необходимо тк при инициализации процесса Process(args=(self.portName, ...)) создаётся копия self.portName,
        # так что если объявить этот процесс в __init__, то в него передастся пустой параметр self.portName,
        # а дальнейшее изменение self.portName не изменит его значение в этом процессе
        self.ComPort_ReadingProcess = Process(target=self.ComPort.startMeasuring, args=(self.portName, self.ComPort_Data, self.MessageQueue, ), daemon=True)

        self.ComPort_ReadingProcess.start()

        sleep(1)    # Время на отрытие COM порта

        self.ComPort_DecodingProcess.start()
        self.Decoded_Data_Checking.start()

    def stopMeasuring(self):
        self.printer.printing('Конец чтения данных')
        self.processingFlag = False

        self.ComPort_ReadingProcess.terminate()
        self.ComPort_ReadingProcess.join()

        sleep(1)    # Для гарантии завершения обработки self.ComPort_Data

        self.ComPort_DecodingProcess.terminate()
        self.ComPort_DecodingProcess.join()

    ##############################################

    def queue_checking(self):
        savingFile = open(self.savingFileName, 'wb')
        print(self.savingFileName)
        while self.processingFlag: # and self.all_queue_empty():
            if not self.Decoded_Data.empty():
                values = self.Decoded_Data.get()
                print(values)
                self.NewData_Signal.emit(values)

            if not self.MessageQueue.empty():
                self.printer.printing(text=str(self.MessageQueue.get()))

            if not self.Duplicate_Queue.empty():
                savingFile.write(self.Duplicate_Queue.get())

        savingFile.close()

    def all_queue_empty(self) -> bool:
        return self.Duplicate_Queue.empty() and self.Decoded_Data.empty() and self.MessageQueue.empty()
