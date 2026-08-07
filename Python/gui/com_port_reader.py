"""Асинхронный фасад GUI для отдельного процесса сессии МК.

Модуль не зависит от Qt. ``ComPortReader`` скрывает межпроцессный протокол,
последовательно выполняет составные операции и сообщает GUI только об их
предметном результате через высокоуровневые callback-функции.
"""

# System imports
import asyncio
import logging
from dataclasses import dataclass
from multiprocessing import get_context
from multiprocessing.context import BaseContext, Process
from multiprocessing.queues import Queue
from pathlib import Path
from queue import Empty
from typing import Awaitable, Callable, Optional

# External imports
from pydantic import ValidationError

# User imports
from async_mc_controller.config import ComPortConfig, LoggerConfig
from telega_session import (
    CommandName,
    CommandRequest,
    SessionEvent,
    SessionEventName,
    TelegaData,
    start_telega_session,
)

##########################################################


_QUEUE_READ_TIMEOUT_SECONDS = 0.1
_DEFAULT_COMMAND_TIMEOUT_SECONDS = 5.0
_DEFAULT_PROCESS_TIMEOUT_SECONDS = 3.0
_DEFAULT_READER_TIMEOUT_SECONDS = 1.0


# =============================================================
# ================= Долгоживущие зависимости ==================
# =============================================================


@dataclass(frozen=True)
class ComPortReaderCallbacks:
    """Содержит высокоуровневые callback-функции ``ComPortReader``.

    Attributes:
        on_handshake_done: Рукопожатие с МК выполнено.
        on_static_init_started: МК подтвердил запуск статического набора.
        on_static_init_completed: Статический набор завершён.
        on_measuring_started: МК подтвердил запуск измерений.
        on_measuring_stopped: Измерения остановлены, CSV-файл закрыт.
        on_data: Получен очередной пакет измерительных данных.
        on_error: Операция завершилась ошибкой.
    """

    on_handshake_done: Callable[[], None]
    on_static_init_started: Callable[[], None]
    on_static_init_completed: Callable[[], None]
    on_measuring_started: Callable[[], None]
    on_measuring_stopped: Callable[[], None]
    on_data: Callable[[TelegaData], None]
    on_error: Callable[['ComPortReaderException'], None]


@dataclass(frozen=True)
class ComPortSessionConfig:
    """Содержит неизменяемые параметры одной сессии связи с МК.

    Attributes:
        logger_config: Конфигурация логирования дочернего процесса.
        com_port_name: Имя COM-порта.
        raw_stream_file: Путь файла исходного байтового потока.
    """

    logger_config: LoggerConfig
    com_port_name: str
    raw_stream_file: Path


# =============================================================
# ======================== Исключения ==========================
# =============================================================


class ComPortReaderException(RuntimeError):
    """Базовое исключение взаимодействия с сессией МК.

    Args:
        message: Описание ошибки.
        fatal_error: Требует ли ошибка завершения текущей сессии.
    """

    def __init__(self, message: str, fatal_error: bool = True) -> None:
        self._fatal_error: bool = fatal_error
        super().__init__(message)

    @property
    def fatal_error(self) -> bool:
        """Возвращает признак необходимости завершить текущую сессию."""
        return self._fatal_error


class InvalidSessionConfig(ComPortReaderException):
    """Параметры новой сессии некорректны, но повтор допустим."""

    def __init__(self, message: str) -> None:
        super().__init__(message, fatal_error=False)


class InvalidSavingFile(ComPortReaderException):
    """Локальный путь CSV-файла некорректен, но операцию можно повторить."""

    def __init__(self, message: str) -> None:
        super().__init__(message, fatal_error=False)


class SavingFilePreparationError(ComPortReaderException):
    """Дочерняя сессия не смогла подготовить CSV-файл."""

    def __init__(self, saving_file: Path, error_info: str) -> None:
        message = error_info or f'Не удалось подготовить CSV-файл {saving_file}'
        super().__init__(message, fatal_error=False)


