# System imports
import asyncio
import logging
from enum import IntEnum
from multiprocessing import Queue
from queue import Empty
from typing import Callable, Awaitable, Optional

# External imports

# User imports
from async_mc_controller.signal_bus import McBus
from async_mc_controller.logger import McLogger
from async_mc_controller.byte_source.read_error import ReadError
from async_mc_controller.controller import Controller
from telega_session.decoder_telega import TelegaData

#########################

_RESPONSE_TIMEOUT: float = 2.0    # Таймаут выставления событий

# ----------------------------------------------------------------

class TelegaStatusCode(IntEnum):
    SUCCESS = 0
    UNKNOWN_ERROR = 1
    READ_ERROR = 2
    HANDSHAKE_FAILED = 3
    DEVICE_LOST = 4
    COMMAND_ACK_TIMEOUT = 5
    COMMAND_REJECTED = 6

# ----------------------------------------------------------------

class UnknownTelegaStatusCode(KeyError):
    def __init__(self, status_code: TelegaStatusCode, message: str = None):
        self.status_code = status_code
        self.message = message or f"Неизвестный код статуса: {status_code.name} // {status_code.value}"
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message

# ----------------------------------------------------------------

class TelegaStatusCodeMessages:
    def __init__(self):
        self.__messages: dict[TelegaStatusCode, str] = {
            TelegaStatusCode.SUCCESS:             "Корректное завершение работы",
            TelegaStatusCode.UNKNOWN_ERROR:       "Неизвестная ошибка",
            TelegaStatusCode.READ_ERROR:          "Ошибка чтения данных",
            TelegaStatusCode.HANDSHAKE_FAILED:     "Ошибка процедуры рукопожатия",
            TelegaStatusCode.DEVICE_LOST:         "Потеря связи с устройством",
            TelegaStatusCode.COMMAND_ACK_TIMEOUT: "Таймаут ожидания подтверждения команды",
            TelegaStatusCode.COMMAND_REJECTED:    "Команда не распознана устройством",
        }

    def __getitem__(self, status_code: TelegaStatusCode) -> str:
        if status_code in self.__messages.keys():
            return self.__messages[status_code]
        else:
            raise UnknownTelegaStatusCode(status_code)

    def __setitem__(self, key, value):
        raise TypeError("TelegaStatusCodeMessage is read-only")

# ----------------------------------------------------------------

