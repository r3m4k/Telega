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
    commands = {
        "restart":                 bytes([0x7e, 0xe7, 0xff, 0xff, 0x00, 0x63]),
        "start_InitialSetting":    bytes([0x7e, 0xe7, 0xff, 0xab, 0xba, 0xc9]),
        "start_Measuring":         bytes([0x7e, 0xe7, 0xff, 0xbc, 0xcb, 0xeb]),
        "stop_Measuring":          bytes([0x7e, 0xe7, 0xff, 0xcd, 0xdc, 0x0d]),
    }

    received_msg = {
        "confirmation_Message":    bytes([0x7e, 0xe7, 0xff, 0xaa, 0xaa, 0xb8, 0, 0]),
        "end_of_InitialSetting":   bytes([0x7e, 0xe7, 0xff, 0xba, 0xab, 0xc9, 0, 0])
    }

    def __init__(self):
        self.port = serial.Serial()         # COM порт, с которым ведётся работа в данном модуле

    def __del__(self):
        self.port.close()

    def startProcess(self, com_port_name: str, baudrate: int,
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

    def reading_ComPort(self, data_queue: Queue, command_pipe: Pipe, msg_queue: Queue):
        # Начнём чтение данных
        msg_queue.put(f'Info__Начало чтения данных из {self.port.port}')
        try:
            while True:
                if not command_pipe.poll():
                    # Если нет поступивших команд, то читаем данные из СOM порта
                    data_queue.put(self.port.read(1))
                else:
                    _ = self.decode_Command(str(command_pipe.recv()), msg_queue)
                    break  # Остановим чтение из com порта

        except SerialException:
            msg_queue.put(f'Warning__{traceback.format_exc()}')
            msg_queue.put(f'Error__Ошибка чтения порта {self.port.port}')

    def decode_Command(self, command: str, msg_queue: Queue) -> (bool, Callable):
        sending_status = False
        try:
            receive_command = command.split('__')[1]
            if receive_command in self.commands:
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

    def foo_function(self, data_queue: Queue, command_pipe: Pipe, msg_queue: Queue):
        self.port.close()
        msg_queue.put('Debug__Doing foo_function')
        while True:
            sleep(0.5)
