import os
from threading import Thread
from multiprocessing import Process, Queue
from multiprocessing.managers import BaseManager, NamespaceProxy
from multiprocessing.context import ProcessError

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
        # print(f'Закрытие {self.port.port}')
        self.port.close()

    def set_ComPort(self, com_port_name: str):
        # self.port.port = com_port_name
        self.port = serial.Serial(port=com_port_name, baudrate=BAUDRATE)
        self.port.open()

    def startMeasuring(self, com_port_name: str, data_container: Queue, msg_container: Queue):
        # Откроем COM порт
        self.port = serial.Serial(port=com_port_name, baudrate=BAUDRATE)
        if self.port.is_open:
            self.port.close()

        try:
            self.port.open()
        except SerialException as error:
            msg_container.put(f'__Error__{error}')
            # return

        # Начнём чтение данных
        msg_container.put(f'Начало чтения данных из {self.port.port}')
        try:
            self.reading_ComPort(data_container)
        except SerialException as error:
            msg_container.put(f'__Error__{error}')
            msg_container.put('__Warning__Ошибка чтения порта')

    def reading_ComPort(self, data_container: Queue):
        while True:
            data_container.put(self.port.read(1))


class Decoder:
    def __init__(self):
        pass

    def decoding(self, type_name: str, source_queue: Queue, output_queue: Queue):
        if type_name == "STM":
            self.decoding_STM(source_queue, output_queue)
        elif type_name == "GPS":
            self.decoding_GPS()
        else:
            raise RuntimeError('Неправильно передан параметр type_name.\n'
                               f'Он может принимать значения "STM" или "GPS", а передан type_name = {type_name}')

    @staticmethod
    def decoding_STM(source_queue: Queue, output_queue: Queue):
        while True:
            if not source_queue.empty():
                output_queue.put(source_queue.get())

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
        self.portName = ''               # Имя COM порта

        self.manager = MyManager()
        try:
            self.manager.start()
        except ProcessError as error:
            self.printer.printing(error)

        self.ArgsQueue = Queue()        # Очередь, через которую передадим параметры в процесс self.ComPort_ReadingProcess
                                        # Это необходимо тк при инициализации процесса Process(args=(self.portName, ...)) создаётся копия self.portName,
                                        # так что дальнейшее изменение self.portName не изменит его значение в другом процессе

        self.ComPort_Data = Queue()     # Очередь, куда будет записываться все данные, полученные из self.port
        self.Decoded_Data = Queue()     # Очередь, куда будет записываться декодированные данные из ComPort_Data
        self.MessageQueue = Queue()     # Очередь сообщений, полученных из различных процессов

        self.ComPort = self.manager.ComPort()
        self.Decoder = self.manager.Decoder()

        self.ComPort_ReadingProcess = Process()
        self.ComPort_DecodingProcess = Process(target=self.Decoder.decoding, args=(self.decoder_type, self.ComPort_Data, self.Decoded_Data, ), daemon=True)
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

    def startMeasuring(self, com_port_name: str):
        self.portName = com_port_name
        self.processingFlag = True

        self.ComPort_ReadingProcess = Process(target=self.ComPort.startMeasuring, args=(self.portName, self.ComPort_Data, self.MessageQueue, ), daemon=True)

        self.ComPort_ReadingProcess.start()
        self.ComPort_DecodingProcess.start()
        self.Decoded_Data_Checking.start()

    def stopMeasuring(self):
        self.printer.printing('Конец чтения данных')
        self.processingFlag = False

        self.ComPort_ReadingProcess.terminate()
        self.ComPort_ReadingProcess.join()

        self.ComPort_DecodingProcess.terminate()
        self.ComPort_DecodingProcess.join()

    ##############################################

    def queue_checking(self):
        while self.processingFlag:
            if not self.Decoded_Data.empty():
                value = self.Decoded_Data.get()
                print(value)

            if not self.MessageQueue.empty():
                self.printer.printing(self.MessageQueue.get())