class ControllerTelega(Controller):
    """
    Список сообщений, которые могут быть отправлены в responce_queue:
    * HANDSHAKE_DONE - процедура рукопожатия выполнена успешно
    * HANDSHAKE_FAILED - процедура рукопожатия завершена с ошибкой
    * STOP_CALIBRATION - получено сообщение от МК о завершении калибровки
    * STOP_STATIC_INIT - получено сообщение от МК о завершении набора статического буфера
    * UNKNOWN_ERROR - поймано непредвиденное исключение
    * READ_ERROR - получено исключение ReadError от AsyncComPort
    * DEVICE_LOST - устройство не ответило на HEARTBEAT
    * COMMAND_ACK_TIMEOUT - таймаут подтверждения получения команды МК
    * COMMAND_REJECTED - МК получил неизвестную ему команду
    """
    def __init__(self, bus: McBus, mc_logger: McLogger,
                 command_queue: Queue, response_queue: Queue, data_queue: Queue):

        # Вызов родительского конструктора
        super().__init__(bus, mc_logger)

        # Используемый в TelegaController логгер
        self._telega_controller_logger: logging.Logger = mc_logger.get_child_logger("Controller.TelegaController")

        # Событие завершения работы контроллера
        self._stop_event: asyncio.Event = asyncio.Event()

        # Код завершения работы с МК и предопределённые текстовые сообщения
        self._telega_status_code: TelegaStatusCode = TelegaStatusCode.SUCCESS
        self._telega_status_code_messages = TelegaStatusCodeMessages()

        # Сохраним переданные очереди для межпроцессорного взаимодействия
        self._command_queue = command_queue
        self._response_queue = response_queue
        self._data_queue = data_queue

        # Таска по чтению очереди команд от родительского процесса
        self._reading_cmd_queue_task: Optional[asyncio.Task] = None

        # Словарь для соответствия полученного сообщения и метода отработки.
        self._command_to_handler: dict[str, Callable[[], Awaitable[None]]] = {
            "STOP_RUNNING": self._stop_running,
            "HANDSHAKE_INIT": self._handshake_init,
            "START_CALIBRATION": self._start_calibration,
            "START_STATIC_INIT": self._start_static_init,
            "START_MEASURING": self._start_measuring,
            "STOP_MEASURING": self._stop_measuring,
        }

    # =============================================================
    # ======= Методы для работы в контекстном менеджере ===========
    # =============================================================

    async def __aenter__(self) -> 'Controller':
        """ Процедура входа в контекстный менеджера """
        await super().__aenter__()

        # Самостоятельная подписка на специфичные события шины
        self._bus.handshake_done.subscribe(self)
        self._bus.stop_calibration.subscribe(self)
        self._bus.stop_static_init.subscribe(self)
        self._bus.interrupt_measuring.subscribe(self)

        # Запустим задачу чтения входящих команд
        self._reading_cmd_queue_task = asyncio.create_task(self._reading_command_queue())

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """ Процедура выхода из контекстного менеджера """

        self._bus.handshake_done.unsubscribe(self)
        self._bus.stop_calibration.unsubscribe(self)
        self._bus.stop_static_init.unsubscribe(self)
        self._bus.interrupt_measuring.unsubscribe(self)

        # Отменим задачу чтения входящих команд
        await self._cancel_task(self._reading_cmd_queue_task)
        self._reading_cmd_queue_task = None

        if self._telega_status_code == TelegaStatusCode.SUCCESS:
            self._telega_controller_logger.info(
                f'Код завершения работы с устройством: {self._telega_status_code} '
                f'// {self._telega_status_code_messages[self._telega_status_code]}'
            )
            self._telega_controller_logger.info("Завершение работы через STOP_EXECUTING")
            await self._bus.stop_executing.emit()
        else:
            self._telega_controller_logger.error(
                f'Код завершения работы с устройством: {self._telega_status_code} '
                f'// {self._telega_status_code_messages[self._telega_status_code]}'
            )
            self._telega_controller_logger.info("Завершение работы через INTERRUPT_MEASURING")
            await self._bus.interrupt_measuring.emit()

        return await super().__aexit__(exc_type, exc_val, exc_tb)

    # =============================================================
    # ===================== Публичные методы ======================
    # =============================================================

    async def running(self) -> None:
        """ Метод для начала и завершения работы с МК.

        Вызывается внутри контекстного менеджера и управляет
        жизненным циклом программы.

        Пример использования:
            async with McSession(decoder, com_port, controller):
                await controller.running()
            print(decoder)
        """
        self._stop_event.clear()
        await self._stop_event.wait()

        # Процедура завершения работы перед выходом из контекстного менеджера
        # await self._send_info_msg(
        #     f'Код завершения работы с устройством: {self._telega_status_code} '
        #     f'// {self._telega_status_code_messages[self._telega_status_code]}'
        # )

    # =============================================================
    # =================== Внутренняя логика =======================
    # =============================================================

    async def _stop_running(self) -> None:
        """ Завершение работы контроллера """
        self._telega_controller_logger.debug('Завершение работы контроллера')
        self._stop_event.set()

    async def _handshake_init(self) -> None:
        """ Инициирование процедуры рукопожатия """
        self._telega_controller_logger.debug('Инициирование процедуры рукопожатия')
        await self._bus.handshake_init.emit()

    async def _start_calibration(self) -> None:
        """ Запуск калибровки датчиков """
        self._telega_controller_logger.debug('Запуск калибровки датчиков')
        await self._bus.start_calibration.emit()

    async def _start_static_init(self) -> None:
        """ Запуск набора статического буфера """
        self._telega_controller_logger.debug('Запуск набора статического буфера')
        await self._bus.start_static_init.emit()

    async def _start_measuring(self) -> None:
        """ Запуск измерений """
        self._telega_controller_logger.debug('Запуск измерений')
        await self._bus.start_measuring.emit()

    async def _stop_measuring(self) -> None:
        """ Остановка измерений """
        self._telega_controller_logger.debug('Остановка измерений')
        await self._bus.stop_measuring.emit()

    async def _reading_command_queue(self):
        """Неблокирующее чтение данных из self._command_queue"""

        self._telega_controller_logger.debug('Запуск _reading_command_queue')

        def get_input_command(command_queue: Queue) -> Optional[str]:
            """Ожидает команду ограниченное время, чтобы поток мог завершиться."""
            try:
                return command_queue.get(timeout=0.1)
            except Empty:
                return None

        try:
            while True:
                cmd: Optional[str] = await asyncio.to_thread(get_input_command, self._command_queue)
                if cmd is None:
                    continue
                if cmd not in self._command_to_handler.keys():
                    self._telega_controller_logger.warning(f'Получена неизвестная команда {cmd} из _command_queue!')
                    continue

                self._telega_controller_logger.debug(f'Получена команда {cmd}')
                coro_handler = self._command_to_handler[cmd]
                await coro_handler()

        except asyncio.CancelledError:
            self._telega_controller_logger.debug('Таска _reading_command_queue отменена')

    async def _send_package(self, data_package: TelegaData) -> None:
        """ Оправка пакета data_package в data_queue """
        try:
            await asyncio.to_thread(self._data_queue.put, data_package)
        except Exception as e:
            self._telega_controller_logger.error(f"Не удалось отправить пакет в data_queue: {e}")

    async def _send_info_msg(self, msg: str) -> None:
        """ Отправка информационных сообщений в response_queue """
        try:
            await asyncio.to_thread(self._response_queue.put, msg)
        except Exception as e:
            self._telega_controller_logger.error(f"Не удалось отправить пакет в response_queue: {e}")

    # =============================================================
    # =================== Обработчики сигналов ====================
    # =============================================================

    async def on_package_ready(self, data_package: TelegaData) -> None:
        """Обработчик сигнала PACKAGE_READY.

        Отправка полученного пакета в очередь data_queue

        Args:
            data_package: Декодированный пакет данных
        """
        await self._send_package(data_package)

    async def on_handshake_done(self) -> None:
        """Обработчик сигнала HANDSHAKE_DONE от декодера.

        Отправка HANDSHAKE_DONE родительскому процессу
        через response_queue.
        """
        await self._send_info_msg("HANDSHAKE_DONE")

    async def on_stop_calibration(self) -> None:
        """ Обработчик сигнала STOP_CALIBRATION от декодера.

        Отправка STOP_CALIBRATION родительскому процессу
        через response_queue.
        """
        await self._send_info_msg("STOP_CALIBRATION")

    async def on_stop_static_init(self) -> None:
        """ Обработчик сигнала STOP_STATIC_INIT от декодера.

        Отправка STOP_STATIC_INIT родительскому процессу
        через response_queue.
        """
        await self._send_info_msg("STOP_STATIC_INIT")

    async def on_interrupt_measuring(self) -> None:
        """ Обработчик сигнала INTERRUPT_MEASURING.

        Отмена _measuring_pipeline_task.
        """
        self._telega_status_code = TelegaStatusCode.UNKNOWN_ERROR
        await self._send_info_msg("UNKNOWN_ERROR")
        self._stop_event.set()

    async def on_read_error(self, err: ReadError) -> None:
        """Обработчик сигнала READ_ERROR.

        Отменим self._measuring_pipeline_task, установим TelegaStatusCode.READ_ERROR
        и вызовем родительский обработчик сигнала.

        Args:
            err (ReadError): Исключение, которое привело к остановке чтения.
        """
        self._telega_controller_logger.error(f'Получено исключение: {err}')
        self._telega_status_code = TelegaStatusCode.READ_ERROR
        self._stop_event.set()
        await self._send_info_msg("READ_ERROR")

    async def on_handshake_failed(self) -> None:
        """Обработчик сигнала HANDSHAKE_FAILED.

        Установим TelegaStatusCode.HANDSHAKE_FAILED
        и вызовем родительский обработчик сигнала.
        """
        self._telega_status_code = TelegaStatusCode.HANDSHAKE_FAILED
        await self._send_info_msg("HANDSHAKE_FAILED")
        self._stop_event.set()

    async def on_device_lost(self) -> None:
        """Обработчик сигнала DEVICE_LOST.

        Установим TelegaStatusCode.DEVICE_LOST
        и вызовем родительский обработчик сигнала.
        """
        self._telega_status_code = TelegaStatusCode.DEVICE_LOST
        await self._send_info_msg("DEVICE_LOST")
        self._stop_event.set()

    async def on_command_ack_timeout(self) -> None:
        """Обработчик сигнала COMMAND_ACK_TIMEOUT.

        Установим TelegaStatusCode.COMMAND_ACK_TIMEOUT
        и вызовем родительский обработчик сигнала.
        """
        self._telega_status_code = TelegaStatusCode.COMMAND_ACK_TIMEOUT
        await self._send_info_msg("COMMAND_ACK_TIMEOUT")
        self._stop_event.set()

    async def on_command_rejected(self) -> None:
        """Обработчик сигнала COMMAND_REJECTED.

        Установим TelegaStatusCode.COMMAND_REJECTED
        и вызовем родительский обработчик сигнала.
        """
        self._telega_status_code = TelegaStatusCode.COMMAND_REJECTED
        await self._send_info_msg("COMMAND_REJECTED")
        self._stop_event.set()
