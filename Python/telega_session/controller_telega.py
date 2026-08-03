# System imports
import asyncio
import logging
from enum import IntEnum
from multiprocessing import Queue
from pathlib import Path
from queue import Empty
from typing import Any, Callable, Awaitable, Optional

# External imports
from pydantic import ValidationError

# User imports
from async_mc_controller.signal_bus import McBus
from async_mc_controller.logger import McLogger
from async_mc_controller.byte_source.read_error import ReadError
from async_mc_controller.controller import Controller
from telega_session.command_name import CommandName
from telega_session.command_request import CommandRequest
from telega_session.data_storage import AsyncDataStorageWriter, DataStorageError
from telega_session.decoder_telega import DecoderTelega, TelegaData
from telega_session.session_event import SessionEvent
from telega_session.session_event_name import SessionEventName

#########################

_RESPONSE_TIMEOUT: float = 2.0    # Таймаут выставления событий
_GUI_PACKAGE_PERIOD: float = 0.5  # Период отправки последнего пакета в GUI

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
            TelegaStatusCode.HANDSHAKE_FAILED:    "Ошибка процедуры рукопожатия",
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
    * STOP_STATIC_INIT - получено сообщение от МК о завершении набора статического буфера
    * UNKNOWN_ERROR - поймано непредвиденное исключение
    * READ_ERROR - получено исключение ReadError от AsyncComPort
    * DEVICE_LOST - устройство не ответило на HEARTBEAT
    * COMMAND_ACK_TIMEOUT - таймаут подтверждения получения команды МК
    * COMMAND_REJECTED - МК получил неизвестную ему команду
    """
    def __init__(self, bus: McBus, mc_logger: McLogger, decoder: DecoderTelega,
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
        self._decoder: DecoderTelega = decoder

        # Хранилище и задача записи пакетов в CSV
        self._data_writer: AsyncDataStorageWriter = AsyncDataStorageWriter(self._on_storage_error)

        # Последний пакет для низкочастотной отправки в GUI
        self._latest_package: Optional[TelegaData] = None
        self._latest_package_version: int = 0
        self._package_publishing_task: Optional[asyncio.Task] = None

        # Таска по чтению очереди команд от родительского процесса
        self._reading_cmd_queue_task: Optional[asyncio.Task] = None

        # Словарь для соответствия полученного сообщения и метода отработки.
        self._command_to_handler: dict[CommandName, Callable[[dict[str, Any]], Awaitable[None]]] = {
            CommandName.STOP_RUNNING: self._stop_running,
            CommandName.HANDSHAKE_INIT: self._handshake_init,
            CommandName.SET_SAVING_FILE: self._set_saving_file,
            CommandName.START_STATIC_INIT: self._start_static_init,
            CommandName.START_MEASURING: self._start_measuring,
            CommandName.STOP_MEASURING: self._stop_measuring,
        }

    # =============================================================
    # ======= Методы для работы в контекстном менеджере ===========
    # =============================================================

    async def __aenter__(self) -> 'Controller':
        """ Процедура входа в контекстный менеджера """
        await self._data_writer.start()
        self._package_publishing_task = asyncio.create_task(self._package_publishing_loop())
        await super().__aenter__()

        # Самостоятельная подписка на специфичные события шины
        self._bus.handshake_done.subscribe(self)
        self._bus.stop_static_init.subscribe(self)
        self._bus.interrupt_measuring.subscribe(self)

        # Запустим задачу чтения входящих команд
        self._reading_cmd_queue_task = asyncio.create_task(self._reading_command_queue())

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """ Процедура выхода из контекстного менеджера """

        self._bus.handshake_done.unsubscribe(self)
        self._bus.stop_static_init.unsubscribe(self)
        self._bus.interrupt_measuring.unsubscribe(self)

        # Отменим задачу чтения входящих команд
        await self._cancel_task(self._reading_cmd_queue_task)
        self._reading_cmd_queue_task = None
        await self._cancel_task(self._package_publishing_task)
        self._package_publishing_task = None

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

        await self._close_storage()
        try:
            await self._data_writer.stop()
        except (DataStorageError, OSError) as err:
            self._telega_controller_logger.error(f'Ошибка завершения CSV-хранилища: {err}')

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

    async def _stop_running(self, params: dict[str, Any]) -> None:
        """ Завершение работы контроллера """
        self._telega_controller_logger.debug('Завершение работы контроллера')
        self._stop_event.set()

    async def _handshake_init(self, params: dict[str, Any]) -> None:
        """ Инициирование процедуры рукопожатия """
        self._telega_controller_logger.debug('Инициирование процедуры рукопожатия')
        await self._bus.handshake_init.emit()

    async def _set_saving_file(self, params: dict[str, Any]) -> None:
        """Подготавливает новый CSV-файл по команде GUI.

        Args:
            params: Параметры команды с обязательным строковым ``filepath``.
        """
        filepath = params.get('filepath')
        if not isinstance(filepath, str) or not filepath:
            await self._send_saving_file_result(
                success=False,
                filepath=filepath if isinstance(filepath, str) else '',
                error_info='Параметр filepath должен быть непустой строкой',
            )
            return

        file_path = Path(filepath)
        if not file_path.is_absolute():
            await self._send_saving_file_result(
                success=False,
                filepath=filepath,
                error_info='Путь к CSV-файлу должен быть абсолютным',
            )
            return

        try:
            await self._decoder.wait_for_packages()
            await self._data_writer.set_file(file_path)
        except (DataStorageError, OSError) as err:
            self._telega_controller_logger.error(f'Не удалось подготовить CSV-файл {file_path}: {err}')
            await self._send_saving_file_result(False, str(file_path), str(err))
            return

        self._telega_controller_logger.info(f'Подготовлен CSV-файл: {file_path}')
        await self._send_saving_file_result(True, str(file_path))

    async def _start_static_init(self, params: dict[str, Any]) -> None:
        """ Запуск набора статического буфера """
        if not await self._ensure_storage_ready():
            return
        self._telega_controller_logger.debug('Запуск набора статического буфера')
        await self._bus.start_static_init.emit()

    async def _start_measuring(self, params: dict[str, Any]) -> None:
        """ Запуск измерений """
        if not await self._ensure_storage_ready():
            return
        self._telega_controller_logger.debug('Запуск измерений')
        await self._bus.start_measuring.emit()

    async def _stop_measuring(self, params: dict[str, Any]) -> None:
        """ Остановка измерений """
        self._telega_controller_logger.debug('Остановка измерений')
        await self._bus.stop_measuring.emit()
        if await self._close_storage():
            await self._send_session_event(SessionEvent(event=SessionEventName.MEASURING_STOPPED))

    async def _reading_command_queue(self):
        """Неблокирующее чтение данных из self._command_queue"""

        self._telega_controller_logger.debug('Запуск _reading_command_queue')

        def get_command_request(command_queue: Queue) -> Optional[CommandRequest]:
            """Получает и валидирует команду ограниченное время.

            Returns:
                CommandRequest или None, если за отведённое время команда не поступила.

            Raises:
                ValidationError: Если полученные из очереди данные не соответствуют
                    межпроцессорному протоколу команд.
            """
            try:
                command_data = command_queue.get(timeout=0.1)
            except Empty:
                return None

            return CommandRequest.model_validate(command_data)

        try:
            while True:
                try:
                    command_request = await asyncio.to_thread(
                        get_command_request,
                        self._command_queue,
                    )
                    if command_request is None:
                        continue
                except ValidationError as err:
                    self._telega_controller_logger.warning(
                        f'Получена некорректная команда из _command_queue: {err}'
                    )
                    continue

                if command_request.command not in self._command_to_handler.keys():
                    self._telega_controller_logger.warning(
                        f'Получена неизвестная команда {command_request.command} из _command_queue!'
                    )
                    continue

                self._telega_controller_logger.debug(
                    f'Получена команда {command_request.command} с параметрами {command_request.params}'
                )
                coro_handler = self._command_to_handler[command_request.command]
                await coro_handler(command_request.params)

        except asyncio.CancelledError:
            self._telega_controller_logger.debug('Таска _reading_command_queue отменена')

    async def _send_package(self, data_package: TelegaData) -> None:
        """Отправляет последний пакет в data_queue для GUI."""
        try:
            await asyncio.to_thread(self._data_queue.put, data_package)
        except Exception as e:
            self._telega_controller_logger.error(f"Не удалось отправить пакет в data_queue: {e}")

    async def _send_session_event(self, session_event: SessionEvent) -> None:
        """Отправляет событие сессии в response_queue."""
        try:
            await asyncio.to_thread(self._response_queue.put, session_event.model_dump())
        except Exception as e:
            self._telega_controller_logger.error(f"Не удалось отправить событие в response_queue: {e}")

    async def _send_saving_file_result(self,
                                       success: bool,
                                       filepath: str,
                                       error_info: Optional[str] = None) -> None:
        """Отправляет результат команды SET_SAVING_FILE в GUI.

        Args:
            success: Успешность подготовки файла.
            filepath: Абсолютный путь к запрошенному файлу.
            error_info: Описание ошибки при неуспешном результате.
        """
        params: dict[str, Any] = {'success': success, 'filepath': filepath}
        if error_info is not None:
            params['error_info'] = error_info
        await self._send_session_event(
            SessionEvent(event=SessionEventName.SET_SAVING_FILE_RESULT, params=params)
        )

    async def _package_publishing_loop(self) -> None:
        """Отправляет в GUI только самый последний пакет не чаще раза в 500 мс."""
        last_published_version = 0
        try:
            while True:
                await asyncio.sleep(_GUI_PACKAGE_PERIOD)
                if self._latest_package is None:
                    continue
                if self._latest_package_version == last_published_version:
                    continue

                await self._send_package(self._latest_package)
                last_published_version = self._latest_package_version
        except asyncio.CancelledError:
            self._telega_controller_logger.debug('Таска отправки пакетов в GUI отменена')

    async def _ensure_storage_ready(self) -> bool:
        """Проверяет готовность хранилища перед запуском этапа измерений."""
        if self._data_writer.is_open:
            return True

        await self._on_storage_error(
            DataStorageError('Перед запуском измерений необходимо выполнить SET_SAVING_FILE'),
            None,
        )
        return False

    async def _close_storage(self) -> bool:
        """Дожидается декодированных пакетов и закрывает CSV-файл.

        Returns:
            ``True``, если хранилище закрыто без ошибок.
        """
        try:
            await self._decoder.wait_for_packages()
            await self._data_writer.close()
            return True
        except (DataStorageError, OSError) as err:
            await self._on_storage_error(err, self._data_writer.file_path)
            return False

    async def _on_storage_error(self, err: Exception, file_path: Optional[Path]) -> None:
        """Сообщает об ошибке CSV и завершает текущую сессию.

        Args:
            err: Ошибка подготовки, записи или закрытия файла.
            file_path: Путь проблемного файла, если он известен.
        """
        self._telega_controller_logger.error(f'Ошибка CSV-хранилища: {err}')
        self._telega_status_code = TelegaStatusCode.UNKNOWN_ERROR
        await self._send_session_event(
            SessionEvent(
                event=SessionEventName.STORAGE_ERROR,
                params={
                    'filepath': str(file_path) if file_path is not None else '',
                    'error_info': str(err),
                },
            )
        )
        self._stop_event.set()

    # =============================================================
    # =================== Обработчики сигналов ====================
    # =============================================================

    async def on_package_ready(self, data_package: TelegaData) -> None:
        """Обработчик сигнала PACKAGE_READY.

        Передаёт пакет фоновому CSV-писателю и обновляет значение для GUI.

        Args:
            data_package: Декодированный пакет данных
        """
        self._latest_package = data_package
        self._latest_package_version += 1
        try:
            await self._data_writer.write_package(data_package)
        except DataStorageError as err:
            await self._on_storage_error(err, self._data_writer.file_path)

    async def on_handshake_done(self) -> None:
        """Обработчик сигнала HANDSHAKE_DONE от декодера.

        Отправка HANDSHAKE_DONE родительскому процессу
        через response_queue.
        """
        await self._send_session_event(SessionEvent(event=SessionEventName.HANDSHAKE_DONE))

    async def on_stop_static_init(self) -> None:
        """ Обработчик сигнала STOP_STATIC_INIT от декодера.

        Отправка STOP_STATIC_INIT родительскому процессу
        через response_queue.
        """
        if await self._close_storage():
            await self._send_session_event(SessionEvent(event=SessionEventName.STOP_STATIC_INIT))

    async def on_interrupt_measuring(self) -> None:
        """ Обработчик сигнала INTERRUPT_MEASURING.

        Отмена _measuring_pipeline_task.
        """
        if self._telega_status_code == TelegaStatusCode.SUCCESS:
            self._telega_status_code = TelegaStatusCode.UNKNOWN_ERROR
            await self._send_session_event(SessionEvent(event=SessionEventName.UNKNOWN_ERROR))
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
        await self._send_session_event(SessionEvent(event=SessionEventName.READ_ERROR))

    async def on_handshake_failed(self) -> None:
        """Обработчик сигнала HANDSHAKE_FAILED.

        Установим TelegaStatusCode.HANDSHAKE_FAILED
        и вызовем родительский обработчик сигнала.
        """
        self._telega_status_code = TelegaStatusCode.HANDSHAKE_FAILED
        await self._send_session_event(SessionEvent(event=SessionEventName.HANDSHAKE_FAILED))
        self._stop_event.set()

    async def on_device_lost(self) -> None:
        """Обработчик сигнала DEVICE_LOST.

        Установим TelegaStatusCode.DEVICE_LOST
        и вызовем родительский обработчик сигнала.
        """
        self._telega_status_code = TelegaStatusCode.DEVICE_LOST
        await self._send_session_event(SessionEvent(event=SessionEventName.DEVICE_LOST))
        self._stop_event.set()

    async def on_command_ack_timeout(self) -> None:
        """Обработчик сигнала COMMAND_ACK_TIMEOUT.

        Установим TelegaStatusCode.COMMAND_ACK_TIMEOUT
        и вызовем родительский обработчик сигнала.
        """
        self._telega_status_code = TelegaStatusCode.COMMAND_ACK_TIMEOUT
        await self._send_session_event(SessionEvent(event=SessionEventName.COMMAND_ACK_TIMEOUT))
        self._stop_event.set()

    async def on_command_rejected(self) -> None:
        """Обработчик сигнала COMMAND_REJECTED.

        Установим TelegaStatusCode.COMMAND_REJECTED
        и вызовем родительский обработчик сигнала.
        """
        self._telega_status_code = TelegaStatusCode.COMMAND_REJECTED
        await self._send_session_event(SessionEvent(event=SessionEventName.COMMAND_REJECTED))
        self._stop_event.set()
