# System imports
from serial import Serial,  SerialException, SerialTimeoutException

# External imports

# User imports
from config import config
from utils import confirm_from_console
from byte_source.bytes_source import BytesSource
from byte_source.com_port import get_ComPorts, ComPort

#########################

# Класс для настройки ComPort
class ComPortSetting:
    _port_name: str
    _baudrate: int

    def __init__(self):
        self._ports: dict[str, ...] = get_ComPorts()        # Подключённые порты
        self._try_use_cached_port()

    def get_bytes_source(self) -> BytesSource:
        if not self._port_name or not self._baudrate:
            raise RuntimeError('Не выбран com порт!')

        # Обновляем глобальный конфиг
        port_info = self._ports[self._port_name]
        config.com_port.name = self._port_name
        config.com_port.desc = port_info['desc']
        config.com_port.hwid = port_info['hwid']
        config.com_port.baudrate = self._baudrate

        # Сохраняем изменения
        config.save()

        return ComPort(self._port_name, self._baudrate)

    def _try_use_cached_port(self):
        com_port_config = config.com_port
        if com_port_config.name and com_port_config.baudrate and com_port_config.name in self._ports:
            print(f'Использовать {com_port_config.name}?\n'
                  f'| desc = {com_port_config.desc}\n'
                  f'| hwid = {com_port_config.hwid}\n'
                  f'| baudrate = {com_port_config.baudrate}')
            if confirm_from_console():
                self._port_name = com_port_config.name
                self._baudrate = com_port_config.baudrate
                return

        self._load_comport_from_console()

    def _load_comport_from_console(self):

        port_list = list(self._ports.keys())

        if len(port_list) == 0:
            print('# -----------------------------------------\n'
                  'Не найдено ни одного com порта!\n'
                  'Завершение программы...\n'
                  '# -----------------------------------------\n')
            exit(1)

        print('# -----------------------------------------\n'
              'Информация о подключённых портах:\n'
              '# -----------------------------------------\n')

        for port in port_list:
            print(f'#{port_list.index(port) + 1}: {port}\n'
                  f'desc: {self._ports[port]["desc"]}\n'
                  f'hwid: {self._ports[port]["hwid"]}\n')

        print('# -----------------------------------------')

        try:
            port_num = int(input('Выберите номер порта: '))
            port_name = port_list[port_num - 1]
        except IndexError:
            print('# -----------------------------------------\n'
                  'Неправильно выбран номер порта!\n'
                  'Завершение программы...\n'
                  '# -----------------------------------------\n')
            exit(1)

        print('# -----------------------------------------')

        baudrate_list = [
            9600,
            57600,
            115200,
            230400,
            460800,
            921600
        ]

        print('Поддерживаемые скорости работы порта:')
        for i in range(len(baudrate_list)):
            print(f'| {i+1} -- {baudrate_list[i]}')

        try:
            port_baudrate = baudrate_list[int(input('\nВыберите скорость работы порта: ')) - 1]
        except IndexError:
            print('# -----------------------------------------\n'
                  'Неправильно выбрана скорость работы порта!\n'
                  'Завершение программы...\n'
                  '# -----------------------------------------\n')
            exit(1)

        print('# -----------------------------------------\n')

        print(f'Выбран порт #{port_num}: {port_name}\n'
              f'Скорость работы порта: {port_baudrate}')

        self._port_name = port_name
        self._baudrate = port_baudrate
