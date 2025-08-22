# System imports
from time import sleep
from threading import Thread
from multiprocessing import Process, Queue, Pipe
from multiprocessing.context import ProcessError


# External imports
from PyQt5.QtCore import QObject, pyqtSignal


# User imports
from constaints import BAUDRATE
from proxy import MyManager, COM_PortProxy, DecodeProxy
from com_port import COM_Port
from decoder import Decoder
from ..printing import Printing

##########################################################

"""
Для корректной работы нескольких процессов и взаимодействий между ними создадим класс MyManager,
который создает служебный процесс, в котором размещается централизованная версия разделяемого объекта. 
Менеджер создает так называемый прокси‑объект для каждого процесса, и процессы обращаются именно к прокси‑объекту.
"""


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
        self.areProcessesActive = False     # Флаг работы процессов

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

        if not self.areProcessesActive:
            self.areProcessesActive = True

            # По новой инициализируем все процессы для корректного запуска при повторном вызове функции
            self.ComPort_ReadingProcess = Process(target=self.ComPort.startProcess,
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
        if self.areProcessesActive:
            # Если процессы активны
            self.areProcessesActive = False
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

    def restart(self):
        if self.areProcessesActive:
            # Если процессы работы с платой активны, то пошлём команду на перезапуск
            self.gui_connection.send('Command__restart')
        else:
            # Если процессы не созданы, то создадим его с первоначальной командой на перезапуск
            self._start_Processes('Command__restart')

        sleep(0.4)  # Для корректного завершения процессов
        self._stop_Processes()
        self.printer.printing('Перезапуск платы\n'
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