class CommandAlreadyPending(ComPortReaderException):
    """Предыдущая командная операция ещё не завершилась."""

    def __init__(self) -> None:
        super().__init__(
            'Предыдущая командная операция ещё не завершилась',
            fatal_error=False,
        )


class SessionNotRunning(ComPortReaderException):
    """Дочерняя сессия с МК не выполняется."""


class NeedConfiguration(ComPortReaderException):
    """Параметры подключения к МК не заданы."""


class CommandResultTimeout(ComPortReaderException):
    """Истёк таймаут ожидания терминального результата команды."""


class CommandExecutionError(ComPortReaderException):
    """Команда завершилась отрицательным фатальным результатом.

    Args:
        command: Команда, которую не удалось выполнить.
        error_info: Описание причины отрицательного результата.
    """

    def __init__(self, command: CommandName, error_info: str) -> None:
        self.command: CommandName = command
        self.error_info: str = error_info
        message = error_info or 'дочерняя сессия не сообщила причину'
        super().__init__(f'Команда {command.name} не выполнена: {message}')


class SessionProtocolError(ComPortReaderException):
    """Нарушен межпроцессный протокол команд или событий сессии."""


class SessionReportedError(ComPortReaderException):
    """Дочерняя сессия сообщила о фатальной ошибке."""


# =============================================================
# ================= Межпроцессный транспорт ====================
# =============================================================


async def _cancel_task(task: Optional[asyncio.Task[None]]) -> None:
    """Отменяет задачу и забирает результат её завершения.

    Args:
        task: Задача для отмены.
    """
    if task is None or task.done():
        return

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


