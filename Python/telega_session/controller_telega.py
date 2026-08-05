"""Контроллер сессии МК и межпроцессорного обмена с GUI."""

# System imports
import asyncio
import logging
from enum import IntEnum
from multiprocessing import Queue
from pathlib import Path
from queue import Empty
from typing import Any, Awaitable, Callable, Optional

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
from telega_session.decoder_telega import TelegaData
from telega_session.session_event import SessionEvent
from telega_session.session_event_name import SessionEventName

#########################

_GUI_PACKAGE_PERIOD: float = 0.5  # Период отправки последнего пакета в GUI

# ----------------------------------------------------------------

class TelegaStatusCode(IntEnum):
    """Коды результатов команд и завершения сессии тележки."""

    SUCCESS = 0
    UNKNOWN_ERROR = 1
    READ_ERROR = 2
    HANDSHAKE_FAILED = 3
    DEVICE_LOST = 4
    COMMAND_ACK_TIMEOUT = 5
    COMMAND_REJECTED = 6
    STORAGE_ERROR = 7
    CONNECTION_FAILED = 8

# ----------------------------------------------------------------

class UnknownTelegaStatusCode(KeyError):
    """Ошибка обращения к неизвестному коду состояния тележки."""

    def __init__(
            self,
            status_code: TelegaStatusCode,
            message: Optional[str] = None,
    ) -> None:
        """Инициализирует ошибку неизвестного кода.

        Args:
            status_code: Неизвестный код состояния.
            message: Пользовательское описание ошибки.
        """
        self.status_code: TelegaStatusCode = status_code
        self.message: str = message or (
            f'Неизвестный код статуса: {status_code.name} // {status_code.value}'
        )
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message

# ----------------------------------------------------------------

class TelegaStatusCodeMessages:
    """Неизменяемое соответствие кодов состояния пользовательским сообщениям."""

    def __init__(self) -> None:
        """Создаёт таблицу сообщений для всех кодов состояния."""
        self._messages: dict[TelegaStatusCode, str] = {
            TelegaStatusCode.SUCCESS:             "Корректное завершение работы",
            TelegaStatusCode.UNKNOWN_ERROR:       "Неизвестная ошибка",
            TelegaStatusCode.READ_ERROR:          "Ошибка чтения данных",
            TelegaStatusCode.HANDSHAKE_FAILED:    "Ошибка процедуры рукопожатия",
            TelegaStatusCode.DEVICE_LOST:         "Потеря связи с устройством",
            TelegaStatusCode.COMMAND_ACK_TIMEOUT: "Таймаут ожидания подтверждения команды",
            TelegaStatusCode.COMMAND_REJECTED:    "Команда не распознана устройством",
            TelegaStatusCode.STORAGE_ERROR:       "Ошибка CSV-хранилища",
            TelegaStatusCode.CONNECTION_FAILED:   "Ошибка подключения к устройству",
        }

    def __getitem__(self, status_code: TelegaStatusCode) -> str:
        """Возвращает сообщение для указанного кода состояния."""
        if status_code not in self._messages:
            raise UnknownTelegaStatusCode(status_code)
        return self._messages[status_code]

    def __setitem__(self, key: TelegaStatusCode, value: str) -> None:
        """Запрещает изменение таблицы сообщений."""
        raise TypeError('TelegaStatusCodeMessages is read-only')

# ----------------------------------------------------------------

