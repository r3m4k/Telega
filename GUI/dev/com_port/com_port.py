# System imports
import traceback
from time import sleep
from typing import Callable
from multiprocessing import Queue, Pipe

# External imports
import serial
from serial.serialutil import SerialException

# User imports


##########################################################

class COM_Port:
    # Формат команд: 2 байта - заголовок, 1 байт - формат посылки, 2 байта - команда, 1 байт - контрольная сумма
    _commands = {
        "restart":                 bytes([0x7e, 0xe7, 0xff, 0xff, 0x00, 0x63]),
        "start_InitialSetting":    bytes([0x7e, 0xe7, 0xff, 0xab, 0xba, 0xc9]),
        "start_Measuring":         bytes([0x7e, 0xe7, 0xff, 0xbc, 0xcb, 0xeb]),
        "stop_Measuring":          bytes([0x7e, 0xe7, 0xff, 0xcd, 0xdc, 0x0d]),
    }

    _received_msg = {
        "confirmation_Message":    bytes([0x7e, 0xe7, 0xff, 0xaa, 0xaa, 0xb8, 0, 0]),
        "end_of_InitialSetting":   bytes([0x7e, 0xe7, 0xff, 0xba, 0xab, 0xc9, 0, 0])
    }

    def __init__(self):
        self._port = serial.Serial()        # COM порт, с которым ведётся работа в данном модуле
        self._baudrate: int = 0             # Скорость работы порта
        self._data_queue: Queue = None      # Очередь для обмена данными с родительским процессами
        self._msg_queue: Queue = None       # Очередь для обмена сообщениями с родительским процессами
        self._command_pipe: Pipe = None     # Канал для получения команд из родительского процесса

    def __del__(self):
        self._port.close()

    def startProcess(self, com_port_name: str, baudrate: int,
                     data_queue: Queue, command_pipe: Pipe, msg_queue: Queue,
                     command = ''):
        self._baudrate = baudrate
        self._data_queue = data_queue
        self._msg_queue = msg_queue
        self._command_pipe = command_pipe

        # При возникновении любого неучтённого исключения перенаправим его в self._msg_queue
        try:
            # Откроем COM порт
            try:
                self._port = serial.Serial(port=com_port_name, baudrate=baudrate, timeout=1)

            except serial.serialutil.SerialException:
                self._msg_queue.put(f'Warning__\n{traceback.format_exc()}')
                self._msg_queue.put(f'Error__Ошибка открытия {com_port_name}')
                return

            command_execution: Callable[..., None] = self.decode_command(command)
            command_execution()

        except Exception as error:
            msg_queue.put(f'Critical__\n{error}\n{traceback.format_exc()}')

    def decode_command(self, command: str) -> Callable[..., None]:
        receive_command = command.split('__')[1]

        # Если полученная команда подразумевает предварительное сообщение по com порту, то отправим его.
        # Пока что при выполнении всех полученных команд из родительского процесса требуется отправка команды по com порту,
        # но это не обязательно, в общем случае
        if receive_command in self._commands:
            try:
                self.send_Command(receive_command)

            except serial.serialutil.SerialException or RuntimeError:
                self._msg_queue.put(f'Warning__\n{traceback.format_exc()}')
                self._msg_queue.put(f'Error__Ошибка отправки команды по {self._port.name}')

            except Exception as error:
                self._msg_queue.put(f'Error__\n{error}\n{traceback.format_exc()}')

        # Вернём функцию, которая отвечает за выполнение полученной команды
        match receive_command:
            case 'restart':
                return self.foo_function
            case 'start_Measuring':
                return self.reading_ComPort
            case 'start_InitialSetting':
                return self.reading_ComPort
            case _:
                return self.foo_function

    def send_Command(self, command: str):
        self._msg_queue.put(f'Info__Отправка команды {command} по {self._port.port}')

        # Отправим команду и дождёмся подтверждение о получении
        self._port.reset_input_buffer()
        self._port.write(self._commands[command])
        msg = self._port.read(size=len(self._received_msg['confirmation_Message']))
        if msg == self._received_msg['confirmation_Message']:
            self._msg_queue.put('Info__Команда успешно принята устройством')
        else:
            self._msg_queue.put(f'Warning__Ошибка чтения команды устройством\n{msg}')
            raise RuntimeError('Команда не опознана устройством')

    def reading_ComPort(self):
        # Начнём чтение данных
        self._msg_queue.put(f'Info__Начало чтения данных из {self._port.port}')
        try:
            while True:
                if not self._command_pipe.poll():
                    # Если нет поступивших команд, то читаем данные из СOM порта
                    self._data_queue.put(self._port.read(1))
                else:
                    _ = self.decode_command(str(self._command_pipe.recv()))
                    break  # Остановим чтение из com порта

        except SerialException:
            self._msg_queue.put(f'Warning__{traceback.format_exc()}')
            self._msg_queue.put(f'Error__Ошибка чтения порта {self._port.port}')


    def foo_function(self):
        self._port.close()
        self._msg_queue.put('Debug__Doing foo_function')
        while True:
            sleep(0.5)