class _SessionProcessTransport:
    """Владеет ресурсами ровно одной дочерней сессии МК.

    Args:
        logger: Логгер родительского процесса.
        session_event_handler: Обработчик события дочерней сессии.
        data_handler: Обработчик пакета измерительных данных.
        error_handler: Обработчик фоновой ошибки транспорта.
    """

    def __init__(
            self,
            logger: logging.Logger,
            session_event_handler: Callable[[SessionEvent], None],
            data_handler: Callable[[TelegaData], None],
            error_handler: Callable[[ComPortReaderException], None]) -> None:
        self._logger: logging.Logger = logger
        self._session_event_handler: Callable[[SessionEvent], None] = (
            session_event_handler
        )
        self._data_handler: Callable[[TelegaData], None] = data_handler
        self._error_handler: Callable[[ComPortReaderException], None] = error_handler

        self._mp_context: BaseContext = get_context('spawn')
        self._mc_session_process: Optional[Process] = None
        self._command_queue: Optional[Queue] = None
        self._response_queue: Optional[Queue] = None
        self._data_queue: Optional[Queue] = None
        self._response_reader_task: Optional[asyncio.Task[None]] = None
        self._data_reader_task: Optional[asyncio.Task[None]] = None
        self._is_stopping: bool = False

    @property
    def is_active(self) -> bool:
        """Возвращает признак активности дочернего процесса."""
        if self._mc_session_process is None:
            return False
        return self._mc_session_process.is_alive()

    # =============================================================
    # ======================== Публичный API ======================
    # =============================================================

    def start(self, session_config: ComPortSessionConfig) -> None:
        """Однократно создаёт очереди, процесс и reader-задачи.

        Args:
            session_config: Параметры запуска дочерней сессии.
        """
        self._command_queue = self._mp_context.Queue()
        self._response_queue = self._mp_context.Queue()
        self._data_queue = self._mp_context.Queue()

        com_port_config = ComPortConfig(
            name=session_config.com_port_name,
            baudrate=115200,
        )
        self._mc_session_process = self._mp_context.Process(
            target=start_telega_session,
            args=(
                session_config.logger_config,
                com_port_config,
                session_config.raw_stream_file,
                self._command_queue,
                self._response_queue,
                self._data_queue,
            ),
            daemon=True,
        )

        self._logger.debug('Запуск дочернего процесса сессии тележки')
        self._mc_session_process.start()
        self._start_reader_tasks()

    async def send_command_request(self, command_request: CommandRequest) -> None:
        """Помещает команду в очередь дочернего процесса.

        Args:
            command_request: Команда и её параметры.

        Raises:
            SessionNotRunning: Дочерний процесс не выполняется.
            ComPortReaderException: Команду не удалось поместить в очередь.
        """
        command_queue = self._command_queue
        if not self.is_active or command_queue is None:
            raise SessionNotRunning('Дочерняя сессия с МК не запущена')

        self._logger.debug(f'Отправка команды {command_request.command.name}')
        try:
            await asyncio.to_thread(
                command_queue.put,
                command_request.model_dump(),
            )
        except (OSError, ValueError) as err:
            raise ComPortReaderException(
                f'Не удалось отправить команду {command_request.command.name}: {err}'
            ) from err

    async def shutdown(self) -> None:
        """Останавливает процесс и освобождает IPC-ресурсы."""
        shutdown_error: Optional[ComPortReaderException] = None
        try:
            await self._shutdown_process()
        except ComPortReaderException as err:
            shutdown_error = err
        finally:
            await self._shutdown_reader_tasks()
            await self._close_queues()

        if shutdown_error is not None:
            raise shutdown_error

    # =============================================================
    # ======================= Работа с IPC ========================
    # =============================================================

    def _start_reader_tasks(self) -> None:
        """Запускает постоянное чтение очередей событий и данных."""
        if self._response_reader_task is not None or self._data_reader_task is not None:
            raise ComPortReaderException('Задачи чтения IPC-очередей уже созданы')

        self._response_reader_task = asyncio.create_task(
            self._read_response_queue(),
            name='telega_response_queue_reader',
        )
        self._data_reader_task = asyncio.create_task(
            self._read_data_queue(),
            name='telega_data_queue_reader',
        )

    @staticmethod
    async def _receive_queue_item(
            source_queue: Queue,
            queue_name: str) -> Optional[object]:
        """Получает один элемент IPC-очереди без блокировки event loop."""

        def get_queue_item(queue: Queue) -> Optional[object]:
            try:
                return queue.get(timeout=_QUEUE_READ_TIMEOUT_SECONDS)
            except Empty:
                return None

        try:
            return await asyncio.to_thread(get_queue_item, source_queue)
        except (EOFError, OSError, ValueError) as err:
            raise ComPortReaderException(
                f'Ошибка чтения очереди {queue_name}: {err}'
            ) from err

    async def _receive_session_event(self) -> Optional[SessionEvent]:
        """Получает и валидирует событие дочерней сессии."""
        if self._response_queue is None:
            raise SessionNotRunning('Очередь событий сессии не создана')

        event_data = await self._receive_queue_item(
            self._response_queue,
            'response_queue',
        )
        if event_data is None:
            return None

        try:
            return SessionEvent.model_validate(event_data)
        except ValidationError as err:
            raise SessionProtocolError(
                f'Получено некорректное событие сессии: {err}'
            ) from err

    async def _receive_data(self) -> Optional[TelegaData]:
        """Получает и проверяет пакет измерительных данных."""
        if self._data_queue is None:
            raise SessionNotRunning('Очередь измерительных данных не создана')

        package = await self._receive_queue_item(self._data_queue, 'data_queue')
        if package is None:
            return None
        if not isinstance(package, TelegaData):
            raise SessionProtocolError(
                'Получен некорректный пакет измерений: '
                f'{type(package).__name__}'
            )
        return package

    async def _read_response_queue(self) -> None:
        """Постоянно читает и передаёт события дочерней сессии."""
        self._logger.debug('Запуск чтения response_queue')
        try:
            while True:
                session_event = await self._receive_session_event()
                if session_event is None:
                    if not self.is_active:
                        if not self._is_stopping:
                            self._error_handler(
                                SessionNotRunning(
                                    'Дочерняя сессия завершилась без SESSION_STOPPED'
                                )
                            )
                        return
                    continue

                self._session_event_handler(session_event)
                if session_event.event is SessionEventName.SESSION_STOPPED:
                    return
        except asyncio.CancelledError:
            self._logger.debug('Чтение response_queue отменено')
            raise
        except ComPortReaderException as err:
            self._error_handler(err)
        except Exception as err:
            self._logger.exception('Неожиданная ошибка чтения response_queue')
            self._error_handler(
                ComPortReaderException(f'Ошибка чтения response_queue: {err}')
            )
        finally:
            self._logger.debug('Чтение response_queue остановлено')

    async def _read_data_queue(self) -> None:
        """Постоянно читает и передаёт пакеты измерительных данных."""
        self._logger.debug('Запуск чтения data_queue')
        try:
            while True:
                package = await self._receive_data()
                if package is None:
                    if not self.is_active:
                        return
                    continue
                self._data_handler(package)
        except asyncio.CancelledError:
            self._logger.debug('Чтение data_queue отменено')
            raise
        except ComPortReaderException as err:
            self._error_handler(err)
        except Exception as err:
            self._logger.exception('Неожиданная ошибка чтения data_queue')
            self._error_handler(
                ComPortReaderException(f'Ошибка чтения data_queue: {err}')
            )
        finally:
            self._logger.debug('Чтение data_queue остановлено')

    # =============================================================
    # ======================== Завершение =========================
    # =============================================================

    async def _shutdown_process(self) -> None:
        """Штатно останавливает процесс либо принудительно завершает его."""
        self._is_stopping = True
        process = self._mc_session_process
        if process is None:
            return

        if self.is_active:
            try:
                await self.send_command_request(
                    CommandRequest(command=CommandName.STOP_RUNNING)
                )
            except ComPortReaderException as err:
                self._logger.warning(
                    f'Не удалось запросить остановку дочерней сессии: {err}'
                )

        if self.is_active:
            await asyncio.to_thread(
                process.join,
                _DEFAULT_PROCESS_TIMEOUT_SECONDS,
            )
        if self.is_active:
            self._logger.warning('Дочерний процесс завершается через terminate()')
            process.terminate()
            await asyncio.to_thread(process.join, 1.0)
        if self.is_active:
            self._logger.warning('Дочерний процесс завершается через kill()')
            process.kill()
            await asyncio.to_thread(process.join, 1.0)
        if self.is_active:
            raise ComPortReaderException(
                'Дочерний процесс не завершился после terminate() и kill()'
            )

        self._logger.debug(f'Дочерний процесс завершён с кодом {process.exitcode}')
        process.close()
        self._mc_session_process = None

    async def _shutdown_reader_tasks(self) -> None:
        """Ожидает естественную остановку readers и отменяет зависшие задачи."""
        for task in (self._response_reader_task, self._data_reader_task):
            if task is None:
                continue
            if not task.done():
                try:
                    await asyncio.wait_for(
                        asyncio.shield(task),
                        timeout=_DEFAULT_READER_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    await _cancel_task(task)
                except ComPortReaderException:
                    pass
            if task.done() and not task.cancelled():
                task.exception()

        self._response_reader_task = None
        self._data_reader_task = None

    async def _close_queues(self) -> None:
        """Закрывает IPC-очереди завершённой сессии."""
        for attribute_name in (
                '_command_queue',
                '_response_queue',
                '_data_queue',
        ):
            source_queue = getattr(self, attribute_name)
            if source_queue is None:
                continue
            source_queue.close()
            await asyncio.to_thread(source_queue.join_thread)
            setattr(self, attribute_name, None)


# =============================================================
# ===================== Асинхронный фасад ======================
# =============================================================


class ComPortReader:
    """Выполняет предметные операции одной сессии связи с МК.

    Args:
        logger: Логгер родительского приложения.
        callbacks: Высокоуровневые обработчики результатов.
    """

    _command_result_events: dict[CommandName, SessionEventName] = {
        CommandName.HANDSHAKE_INIT: SessionEventName.HANDSHAKE_INIT_RESULT,
        CommandName.SET_SAVING_FILE: SessionEventName.SET_SAVING_FILE_RESULT,
        CommandName.START_STATIC_INIT: SessionEventName.START_STATIC_INIT_RESULT,
        CommandName.START_MEASURING: SessionEventName.START_MEASURING_RESULT,
        CommandName.STOP_MEASURING: SessionEventName.STOP_MEASURING_RESULT,
    }
    _result_event_names: frozenset[SessionEventName] = frozenset(
        _command_result_events.values()
    )

    def __init__(
            self,
            logger: logging.Logger,
            callbacks: ComPortReaderCallbacks) -> None:
        self._logger: logging.Logger = logger
        self._callbacks: ComPortReaderCallbacks = callbacks

        self._is_configured: bool = False
        self._is_closed: bool = False
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self._operation_task: Optional[asyncio.Task[None]] = None
        self._pending_result: Optional[asyncio.Future[SessionEvent]] = None
        self._expected_result_event: Optional[SessionEventName] = None
        self._background_error: Optional[ComPortReaderException] = None

        self._transport: Optional[_SessionProcessTransport] = None

    @property
    def is_active(self) -> bool:
        """Возвращает признак активности дочерней сессии."""
        transport = self._transport
        return transport is not None and transport.is_active

    @property
    def is_configured(self) -> bool:
        """Возвращает наличие успешно настроенной сессии."""
        return self._is_configured

    # =============================================================
    # ======================== Публичный API ======================
    # =============================================================

    def configure(self, session_config: ComPortSessionConfig) -> None:
        """Запускает дочернюю сессию и выполняет рукопожатие.

        Args:
            session_config: Параметры одной сессии связи.
        """
        validation_error = self._validate_session_config(session_config)
        if validation_error is not None:
            self._report_error(validation_error)
            return

        self._start_operation(lambda: self._configure(session_config))

    def start_static_init(self, saving_file: Path) -> None:
        """Подготавливает CSV и запускает статический набор.

        Args:
            saving_file: Абсолютный путь CSV-файла.
        """
        validation_error = self._validate_saving_file(saving_file)
        if validation_error is not None:
            self._report_error(validation_error)
            return

        self._start_operation(
            lambda: self._start_static_init(saving_file)
        )

    def start_measuring(self, saving_file: Path) -> None:
        """Подготавливает CSV и запускает измерения.

        Args:
            saving_file: Абсолютный путь CSV-файла.
        """
        validation_error = self._validate_saving_file(saving_file)
        if validation_error is not None:
            self._report_error(validation_error)
            return

        self._start_operation(lambda: self._start_measuring(saving_file))

    def stop_measuring(self) -> None:
        """Запрашивает остановку измерений и закрытие CSV-файла."""
        self._start_operation(self._stop_measuring)

    async def reset(self) -> None:
        """Освобождает сессию и разрешает повторное конфигурирование."""
        if self._is_closed:
            raise ComPortReaderException(
                'Нельзя сбросить окончательно закрытый ComPortReader'
            )
        await self._cleanup(close_reader=False)

    async def shutdown(self) -> None:
        """Освобождает сессию и окончательно закрывает объект."""
        if self._is_closed:
            return
        await self._cleanup(close_reader=True)

    # =============================================================
    # ===================== Предметные операции ===================
    # =============================================================

    async def _configure(self, session_config: ComPortSessionConfig) -> None:
        """Запускает транспорт, выполняет handshake и вызывает callback."""
        if self._is_closed:
            raise ComPortReaderException('ComPortReader окончательно закрыт')
        if self._cleanup_lock.locked():
            raise ComPortReaderException('Выполняется освобождение ресурсов сессии')
        if self._transport is not None:
            raise ComPortReaderException(
                'Перед повторным конфигурированием необходимо выполнить reset()'
            )

        self._is_configured = False
        self._background_error = None
        self._logger.debug(
            'Конфигурирование ComPortReader: '
            f'port={session_config.com_port_name}, '
            f'raw_stream_file={session_config.raw_stream_file}'
        )
        transport = _SessionProcessTransport(
            logger=self._logger,
            session_event_handler=self._session_event_handler,
            data_handler=self._data_handler,
            error_handler=self._transport_error_handler,
        )
        # Ссылка сохраняется до запуска, чтобы reset() освободил даже
        # частично созданные процессом или очередями ресурсы.
        self._transport = transport
        transport.start(session_config)
        await self._execute_command(CommandName.HANDSHAKE_INIT)
        self._is_configured = True
        self._callbacks.on_handshake_done()

    async def _start_static_init(self, saving_file: Path) -> None:
        """Выполняет SET_SAVING_FILE и START_STATIC_INIT."""
        await self._prepare_saving_file(saving_file)
        await self._execute_command(CommandName.START_STATIC_INIT)
        self._callbacks.on_static_init_started()

    async def _start_measuring(self, saving_file: Path) -> None:
        """Выполняет SET_SAVING_FILE и START_MEASURING."""
        await self._prepare_saving_file(saving_file)
        await self._execute_command(CommandName.START_MEASURING)
        self._callbacks.on_measuring_started()

    async def _stop_measuring(self) -> None:
        """Выполняет STOP_MEASURING."""
        await self._execute_command(CommandName.STOP_MEASURING)
        self._callbacks.on_measuring_stopped()

    async def _prepare_saving_file(self, saving_file: Path) -> None:
        """Передаёт дочерней сессии абсолютный путь CSV-файла."""
        await self._execute_command(
            CommandName.SET_SAVING_FILE,
            params={'filepath': str(saving_file)},
        )

    # =============================================================
    # ======================= Владение задачей ====================
    # =============================================================

    def _start_operation(self,
                         operation_factory: Callable[[], Awaitable[None]]) -> None:
        """Создаёт единственную командную задачу и забирает её результат."""
        if self._operation_task is not None and not self._operation_task.done():
            self._report_error(CommandAlreadyPending())
            return

        self._operation_task = asyncio.create_task(
            self._run_operation(operation_factory),
            name='com_port_reader_operation',
        )
        self._operation_task.add_done_callback(self._operation_done)

    async def _run_operation(self, operation_factory: Callable[[], Awaitable[None]]) -> None:
        """Направляет любое исключение операции в единый обработчик."""
        try:
            await operation_factory()
        except asyncio.CancelledError:
            raise
        except ComPortReaderException as err:
            if err.fatal_error:
                self._mark_session_failed()
            if self._background_error is err:
                self._background_error = None
            self._report_error(err)
        except Exception as err:
            self._logger.exception('Неожиданная ошибка командной операции')
            self._mark_session_failed()
            self._report_error(
                ComPortReaderException(f'Неожиданная ошибка операции: {err}')
            )

    def _operation_done(self, task: asyncio.Task[None]) -> None:
        """Забирает результат принадлежащей объекту командной задачи."""
        if self._operation_task is task:
            self._operation_task = None
        if task.cancelled():
            return
        task.exception()

    # =============================================================
    # ==================== Выполнение команды =====================
    # =============================================================

    async def _execute_command(
            self,
            command: CommandName,
            params: Optional[dict[str, object]] = None) -> None:
        """Отправка команды и проверка её терминального результата."""
        self._raise_background_error()
        if command is CommandName.HANDSHAKE_INIT:
            self._ensure_transport_running()
        else:
            self._ensure_session_running()

        if self._pending_result is not None:
            raise CommandAlreadyPending()

        transport = self._transport
        if transport is None:
            raise SessionNotRunning('Транспорт дочерней сессии не создан')

        expected_event = self._command_result_events.get(command)
        if expected_event is None:
            raise SessionProtocolError(
                f'Для команды {command.name} не определён терминальный результат'
            )

        future: asyncio.Future[SessionEvent] = asyncio.get_running_loop().create_future()

        self._pending_result = future
        self._expected_result_event = expected_event

        try:
            await transport.send_command_request(
                CommandRequest(command=command, params=params or {})
            )
            session_event = await asyncio.wait_for(
                future,
                timeout=_DEFAULT_COMMAND_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as err:
            raise CommandResultTimeout(
                f'Истёк таймаут ожидания результата команды {command.name}'
            ) from err
        finally:
            if self._pending_result is future:
                self._pending_result = None
                self._expected_result_event = None

        if session_event.params['success']:
            return

        error_info = session_event.params['error_info']
        if command is CommandName.SET_SAVING_FILE:
            saving_file = Path(str((params or {}).get('filepath', '')))
            raise SavingFilePreparationError(saving_file, error_info)
        raise CommandExecutionError(command, error_info)

    def _ensure_session_running(self) -> None:
        """Проверяет готовность сессии к предметной команде."""
        if not self._is_configured:
            raise NeedConfiguration(
                'Перед началом операции задайте параметры подключения'
            )
        self._ensure_transport_running()

    def _ensure_transport_running(self) -> None:
        """Проверяет активность транспорта."""
        if not self.is_active:
            raise SessionNotRunning('Дочерняя сессия с МК не запущена')

    def _raise_background_error(self) -> None:
        """Возбуждает ранее полученную фоновую ошибку внутри операции."""
        if self._background_error is not None:
            raise self._background_error

    # =============================================================
    # ===================== Обработка событий =====================
    # =============================================================

    def _data_handler(self, package: TelegaData) -> None:
        """Передаёт пакет GUI без раскрытия межпроцессного протокола."""
        self._callbacks.on_data(package)

    def _session_event_handler(self, session_event: SessionEvent) -> None:
        """Маршрутизирует внутреннее событие дочерней сессии."""
        self._logger.debug(f'Получено событие сессии: {session_event.event.name}')

        if session_event.event in self._result_event_names:
            self._command_result_handler(session_event)
            return
        if session_event.event is SessionEventName.STATIC_INIT_COMPLETED:
            self._callbacks.on_static_init_completed()
            return
        if session_event.event is SessionEventName.SESSION_ERROR:
            self._session_error_handler(session_event)
            return
        if session_event.event is SessionEventName.SESSION_STOPPED:
            self._is_configured = False
            if not self._cleanup_lock.locked():
                self._handle_background_failure(
                    SessionNotRunning('Дочерняя сессия завершила работу')
                )
            return

        self._handle_background_failure(
            SessionProtocolError(
                f'Получено неизвестное событие сессии: {session_event.event}'
            )
        )

    def _command_result_handler(self, session_event: SessionEvent) -> None:
        """Проверяет результат команды и завершает ожидающий ``Future``."""
        future = self._pending_result
        expected_event = self._expected_result_event
        if future is None or expected_event is None:
            self._handle_background_failure(
                SessionProtocolError(
                    f'Получен неожидаемый результат команды {session_event.event.name}'
                )
            )
            return
        if session_event.event is not expected_event:
            self._handle_background_failure(
                SessionProtocolError(
                    f'Ожидалось {expected_event.name}, '
                    f'получено {session_event.event.name}'
                )
            )
            return

        try:
            self._validate_command_result(session_event)
        except SessionProtocolError as err:
            self._handle_background_failure(err)
            return

        if future.done():
            self._handle_background_failure(
                SessionProtocolError(
                    f'Результат {session_event.event.name} получен повторно'
                )
            )
            return
        future.set_result(session_event)

    @staticmethod
    def _validate_command_result(session_event: SessionEvent) -> None:
        """Проверяет обязательные параметры результата команды."""
        success = session_event.params.get('success')
        error_info = session_event.params.get('error_info')
        if not isinstance(success, bool) or not isinstance(error_info, str):
            raise SessionProtocolError(
                f'Результат {session_event.event.name} имеет некорректные параметры'
            )

        if session_event.event is SessionEventName.SET_SAVING_FILE_RESULT:
            filepath = session_event.params.get('filepath')
            if not isinstance(filepath, str):
                raise SessionProtocolError(
                    'Результат подготовки CSV не содержит строковый путь'
                )

    def _session_error_handler(self, session_event: SessionEvent) -> None:
        """Преобразует SESSION_ERROR в предметное исключение."""
        error_code = session_event.params.get('error_code')
        error_info = session_event.params.get('error_info')
        if not isinstance(error_code, str) or not isinstance(error_info, str):
            self._handle_background_failure(
                SessionProtocolError(
                    'Ошибка дочерней сессии имеет некорректные параметры'
                )
            )
            return

        message = error_code if not error_info else f'{error_code}: {error_info}'
        self._handle_background_failure(SessionReportedError(message))

    def _transport_error_handler(self, error: ComPortReaderException) -> None:
        """Получает фоновую ошибку транспорта без выброса из reader-задачи."""
        self._handle_background_failure(error)

    def _handle_background_failure(self, error: ComPortReaderException) -> None:
        """Помечает сессию неготовой и доставляет ошибку ровно один раз."""
        if self._background_error is not None:
            return

        self._logger.error(str(error))
        self._mark_session_failed()
        self._background_error = error

        future = self._pending_result
        operation = self._operation_task
        if future is not None and not future.done():
            future.set_exception(error)
            return
        if operation is not None and not operation.done():
            return

        self._background_error = None
        self._report_error(error)

    def _mark_session_failed(self) -> None:
        """Помечает текущую сессию непригодной для новых команд."""
        self._is_configured = False

    def _report_error(self, error: ComPortReaderException) -> None:
        """Безопасно передаёт предметную ошибку GUI."""
        try:
            self._callbacks.on_error(error)
        except Exception:
            self._logger.exception('Обработчик ошибки ComPortReader завершился аварийно')

    # =============================================================
    # ======================== Валидация ==========================
    # =============================================================

    @staticmethod
    def _validate_session_config(
            session_config: object) -> Optional[InvalidSessionConfig]:
        """Проверяет локальные параметры новой сессии."""
        if not isinstance(session_config, ComPortSessionConfig):
            return InvalidSessionConfig(
                'Ожидается ComPortSessionConfig для настройки сессии'
            )
        if not isinstance(session_config.logger_config, LoggerConfig):
            return InvalidSessionConfig(
                'Конфигурация логирования должна быть LoggerConfig'
            )
        if (
                not isinstance(session_config.com_port_name, str)
                or not session_config.com_port_name.strip()
        ):
            return InvalidSessionConfig('Не задан COM-порт для подключения к МК')
        if not isinstance(session_config.raw_stream_file, Path):
            return InvalidSessionConfig('Путь файла сырого потока должен быть Path')
        if not session_config.raw_stream_file.is_absolute():
            return InvalidSessionConfig(
                'Путь файла сырого потока должен быть абсолютным'
            )
        return None

    @staticmethod
    def _validate_saving_file(saving_file: object) -> Optional[InvalidSavingFile]:
        """Проверяет локальный путь результата отдельной операции."""
        if not isinstance(saving_file, Path):
            return InvalidSavingFile('Путь CSV-файла должен быть Path')
        if not saving_file.is_absolute():
            return InvalidSavingFile('Путь CSV-файла должен быть абсолютным')
        return None

    # =============================================================
    # ======================== Завершение =========================
    # =============================================================

    async def _cleanup(self, close_reader: bool) -> None:
        """Освобождает и удаляет одноразовый транспорт текущей сессии."""
        async with self._cleanup_lock:
            if self._is_closed:
                if close_reader:
                    return
                raise ComPortReaderException(
                    'Нельзя сбросить окончательно закрытый ComPortReader'
                )

            self._logger.debug('Освобождение ресурсов ComPortReader')
            self._is_configured = False

            operation_task = self._operation_task
            if operation_task is not None and operation_task is not asyncio.current_task():
                await _cancel_task(operation_task)
            if self._operation_task is operation_task:
                self._operation_task = None

            future = self._pending_result
            if future is not None and not future.done():
                future.cancel()
            self._pending_result = None
            self._expected_result_event = None

            transport = self._transport
            try:
                if transport is not None:
                    await transport.shutdown()
                if self._transport is transport:
                    self._transport = None
                self._is_closed = close_reader
            finally:
                self._background_error = None

            self._logger.debug('Ресурсы ComPortReader освобождены')
