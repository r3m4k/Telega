import os
import threading
from multiprocessing import Process, Queue, freeze_support
from typing import Callable

if os.name == 'nt':  # sys.platform == 'win32':
    from serial.tools.list_ports_windows import comports
elif os.name == 'posix':
    from serial.tools.list_ports_posix import comports

from PyQt5.QtCore import QObject, pyqtSignal
import serial
from serial.serialutil import SerialException

from message import message


"""
Для корректной работы нескольких процессов и взаимодействий между ними 
вынесем необходимые функции и экземпляры необходимых классов в область 
видимости всего модуля com_port.py

Непосредственно класс COM_Port реализует удобный API для работы GUI.
Суть большинства методов этого класса - вызов и управление функциями и 
переменными из зоны видимости всего модуля, которые недоступны из вне
при импорте данного класса способом 'from com_port.py import Com_Port'
"""

def reading_ComPort(port: serial.Serial):
    print(f'Начало чтения данных {port.port}')
    try:
        ComPort_Data.put(port.read(1))
    except serial.serialutil.PortNotOpenError:
        port.open()
    except SerialException as error:
        print(error)
        message('Ошибка чтения порта', 'Warning')

def open_ComPort():
    Port.open()

def close_ComPort():
    Port.close()

def set_ComPort_Name(portName):
    Port.port = portName


BAUDRATE = 115200                               # Скорость работы COM порта

Port = serial.Serial(baudrate=BAUDRATE)         # COM порт, с которым ведётся работа в данном модуле
ComPort_Data = Queue()                          # Очередь, куда будет записываться все данные, полученные из Port
Decoded_Data = Queue()                          # Очередь, куда будет записываться декодированные данные из ComPort_Data

Reading_ComPort_Process = Process(target=reading_ComPort, args=(Port, ), daemon=True)


class COM_Port(QObject):
    NewData_Signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        self.portName = str()
        self.LogFileName = str()

    def __del__(self):
        try:
            Port.close()
            print('COM порт закрыт')
        except Exception as error:
            message(error, 'Warning')

    def set_ComPort(self, com_port_name):
        self.portName = com_port_name
        Port.port = self.portName


    @staticmethod
    def get_ComPorts() -> dir:
        iterator = comports(include_links=False)
        res = {'-----': {"desc": "Здесь будут отображаться дескриптор выбранного COM порта"}}
        for n, (_port, desc, hwid) in enumerate(iterator, 1):
            res[_port] = {"desc": desc, "hwid": hwid}

        return res

    def startMeasuring(self, com_port_name: str):
        self.set_ComPort(com_port_name)
        try:
            open_ComPort()
        except SerialException as error:
            message(error, 'Warning')
            return
        try:
            Reading_ComPort_Process.start()
        except RuntimeError:
            Reading_ComPort_Process.join()

    def stopMeasuring(self):
        print('Конец чтения данных')
        Reading_ComPort_Process.close()
        close_ComPort()
