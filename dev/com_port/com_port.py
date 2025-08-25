# System imports
import os
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

            try:
                if command != '':
                    # Отправим команду по COM порту
                    sending_status, command_function = self.decode_Command(command, msg_queue)
                    if not sending_status:
                        return

            except serial.serialutil.SerialException or RuntimeError:
                msg_queue.put(f'Warning__\n{traceback.format_exc()}')
                msg_queue.put(f'Error__Ошибка отправки команды по {com_port_name}')
                return

            command_function(data_queue, command_pipe, msg_queue)


        except Exception as error:
            msg_queue.put(f'Critical__\n{error}\n{traceback.format_exc()}')

    def decode_command(self, command: str) -> Callable[..., None]:
        receive_command = command.split('__')[1]

        match receive_command:
            case 'restart':
                return self.foo_function
            case 'start_Measuring':
                return self.reading_ComPort
            case 'start_InitialSetting':
                return self.reading_ComPort
            case _:
                return self.foo_function

    def reading_ComPort(self, data_queue: Queue, command_pipe: Pipe, msg_queue: Queue):
        # Начнём чтение данных
        msg_queue.put(f'Info__Начало чтения данных из {self._port.port}')
        try:
            while True:
                if not command_pipe.poll():
                    # Если нет поступивших команд, то читаем данные из СOM порта
                    data_queue.put(self._port.read(1))
                else:
                    _ = self.decode_Command(str(command_pipe.recv()), msg_queue)
                    break  # Остановим чтение из com порта

        except SerialException:
            msg_queue.put(f'Warning__{traceback.format_exc()}')
            msg_queue.put(f'Error__Ошибка чтения порта {self._port.port}')

    def decode_Command(self, command: str, msg_queue: Queue) -> (bool, Callable):
        sending_status = False
        try:
            receive_command = command.split('__')[1]
            if receive_command in self._commands:
                sending_status = self.send_Command(receive_command, msg_queue)
            else:
                msg_queue.put(f'Warning__Команда не распознана')
                return sending_status, self.foo_function

            match receive_command:
                case 'restart':
                    return sending_status, self.foo_function
                case 'start_Measuring':
                    return sending_status, self.reading_ComPort
                case 'start_InitialSetting':
                    return sending_status, self.reading_ComPort
                case _:
                    return False, self.foo_function


        except Exception:
            msg_queue.put(f'Warning__Неправильно передана команда {command}')
            raise RuntimeError('Неправильно передана команда')
        return False    # Если произошла ошибка, то вернём False

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


    def foo_function(self):
        self._port.close()
        self._msg_queue.put('Debug__Doing foo_function')
        while True:
            sleep(0.5)
