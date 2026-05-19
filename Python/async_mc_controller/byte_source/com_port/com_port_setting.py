# System imports
from typing import Optional, TypeVar, Generic, NamedTuple

# External imports

# User imports
from async_mc_controller.config import McConfig
from async_mc_controller.utils import confirm_from_console
from async_mc_controller.logger import LoggerProtocol, FooLogger
from async_mc_controller.byte_source.bytes_source import AsyncBytesSource, AsyncBytesSourceFactory
from async_mc_controller.byte_source.com_port import get_ComPorts
from async_mc_controller.byte_source.com_port import AsyncComPort


#########################

T = TypeVar('T', bound=AsyncComPort)    # Тип возвращаемого com_port (должен быть наследником AsyncComPort)

# ------------------------------------------

class ComPortInfo(NamedTuple):
    name: str
    baudrate: int

# ------------------------------------------

class AsyncComPortSetting(AsyncBytesSourceFactory, Generic[T]):
    """Фабрика для настройки AsyncComPort через консоль.

    Настройка параметров (имя порта, скорость) собирается в `configure_source()`
    из кэша конфига или через интерактивный диалог. Создание готового
    источника выполняется в `get_bytes_source()`. Если `get_bytes_source()`
    вызван без предварительной настройки — `configure_source()` вызывается
    автоматически.
    """

    def __init__(self, com_port_type: type[T], config: McConfig, logger: LoggerProtocol = FooLogger()):

        self._com_port_type: type[T] = com_port_type

        if not issubclass(com_port_type, AsyncComPort):
            raise TypeError(f"{type(com_port_type).__name__} не является наследником AsyncComPort")

        self._config: McConfig = config
        self._logger = logger
        self._port_name: Optional[str] = None
        self._baudrate: Optional[int] = None

        # Доступные COM-порты
        self._ports: dict[str, dict[str, str]]  = get_ComPorts()

    def configure_source(self) -> None:
        """Собирает параметры COM-порта: из кэша конфига или через консоль.

        Если в конфиге есть валидные настройки и порт доступен — предлагает их
        использовать. При отказе пользователя или отсутствии кэша — запускает
        интерактивный выбор порта и скорости.
        """
        self._try_use_cached_port()

    def get_bytes_source(self, *args, **kwargs) -> T:
        """Создание AsyncComPort с выбранными настройками.

        Если источник не был настроен — вызывает `configure_source()`
        автоматически. Обновляет глобальный конфиг и сохраняет его
        перед возвратом источника.

        Returns:
            AsyncBytesSource: Готовый к использованию асинхронный COM-порт.
        """
        if not self._port_name or not self._baudrate:
            self._logger.debug('Источник не настроен — ленивый вызов configure_source()')
            self.configure_source()

        # Обновляем глобальный конфиг
        port_info = self._ports[self._port_name]
        self._config.com_port.name = self._port_name
        self._config.com_port.desc = port_info['desc']
        self._config.com_port.hwid = port_info['hwid']
        self._config.com_port.baudrate = self._baudrate

        # Сохраняем изменения
        self._config.save()

        self._logger.debug(f'Создан AsyncComPort типа {self._com_port_type.__name__}: '
                      f'{self._port_name} ({self._baudrate} бод)')
        return self._com_port_type(self._port_name, self._baudrate, *args, **kwargs)

    def get_port_info(self) -> ComPortInfo:
        return ComPortInfo(self._port_name, self._baudrate)

    def _try_use_cached_port(self) -> None:
        """Попытка использовать сохранённые в конфиге настройки порта.

        Если в конфиге есть валидные настройки и порт доступен —
        предлагает их использовать. Иначе запускает интерактивный выбор.
        """
        com_port_config = self._config.com_port

        if com_port_config.name and com_port_config.baudrate and (com_port_config.name in self._ports):

            print(f'Использовать {com_port_config.name}?\n'
                  f'| desc     = {com_port_config.desc}\n'
                  f'| hwid     = {com_port_config.hwid}\n'
                  f'| baudrate = {com_port_config.baudrate}')

            if confirm_from_console():
                self._port_name = com_port_config.name
                self._baudrate  = com_port_config.baudrate
                self._logger.debug(f'Используются сохранённые настройки порта: {self._port_name}')
                return

        self._load_comport_from_console()

    def _load_comport_from_console(self) -> None:
        """Интерактивный выбор COM-порта и скорости через консоль."""

        port_list = list(self._ports.keys())

        if len(port_list) == 0:
            self._logger.error('Не найдено ни одного COM-порта')
            print('# -----------------------------------------\n'
                  'Не найдено ни одного COM-порта!\n'
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
            port_num  = int(input('Выберите номер порта: '))
            port_name = port_list[port_num - 1]
        except (ValueError, IndexError):
            self._logger.error('Неверный номер порта')
            print('# -----------------------------------------\n'
                  'Неправильно выбран номер порта!\n'
                  'Завершение программы...\n'
                  '# -----------------------------------------\n')
            exit(1)

        print('# -----------------------------------------')

        baudrate_list = [9600, 57600, 115200, 230400, 460800, 921600]

        print('Поддерживаемые скорости работы порта:')
        for i, baudrate in enumerate(baudrate_list):
            print(f'| {i + 1} -- {baudrate}')

        try:
            port_baudrate = baudrate_list[int(input('\nВыберите скорость работы порта: ')) - 1]
        except (ValueError, IndexError):
            self._logger.error('Неверный номер скорости порта')
            print('# -----------------------------------------\n'
                  'Неправильно выбрана скорость работы порта!\n'
                  'Завершение программы...\n'
                  '# -----------------------------------------\n')
            exit(1)

        print('# -----------------------------------------\n')
        print(f'Выбран порт #{port_num}: {port_name}\n'
              f'Скорость работы порта: {port_baudrate}')

        self._logger.debug('Выбран порт: {port_name} ({port_baudrate} бод)')

        self._port_name = port_name
        self._baudrate  = port_baudrate
