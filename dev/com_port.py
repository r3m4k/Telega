import os
if os.name == 'nt':  # sys.platform == 'win32':
    from serial.tools.list_ports_windows import comports
elif os.name == 'posix':
    from serial.tools.list_ports_posix import comports

from PyQt5.QtCore import QObject, pyqtSignal
import serial


BAUDRATE = 115200
PACKET_SIZE = 34


class COM_Port(QObject):
    NewData_Signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # self.port = serial.Serial(self.get_STMPort(), baudrate=BAUDRATE)
        # self.LogFileName = logfilePath
        # self.LogFile = open(self.LogFileName, 'ab')

    def __del__(self):
        # try:
        #     self.port.close()
        #     self.LogFile.close()
        #
        # except AttributeError:
        #     pass
        pass

    def do(self):
        data = self.read_packege(PACKET_SIZE)
        print('+')
        self.LogFile.write(bytearray(data))
        print('+')
        self.NewData_Signal.emit('New data')
        print('+')

    def read_packege(self, size):
        try:
            _data = self.port.read(size=size)
        except serial.SerialException as error:
            print(error)
            exit(-1)

        return _data

    @staticmethod
    def get_STMPort() -> str:
        iterator = comports(include_links=False)
        _port_name = ''

        for n, (port, desc, hwid) in enumerate(iterator, 1):
            if 'STM' in desc:
                _port_name = port
            print("{:20}".format(port))
            print(f"    desc: {desc}")
            print(f"    hwid: {hwid}")

        if _port_name == '':
            print('Порт STM не найден')
            exit(1)
        else:
            return _port_name

    @staticmethod
    def get_ComPorts() -> dir:
        iterator = comports(include_links=False)
        res = {}
        for n, (port, desc, hwid) in enumerate(iterator, 1):
            res[port] = {"desc": desc, "hwid": hwid}

        return res



if __name__ == '__main__':
    COM_Port()