class ControllerTelega(Controller):
    """Связывает команды GUI, внутреннюю шину МК и события сессии."""

    def __init__(
            self,
            bus: McBus,
            mc_logger: McLogger,
            command_queue: Queue,
            response_queue: Queue,
            data_queue: Queue,
    ) -> None:
        """Инициализирует контроллер тележки.

        Args:
            bus: Сигнальная шина сессии МК.
            mc_logger: Фабрика логгеров сессии.
            command_queue: Очередь команд родительского процесса.
            response_queue: Очередь событий для родительского процесса.
            data_queue: Очередь последних пакетов телеметрии.
        """

        # Вызов родительского конструктора
        super().__init__(bus, mc_logger)

        # Используемый в TelegaController логгер
        self._telega_controller_logger: logging.Logger = mc_logger.get_child_logger("Controller.TelegaController")

        # Событие завершения работы контроллера
        self._stop_event: asyncio.Event = asyncio.Event()

        # Код завершения работы с МК и предопределённые текстовые сообщения
        self._telega_status_code: TelegaStatusCode = TelegaStatusCode.SUCCESS
        self._telega_status_code_messages: TelegaStatusCodeMessages = TelegaStatusCodeMessages()

        # Сохраним переданные очереди для межпроцессорного взаимодействия
        self._command_queue = command_queue
        self._response_queue = response_queue
        self._data_queue = data_queue

        # Хранилище и задача записи пакетов в CSV
        self._data_writer: AsyncDataStorageWriter = AsyncDataStorageWriter(self._on_storage_error)

        # Последний пакет для низкочастотной отправки в GUI
        self._latest_package: Optional[TelegaData] = None
        self._latest_package_version: int = 0
        self._package_publishing_task: Optional[asyncio.Task] = None

        # Таска по чтению очереди команд от родительского процесса
        self._reading_cmd_queue_task: Optional[asyncio.Task] = None

        # Результат единственной выполняемой команды МК.
        self._pending_command_result: Optional[asyncio.Future[TelegaStatusCode]] = None

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
        self._bus.command_ack.subscribe(self)
        self._bus.stop_static_init.subscribe(self)
        self._bus.interrupt_measuring.subscribe(self)

        # Запустим задачу чтения входящих команд
        self._reading_cmd_queue_task = asyncio.create_task(self._reading_command_queue())

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """ Процедура выхода из контекстного менеджера """

        self._bus.handshake_done.unsubscribe(self)
        self._bus.command_ack.unsubscribe(self)
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

        try:
            await self._close_storage()
        except (DataStorageError, OSError) as err:
            self._telega_controller_logger.error(f'Ошибка закрытия CSV-хранилища: {err}')
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
        await self._stop_event.wait()

    # =============================================================
    # ============= Обработчики полученных команд =================
    # =============================================================

    # -------------------------------------------------------------
    # Добавление новой IPC-команды:
    # 1. Добавить CommandName, парный *_RESULT и соответствия в
    #    _command_to_handler и ComPortReader._command_result_events.
    # 2. Если команда ждёт ответ МК, использовать Future-пайплайн из
    #    _handshake_init(); иначе сформировать результат непосредственно.
    # 3. Кроме STOP_RUNNING, обработчик отправляет ровно один терминальный
    #    *_RESULT с обязательными success и error_info.
    # -------------------------------------------------------------

    async def _stop_running(self, params: dict[str, Any]) -> None:
        """ Завершение работы контроллера """
        self._telega_controller_logger.debug('Завершение работы контроллера')
        self._stop_event.set()

    async def _handshake_init(self, params: dict[str, Any]) -> None:
        """Инициирует handshake и отправляет его терминальный результат."""
        # Регистрируем Future до McBus.emit(): ответ МК может прийти сразу после
        # записи запроса в COM-порт, и обработчик должен уже видеть Future команды.
        if self._pending_command_result is not None:
            raise RuntimeError('Предыдущая команда МК ещё не завершена')
        command_result = asyncio.get_running_loop().create_future()
        self._pending_command_result = command_result

        try:
            # McBus.emit() завершится после получения ответа либо таймаута внутри
            # AsyncComPortDevice.on_handshake_init(). Результат в Future запишет
            # on_handshake_done() или on_handshake_failed().
            self._telega_controller_logger.debug('Инициирование процедуры рукопожатия')
            await self._bus.handshake_init.emit()

            # Возврат из emit() без результата означает нарушение внутреннего
            # протокола обработки команды.
            if not command_result.done():
                command_result.set_result(TelegaStatusCode.UNKNOWN_ERROR)

            # Преобразуем внутренний код результата в терминальный SessionEvent.
            status_code = await command_result
            success = status_code == TelegaStatusCode.SUCCESS
            error_info = '' if success else self._telega_status_code_messages[status_code]
            await self._send_session_event(
                SessionEvent(
                    event=SessionEventName.HANDSHAKE_INIT_RESULT,
                    params={'success': success, 'error_info': error_info},
                )
            )

            # Неуспешный handshake не позволяет продолжать текущую сессию.
            if not success:
                self._telega_status_code = status_code
                self._stop_event.set()
        finally:
            # Очищаем только Future, созданный текущим обработчиком команды.
            if self._pending_command_result is command_result:
                self._pending_command_result = None

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
            await self._data_writer.set_file(file_path)
        except (DataStorageError, OSError) as err:
            self._telega_controller_logger.error(f'Не удалось подготовить CSV-файл {file_path}: {err}')
            await self._send_saving_file_result(False, str(file_path), str(err))
            return

        self._telega_controller_logger.info(f'Подготовлен CSV-файл: {file_path}')
        await self._send_saving_file_result(True, str(file_path))

    async def _start_static_init(self, params: dict[str, Any]) -> None:
        """Запускает статический набор и отправляет результат команды."""
        if not self._ensure_storage_ready():
            await self._send_session_event(
                SessionEvent(
                    event=SessionEventName.START_STATIC_INIT_RESULT,
                    params={
                        'success': False,
                        'error_info': (
                            'Перед запуском статического набора необходимо '
                            'выполнить SET_SAVING_FILE'
                        ),
                    },
                )
            )
            return

        # Future-пайплайн описан в _handshake_init(). Для обычной команды
        # результат устанавливают обработчики ACK, отказа или таймаута.
        if self._pending_command_result is not None:
            raise RuntimeError('Предыдущая команда МК ещё не завершена')
        command_result = asyncio.get_running_loop().create_future()
        self._pending_command_result = command_result

        try:
            self._telega_controller_logger.debug('Запуск набора статического буфера')
            await self._bus.enable_package_publishing.emit()
            await self._bus.start_static_init.emit()

            if not command_result.done():
                command_result.set_result(TelegaStatusCode.UNKNOWN_ERROR)

            status_code = await command_result
            success = status_code == TelegaStatusCode.SUCCESS
            error_info = '' if success else self._telega_status_code_messages[status_code]
            await self._send_session_event(
                SessionEvent(
                    event=SessionEventName.START_STATIC_INIT_RESULT,
                    params={'success': success, 'error_info': error_info},
                )
            )

            if not success:
                self._telega_status_code = status_code
                self._stop_event.set()
        finally:
            if self._pending_command_result is command_result:
                self._pending_command_result = None

    async def _start_measuring(self, params: dict[str, Any]) -> None:
        """Запускает измерения и отправляет результат команды."""
        if not self._ensure_storage_ready():
            await self._send_session_event(
                SessionEvent(
                    event=SessionEventName.START_MEASURING_RESULT,
                    params={
                        'success': False,
                        'error_info': (
                            'Перед запуском измерений необходимо выполнить '
                            'SET_SAVING_FILE'
                        ),
                    },
                )
            )
            return

        # Future-пайплайн описан в _handshake_init(). Здесь результат
        # устанавливают обработчики ACK, отказа или таймаута обычной команды.
        if self._pending_command_result is not None:
            raise RuntimeError('Предыдущая команда МК ещё не завершена')
        command_result = asyncio.get_running_loop().create_future()
        self._pending_command_result = command_result

        try:
            self._telega_controller_logger.debug('Запуск измерений')
            await self._bus.enable_package_publishing.emit()
            await self._bus.start_measuring.emit()

            if not command_result.done():
                command_result.set_result(TelegaStatusCode.UNKNOWN_ERROR)

            status_code = await command_result
            success = (status_code == TelegaStatusCode.SUCCESS)
            error_info = '' if success else self._telega_status_code_messages[status_code]
            await self._send_session_event(
                SessionEvent(
                    event=SessionEventName.START_MEASURING_RESULT,
                    params={'success': success, 'error_info': error_info},
                )
            )

            # Отказ МК, таймаут или нарушение протокола считаются фатальными.
            if not success:
                self._telega_status_code = status_code
                self._stop_event.set()

        finally:
            if self._pending_command_result is command_result:
                self._pending_command_result = None

    async def _stop_measuring(self, params: dict[str, Any]) -> None:
        """Останавливает измерения, закрывает CSV и отправляет результат."""
        # Future-пайплайн описан в _handshake_init(). Здесь результат
        # устанавливают обработчики ACK, отказа или таймаута обычной команды.
        if self._pending_command_result is not None:
            raise RuntimeError('Предыдущая команда МК ещё не завершена')
        command_result = asyncio.get_running_loop().create_future()
        self._pending_command_result = command_result

        try:
            self._telega_controller_logger.debug('Остановка измерений')
            await self._bus.stop_measuring.emit()

            if not command_result.done():
                command_result.set_result(TelegaStatusCode.UNKNOWN_ERROR)

            status_code = await command_result
            if status_code != TelegaStatusCode.SUCCESS:
                await self._send_session_event(
                    SessionEvent(
                        event=SessionEventName.STOP_MEASURING_RESULT,
                        params={
                            'success': False,
                            'error_info': self._telega_status_code_messages[status_code],
                        },
                    )
                )
                self._telega_status_code = status_code
                self._stop_event.set()
                return

            # После успешного ACK дожидаемся пакетов и закрываем CSV, поэтому
            # STOP_MEASURING_RESULT подтверждает завершение всей операции.
            try:
                await self._close_storage()
            except (DataStorageError, OSError) as err:
                # Фоновая ошибка записи уже отправила SESSION_ERROR и тем самым
                # завершила ожидающую GUI-команду без дополнительного *_RESULT.
                if self._telega_status_code == TelegaStatusCode.STORAGE_ERROR:
                    return

                error_info = f'{self._telega_status_code_messages[TelegaStatusCode.STORAGE_ERROR]}: {err}'
                await self._send_session_event(
                    SessionEvent(
                        event=SessionEventName.STOP_MEASURING_RESULT,
                        params={'success': False, 'error_info': error_info},
                    )
                )
                self._telega_status_code = TelegaStatusCode.STORAGE_ERROR
                self._stop_event.set()
                return

            await self._send_session_event(
                SessionEvent(
                    event=SessionEventName.STOP_MEASURING_RESULT,
                    params={'success': True, 'error_info': ''},
                )
            )
        finally:
            if self._pending_command_result is command_result:
                self._pending_command_result = None

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
        """Завершает Future handshake успешным результатом."""
        command_result = self._pending_command_result
        if command_result is not None and not command_result.done():
            command_result.set_result(TelegaStatusCode.SUCCESS)

    async def on_command_ack(self) -> None:
        """Завершает Future текущей обычной команды успешным результатом."""
        command_result = self._pending_command_result
        if command_result is not None and not command_result.done():
            command_result.set_result(TelegaStatusCode.SUCCESS)

    async def on_stop_static_init(self) -> None:
        """Закрывает CSV и сообщает о фактическом завершении static init."""
        try:
            await self._close_storage()
        except (DataStorageError, OSError) as err:
            await self._on_storage_error(err, self._data_writer.file_path)
            return

        await self._send_session_event(
            SessionEvent(event=SessionEventName.STATIC_INIT_COMPLETED)
        )

    async def on_interrupt_measuring(self) -> None:
        """ Обработчик сигнала INTERRUPT_MEASURING.

        Отмена _measuring_pipeline_task.
        """
        if self._telega_status_code == TelegaStatusCode.SUCCESS:
            self._telega_status_code = TelegaStatusCode.UNKNOWN_ERROR
            await self._send_session_event(
                SessionEvent(
                    event=SessionEventName.SESSION_ERROR,
                    params={
                        'error_code': TelegaStatusCode.UNKNOWN_ERROR.name,
                        'error_info': self._telega_status_code_messages[
                            TelegaStatusCode.UNKNOWN_ERROR
                        ],
                    },
                )
            )
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
        await self._send_session_event(
            SessionEvent(
                event=SessionEventName.SESSION_ERROR,
                params={
                    'error_code': TelegaStatusCode.READ_ERROR.name,
                    'error_info': (
                        f'{self._telega_status_code_messages[TelegaStatusCode.READ_ERROR]}: {err}'
                    ),
                },
            )
        )
        self._stop_event.set()

    async def on_handshake_failed(self) -> None:
        """Обработчик сигнала HANDSHAKE_FAILED.

        Завершает Future handshake отрицательным результатом. Остановку сессии
        выполняет командный обработчик после отправки HANDSHAKE_INIT_RESULT.
        """
        command_result = self._pending_command_result
        if command_result is not None and not command_result.done():
            command_result.set_result(TelegaStatusCode.HANDSHAKE_FAILED)
            return

        self._telega_status_code = TelegaStatusCode.HANDSHAKE_FAILED
        self._stop_event.set()

    async def on_device_lost(self) -> None:
        """Обработчик сигнала DEVICE_LOST.

        Установим TelegaStatusCode.DEVICE_LOST
        и вызовем родительский обработчик сигнала.
        """
        self._telega_status_code = TelegaStatusCode.DEVICE_LOST
        await self._send_session_event(
            SessionEvent(
                event=SessionEventName.SESSION_ERROR,
                params={
                    'error_code': TelegaStatusCode.DEVICE_LOST.name,
                    'error_info': self._telega_status_code_messages[
                        TelegaStatusCode.DEVICE_LOST
                    ],
                },
            )
        )
        self._stop_event.set()

    async def on_command_ack_timeout(self) -> None:
        """Обработчик сигнала COMMAND_ACK_TIMEOUT.

        Завершает Future текущей команды отрицательным результатом. Остановку
        сессии выполняет командный обработчик после отправки `*_RESULT`.
        """
        command_result = self._pending_command_result
        if command_result is not None and not command_result.done():
            command_result.set_result(TelegaStatusCode.COMMAND_ACK_TIMEOUT)
            return

        self._telega_status_code = TelegaStatusCode.COMMAND_ACK_TIMEOUT
        self._stop_event.set()

    async def on_command_rejected(self) -> None:
        """Обработчик сигнала COMMAND_REJECTED.

        Завершает Future текущей команды отрицательным результатом. Остановку
        сессии выполняет командный обработчик после отправки `*_RESULT`.
        """
        command_result = self._pending_command_result
        if command_result is not None and not command_result.done():
            command_result.set_result(TelegaStatusCode.COMMAND_REJECTED)
            return

        self._telega_status_code = TelegaStatusCode.COMMAND_REJECTED
        self._stop_event.set()

    # =============================================================
    # =========== Метод для работы с очередью команд ==============
    # =============================================================

    async def _reading_command_queue(self) -> None:
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
                try:
                    await coro_handler(command_request.params)
                except asyncio.CancelledError:
                    raise
                except Exception as err:
                    self._telega_controller_logger.exception(
                        f'Непредвиденная ошибка выполнения команды '
                        f'{command_request.command}: {err}'
                    )
                    self._telega_status_code = TelegaStatusCode.UNKNOWN_ERROR
                    await self._send_session_event(
                        SessionEvent(
                            event=SessionEventName.SESSION_ERROR,
                            params={
                                'error_code': TelegaStatusCode.UNKNOWN_ERROR.name,
                                'error_info': str(err),
                            },
                        )
                    )
                    self._stop_event.set()
                    return

        except asyncio.CancelledError:
            self._telega_controller_logger.debug('Таска _reading_command_queue отменена')
            raise

    # =============================================================
    # ====== Отправка ответов/данных в управляющий процесс ========
    # =============================================================

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
                                       error_info: str = '') -> None:
        """Отправляет результат команды SET_SAVING_FILE в GUI.

        Args:
            success: Успешность подготовки файла.
            filepath: Абсолютный путь к запрошенному файлу.
            error_info: Описание ошибки при неуспешном результате.
        """
        await self._send_session_event(
            SessionEvent(
                event=SessionEventName.SET_SAVING_FILE_RESULT,
                params={
                    'success': success,
                    'error_info': error_info,
                    'filepath': filepath,
                },
            )
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

    # =============================================================
    # ======== Методы для работы с хранилищем телеметрии ==========
    # =============================================================

    def _ensure_storage_ready(self) -> bool:
        """Проверяет готовность хранилища перед запуском этапа измерений."""
        return self._data_writer.is_open

    async def _close_storage(self) -> None:
        """Дожидается декодированных пакетов и закрывает CSV-файл.

        Raises:
            DataStorageError: Фоновая запись CSV завершилась ошибкой.
            OSError: Не удалось сбросить буфер или закрыть файл.
        """
        await self._bus.drain_packages.emit()
        await self._data_writer.close()

    async def _on_storage_error(self, err: Exception, file_path: Optional[Path]) -> None:
        """Сообщает об ошибке CSV и завершает текущую сессию.

        Args:
            err: Ошибка подготовки, записи или закрытия файла.
            file_path: Путь проблемного файла, если он известен.
        """
        self._telega_controller_logger.error(f'Ошибка CSV-хранилища: {err}')
        if self._telega_status_code == TelegaStatusCode.STORAGE_ERROR:
            self._stop_event.set()
            return

        self._telega_status_code = TelegaStatusCode.STORAGE_ERROR
        error_info = f'{self._telega_status_code_messages[TelegaStatusCode.STORAGE_ERROR]}: {err}'
        await self._send_session_event(
            SessionEvent(
                event=SessionEventName.SESSION_ERROR,
                params={
                    'error_code': TelegaStatusCode.STORAGE_ERROR.name,
                    'error_info': error_info,
                    'filepath': str(file_path) if file_path is not None else '',
                },
            )
        )
        self._stop_event.set()
