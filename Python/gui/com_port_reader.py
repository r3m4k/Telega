# -*- coding: utf-8 -*-
"""Асинхронный доступ GUI к отдельному процессу сессии МК.

Модуль не зависит от Qt. :class:`ComPortReader` предоставляет awaitable API,
последовательно отправляет команды и ожидает их терминальные
:class:`SessionEvent`. :class:`_SessionProcessTransport` владеет дочерним
процессом и IPC-очередями, но не интерпретирует пользовательский сценарий.
"""

# System imports
import asyncio
import logging
from multiprocessing import get_context
from multiprocessing.context import BaseContext, Process
from multiprocessing.queues import Queue
from pathlib import Path
from queue import Empty
from typing import Any, Optional

# External imports
from pydantic import ValidationError

# User imports
from async_mc_controller.config import ComPortConfig, LoggerConfig
from telega_session import (
    CommandName,
    CommandRequest,
    SessionEvent,
    SessionEventName,
    start_telega_session,
)
from telega_session import TelegaData as PackageType

##########################################################


_QUEUE_READ_TIMEOUT_SECONDS = 0.1
_DEFAULT_COMMAND_TIMEOUT_SECONDS = 5.0
_DEFAULT_PROCESS_TIMEOUT_MS = 3000
_DEFAULT_READER_TIMEOUT_MS = 1000


# =============================================================
# ======================== Исключения ==========================
# =============================================================


class ComPortReaderException(RuntimeError):
    """Базовое исключение модуля взаимодействия с сессией МК."""


class SessionNotRunning(ComPortReaderException):
    """Дочерняя сессия с МК не выполняется."""


class NeedConfiguration(ComPortReaderException):
    """Параметры подключения к МК не заданы."""


class CommandAlreadyPending(ComPortReaderException):
    """Предыдущая команда ещё не получила терминальный результат."""


class CommandResultTimeout(ComPortReaderException):
    """Истёк таймаут ожидания терминального результата команды."""


class SessionProtocolError(ComPortReaderException):
    """Нарушен межпроцессный протокол команд или событий сессии."""


class SessionDesynchronized(ComPortReaderException):
    """Сессия рассинхронизирована и не допускает отправку новых команд."""


class SessionReportedError(ComPortReaderException):
    """Дочерняя сессия сообщила о фатальной ошибке."""


# =============================================================
# ====================== Вспомогательный IPC ===================
# =============================================================


def _get_queue_item(source_queue: Queue) -> tuple[bool, object]:
    """Блокирующе получает один элемент очереди ограниченное время.

    Args:
        source_queue: Межпроцессная очередь для чтения.

    Returns:
        Пара ``(получен ли элемент, значение)``. При таймауте возвращается
        ``(False, None)``.
    """
    try:
        return True, source_queue.get(timeout=_QUEUE_READ_TIMEOUT_SECONDS)
    except Empty:
        return False, None


# =============================================================
# ================= Транспорт дочерней сессии ==================
# =============================================================


class _SessionProcessTransport:
    """Управляет дочерним процессом и IPC-очередями без зависимости от Qt.

    Args:
        logger: Логгер родительского процесса.
    """

    def __init__(self, logger: logging.Logger):
        self._logger: logging.Logger = logger
        self._mp_context: BaseContext = get_context('spawn')
        self._mc_session_process: Optional[Process] = None
        self._command_queue: Optional[Queue] = None
        self._response_queue: Optional[Queue] = None
        self._data_queue: Optional[Queue] = None

    @property
    def is_active(self) -> bool:
        """Возвращает ``True``, когда дочерний процесс выполняется."""
        process = self._mc_session_process
        if process is None:
            return False

        try:
            return process.is_alive()
        except ValueError:
            return False

    @property
    def has_resources(self) -> bool:
        """Возвращает наличие принадлежащих транспорту ресурсов."""
        return any((
            self._mc_session_process is not None,
            self._command_queue is not None,
            self._response_queue is not None,
            self._data_queue is not None,
        ))

    # =============================================================
    # ======================== Публичный API ======================
    # =============================================================

    def start(self,
              logger_config: LoggerConfig,
              com_port_config: ComPortConfig,
              bin_file: Path) -> None:
        """Создаёт IPC-очереди и запускает дочернюю сессию.

        Args:
            logger_config: Конфигурация логирования дочернего процесса.
            com_port_config: Конфигурация COM-порта.
            bin_file: Файл исходного байтового потока.

        Raises:
            ComPortReaderException: Сессия активна или старые ресурсы не
                освобождены.
        """
        if self.is_active:
            raise ComPortReaderException('Сессия взаимодействия с МК уже запущена!')
        if self.has_resources:
            raise ComPortReaderException(
                'Перед запуском новой сессии необходимо освободить старые IPC-ресурсы!'
            )

        self._command_queue = self._mp_context.Queue()
        self._response_queue = self._mp_context.Queue()
        self._data_queue = self._mp_context.Queue()
        self._mc_session_process = self._mp_context.Process(
            target=start_telega_session,
            args=(
                logger_config,
                com_port_config,
                bin_file,
                self._command_queue,
                self._response_queue,
                self._data_queue,
            ),
            daemon=True,
        )

        self._logger.debug('Запуск дочернего процесса сессии тележки')
        self._mc_session_process.start()

    async def send_command(self, command_request: CommandRequest) -> None:
        """Асинхронно помещает команду в `command_queue`.

        Args:
            command_request: Команда для `ControllerTelega`.

        Raises:
            SessionNotRunning: Дочерний процесс не выполняется.
            ComPortReaderException: Не удалось записать команду в очередь.
        """
        command_queue = self._command_queue
        if not self.is_active or command_queue is None:
            raise SessionNotRunning('Для отправки команды сначала запустите процесс!')

        self._logger.debug(f'Отправка команды {command_request.command}')
        try:
            await asyncio.to_thread(
                command_queue.put,
                command_request.model_dump(),
            )
        except (OSError, ValueError) as err:
            raise ComPortReaderException(
                f'Не удалось отправить команду {command_request.command}: {err}'
            ) from err

    async def receive_session_event(self) -> Optional[SessionEvent]:
        """Получает и валидирует очередное событие из `response_queue`.

        Returns:
            Событие сессии либо ``None``, если за интервал опроса данных нет.

        Raises:
            SessionNotRunning: Очередь событий не создана.
            SessionProtocolError: Получены некорректные данные.
            ComPortReaderException: Ошибка чтения IPC-очереди.
        """
        response_queue = self._response_queue
        if response_queue is None:
            raise SessionNotRunning('Очередь response_queue не создана!')

        event_data = await self._receive_queue_item(response_queue, 'response_queue')
        if event_data is None:
            return None

        try:
            return SessionEvent.model_validate(event_data)
        except ValidationError as err:
            raise SessionProtocolError(
                f'Получено некорректное событие из response_queue: {err}'
            ) from err

    async def receive_data(self) -> Optional[PackageType]:
        """Получает и проверяет очередной пакет из `data_queue`.

        Returns:
            Пакет измерений либо ``None``, если за интервал опроса данных нет.

        Raises:
            SessionNotRunning: Очередь данных не создана.
            SessionProtocolError: Получен объект неправильного типа.
            ComPortReaderException: Ошибка чтения IPC-очереди.
        """
        data_queue = self._data_queue
        if data_queue is None:
            raise SessionNotRunning('Очередь data_queue не создана!')

        package_data = await self._receive_queue_item(data_queue, 'data_queue')
        if package_data is None:
            return None
        if not isinstance(package_data, PackageType):
            raise SessionProtocolError(
                'Получен некорректный пакет из data_queue: '
                f'ожидается {PackageType.__name__}, '
                f'получен {type(package_data).__name__}'
            )

        return package_data

    async def request_session_stop(self) -> None:
        """Отправляет специальную команду штатной остановки сессии."""
        if not self.is_active:
            return

        try:
            await self.send_command(CommandRequest(command=CommandName.STOP_RUNNING))
        except ComPortReaderException as err:
            self._logger.warning(f'Не удалось отправить команду остановки сессии МК: {err}')

    async def wait_session_process(
            self,
            timeout_ms: int = _DEFAULT_PROCESS_TIMEOUT_MS) -> None:
        """Ожидает процесс и при необходимости завершает его принудительно.

        Args:
            timeout_ms: Время ожидания штатного завершения процесса.

        Raises:
            ComPortReaderException: Процесс не удалось завершить.
        """
        await asyncio.to_thread(self._wait_session_process, timeout_ms)
        if self.is_active:
            raise ComPortReaderException('Не удалось завершить дочерний процесс сессии МК!')

    async def close_resources(self) -> None:
        """Закрывает IPC-очереди и дескриптор завершённого процесса.

        Raises:
            ComPortReaderException: Дочерний процесс ещё выполняется либо его
                дескриптор не удалось закрыть.
        """
        if self.is_active:
            raise ComPortReaderException(
                'Нельзя освобождать IPC-ресурсы работающей дочерней сессии!'
            )

        await asyncio.to_thread(self._close_ipc_queues)
        self._close_session_process()

    # =============================================================
    # ======================= Работа с IPC ========================
    # =============================================================

    async def _receive_queue_item(
            self,
            source_queue: Queue,
            queue_name: str) -> Optional[object]:
        """Асинхронно получает один необработанный элемент IPC-очереди."""
        try:
            has_item, item = await asyncio.to_thread(
                _get_queue_item,
                source_queue,
            )
        except (EOFError, OSError, ValueError) as err:
            raise ComPortReaderException(
                f'Ошибка чтения очереди {queue_name}: {err}'
            ) from err

        return item if has_item else None

    # =============================================================
    # ===================== Завершение ресурсов ===================
    # =============================================================

    def _wait_session_process(self, timeout_ms: int) -> None:
        """Блокирующе ожидает и при необходимости завершает процесс."""
        process = self._mc_session_process
        if process is None or process.pid is None:
            return

        if self.is_active:
            self._logger.debug('Ожидание завершения дочернего процесса сессии МК')
            process.join(timeout_ms / 1000)

        if self.is_active:
            self._logger.warning(
                'Дочерний процесс сессии МК не завершился штатно, выполняется terminate()'
            )
            process.terminate()
            process.join(1)

        if self.is_active and hasattr(process, 'kill'):
            self._logger.warning(
                'Дочерний процесс сессии МК не завершился после terminate(), выполняется kill()'
            )
            process.kill()
            process.join(1)

        if self.is_active:
            self._logger.error('Не удалось завершить дочерний процесс сессии МК')
        else:
            self._logger.debug(
                f'Дочерний процесс сессии МК завершён с кодом {process.exitcode}'
            )

    def _close_ipc_queues(self) -> None:
        """Блокирующе закрывает все IPC-очереди."""
        queue_attributes = (
            ('_command_queue', 'command_queue'),
            ('_response_queue', 'response_queue'),
            ('_data_queue', 'data_queue'),
        )
        for attribute_name, queue_name in queue_attributes:
            source_queue = getattr(self, attribute_name)
            if source_queue is None:
                continue

            try:
                source_queue.close()
                source_queue.join_thread()
                self._logger.debug(f'Очередь {queue_name} закрыта')
            except (OSError, ValueError) as err:
                self._logger.debug(
                    f'Очередь {queue_name} уже закрыта или недоступна: {err}'
                )
            finally:
                setattr(self, attribute_name, None)

    def _close_session_process(self) -> None:
        """Закрывает дескриптор завершённого дочернего процесса."""
        process = self._mc_session_process
        if process is None:
            return
        if self.is_active:
            raise ComPortReaderException('Нельзя закрыть дескриптор работающего процесса!')

        try:
            process.close()
        except ValueError as err:
            raise ComPortReaderException(
                f'Не удалось закрыть дескриптор дочернего процесса: {err}'
            ) from err

        self._mc_session_process = None


# =============================================================
# ===================== Асинхронный фасад ======================
# =============================================================


class ComPortReader:
    """Предоставляет Qt-free asyncio API для взаимодействия с сессией МК.

    Одновременно допускается ровно одна команда, ожидающая терминальный
    результат. Публичные command-методы возвращают валидированный
    :class:`SessionEvent`. Самостоятельные события, пакеты данных и ошибки
    доступны через отдельные awaitable-методы.

    Args:
        logger: Логгер родительского приложения.
        command_timeout_seconds: Таймаут ожидания терминального результата.

    Raises:
        ValueError: Таймаут команды не является положительным числом.
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
            command_timeout_seconds: float = _DEFAULT_COMMAND_TIMEOUT_SECONDS):
        if (
                not isinstance(command_timeout_seconds, (int, float))
                or isinstance(command_timeout_seconds, bool)
        ):
            raise TypeError(
                'Ожидается command_timeout_seconds: int или float, '
                f'получен {type(command_timeout_seconds)}'
            )
        if command_timeout_seconds <= 0:
            raise ValueError('Таймаут результата команды должен быть больше нуля')

        self._logger: logging.Logger = logger
        self._command_timeout_seconds: float = command_timeout_seconds
        self._transport: _SessionProcessTransport = _SessionProcessTransport(logger)

        self._is_configured: bool = False
        self._is_synchronized: bool = True
        self._is_shutting_down: bool = False
        self._session_stopped_received: bool = False

        self._pending_result: Optional[asyncio.Future[SessionEvent]] = None
        self._expected_result_event: Optional[SessionEventName] = None

        self._response_reader_task: Optional[asyncio.Task[None]] = None
        self._data_reader_task: Optional[asyncio.Task[None]] = None
        self._background_shutdown_task: Optional[asyncio.Task[None]] = None
        self._shutdown_lock: asyncio.Lock = asyncio.Lock()

        self._session_events: asyncio.Queue[SessionEvent] = asyncio.Queue()
        self._received_data: asyncio.Queue[PackageType] = asyncio.Queue(maxsize=1)
        self._errors: asyncio.Queue[ComPortReaderException] = asyncio.Queue()

    @property
    def is_active(self) -> bool:
        """Возвращает ``True``, когда дочерняя сессия активна."""
        return self._transport.is_active

    @property
    def is_configured(self) -> bool:
        """Возвращает наличие действующей конфигурации сессии."""
        return self._is_configured

    # =============================================================
    # ======================== Публичный API ======================
    # =============================================================

    async def configure(self,
                        logger_config: LoggerConfig,
                        com_port_name: str,
                        bin_file: Path) -> SessionEvent:
        """Запускает дочернюю сессию и ожидает результат handshake.

        Args:
            logger_config: Конфигурация логирования дочернего процесса.
            com_port_name: Имя COM-порта.
            bin_file: Файл исходного байтового потока.

        Returns:
            `HANDSHAKE_INIT_RESULT` с параметрами результата.

        Raises:
            ComPortReaderException: Сессия уже запущена или запуск не удался.
            NeedConfiguration: Имя COM-порта не задано.
            TypeError: `bin_file` не является :class:`Path`.
        """
        await self._wait_background_shutdown()
        if self.is_active:
            raise ComPortReaderException(
                'Нельзя изменить параметры при запущенной сессии взаимодействия с МК!'
            )
        if not com_port_name:
            raise NeedConfiguration('Не задан COM-порт для подключения к МК!')
        if not isinstance(bin_file, Path):
            raise TypeError(f'Ожидается bin_file: Path, получен {type(bin_file)}')

        if self._transport.has_resources:
            await self.shutdown()

        self._clear_received_items()
        self._is_synchronized = True
        self._session_stopped_received = False
        com_port_config = ComPortConfig(name=com_port_name, baudrate=115200)
        self._logger.debug(
            f'Конфигурирование ComPortReader: port={com_port_name}, bin_file={bin_file}'
        )

        try:
            self._transport.start(logger_config, com_port_config, bin_file)
            self._is_configured = True
            self._start_reader_tasks()
            return await self._execute_command(CommandName.HANDSHAKE_INIT)
        except asyncio.CancelledError:
            self._is_synchronized = False
            self._schedule_shutdown()
            raise
        except Exception:
            self._logger.exception(
                'Ошибка конфигурирования ComPortReader, выполняется очистка ресурсов'
            )
            await self._shutdown_after_configuration_error()
            raise

    async def set_saving_file(self, file_path: Path) -> SessionEvent:
        """Устанавливает CSV-файл и ожидает результат его подготовки.

        Args:
            file_path: Абсолютный путь к CSV-файлу.

        Returns:
            `SET_SAVING_FILE_RESULT`.

        Raises:
            TypeError: `file_path` не является :class:`Path`.
            ValueError: Путь не абсолютный.
            ComPortReaderException: Команду невозможно выполнить.
        """
        if not isinstance(file_path, Path):
            raise TypeError(f'Ожидается file_path: Path, получен {type(file_path)}')
        if not file_path.is_absolute():
            raise ValueError('Путь к CSV-файлу должен быть абсолютным')

        return await self._execute_command(
            CommandName.SET_SAVING_FILE,
            params={'filepath': str(file_path)},
        )

    async def start_static_init(self) -> SessionEvent:
        """Запускает статический набор и ожидает подтверждение переключения МК."""
        return await self._execute_command(CommandName.START_STATIC_INIT)

    async def start_measuring(self) -> SessionEvent:
        """Запускает измерения и ожидает подтверждение переключения МК."""
        return await self._execute_command(CommandName.START_MEASURING)

    async def stop_measuring(self) -> SessionEvent:
        """Останавливает измерения и ожидает терминальный результат команды."""
        return await self._execute_command(CommandName.STOP_MEASURING)

    async def stop_running(self) -> None:
        """Отправляет специальную команду завершения без командного `Future`."""
        self._ensure_session_running()
        if self._pending_result is not None:
            raise CommandAlreadyPending(
                'Нельзя отдельно отправить STOP_RUNNING во время ожидания другой команды'
            )
        await self._transport.request_session_stop()

    async def receive_session_event(self) -> SessionEvent:
        """Ожидает самостоятельное событие сессии."""
        return await self._session_events.get()

    async def receive_data(self) -> PackageType:
        """Ожидает последний доступный пакет измерительных данных."""
        return await self._received_data.get()

    async def receive_error(self) -> ComPortReaderException:
        """Ожидает транспортную или протокольную ошибку фонового чтения."""
        return await self._errors.get()

    async def shutdown(
            self,
            process_timeout_ms: int = _DEFAULT_PROCESS_TIMEOUT_MS,
            reader_timeout_ms: int = _DEFAULT_READER_TIMEOUT_MS) -> None:
        """Асинхронно завершает процесс, readers и IPC-ресурсы.

        Args:
            process_timeout_ms: Время ожидания штатного завершения процесса.
            reader_timeout_ms: Время ожидания естественной остановки readers.

        Raises:
            ComPortReaderException: Ресурсы не удалось полностью освободить.
        """
        async with self._shutdown_lock:
            if not self._transport.has_resources:
                self._reset_session_state()
                return

            self._logger.debug('Завершение работы ComPortReader')
            self._is_shutting_down = True
            self._is_configured = False
            self._fail_pending_result(
                SessionNotRunning('Сессия завершается до получения результата команды')
            )

            try:
                await self._transport.request_session_stop()
                await self._transport.wait_session_process(process_timeout_ms)
                await self._wait_reader_tasks(reader_timeout_ms)
                await self._transport.close_resources()
            finally:
                self._response_reader_task = None
                self._data_reader_task = None
                self._reset_session_state()

            self._logger.debug('Завершение работы ComPortReader выполнено')

    async def close(self) -> None:
        """Асинхронно закрывает `ComPortReader`."""
        await self.shutdown()

    # =============================================================
    # ======================= Внутренняя логика ===================
    # =============================================================

    async def _execute_command(
            self,
            command: CommandName,
            params: Optional[dict[str, object]] = None) -> SessionEvent:
        """Отправляет одну команду и ожидает соответствующий результат."""
        self._ensure_session_running()
        if self._pending_result is not None:
            raise CommandAlreadyPending(
                'Предыдущая команда ещё не получила терминальный результат'
            )

        expected_event = self._command_result_events.get(command)
        if expected_event is None:
            raise SessionProtocolError(
                f'Для команды {command} не определён терминальный результат'
            )

        future: asyncio.Future[SessionEvent] = (
            asyncio.get_running_loop().create_future()
        )
        self._pending_result = future
        self._expected_result_event = expected_event

        try:
            await self._transport.send_command(
                CommandRequest(command=command, params=params or {})
            )
            return await asyncio.wait_for(
                future,
                timeout=self._command_timeout_seconds,
            )
        except asyncio.TimeoutError as err:
            self._is_synchronized = False
            self._schedule_shutdown()
            raise CommandResultTimeout(
                f'Истёк таймаут ожидания события {expected_event}'
            ) from err
        except asyncio.CancelledError:
            self._is_synchronized = False
            self._schedule_shutdown()
            raise
        except ComPortReaderException:
            self._is_synchronized = False
            self._schedule_shutdown()
            raise
        finally:
            if self._pending_result is future:
                self._pending_result = None
                self._expected_result_event = None

    def _ensure_session_running(self) -> None:
        """Проверяет конфигурацию, синхронизацию и активность сессии."""
        if not self._is_configured:
            raise NeedConfiguration('Перед началом работы задайте параметры подключения!')
        if not self._is_synchronized:
            raise SessionDesynchronized(
                'Сессия рассинхронизирована и должна быть перезапущена'
            )
        if not self.is_active:
            raise SessionNotRunning('Сессия взаимодействия с МК не запущена!')

    def _start_reader_tasks(self) -> None:
        """Запускает async-задачи чтения очередей событий и данных."""
        if self._response_reader_task is not None or self._data_reader_task is not None:
            raise ComPortReaderException('Задачи чтения IPC-очередей уже созданы')

        self._response_reader_task = asyncio.create_task(
            self._reading_response_queue(),
            name='telega_response_queue_reader',
        )
        self._data_reader_task = asyncio.create_task(
            self._reading_data_queue(),
            name='telega_data_queue_reader',
        )

    async def _reading_response_queue(self) -> None:
        """Читает `response_queue` и маршрутизирует события сессии."""
        self._logger.debug('Запуск async-чтения response_queue')
        try:
            while True:
                session_event = await self._transport.receive_session_event()
                if session_event is None:
                    if not self.is_active:
                        if not self._is_shutting_down and not self._session_stopped_received:
                            self._handle_background_failure(
                                SessionNotRunning(
                                    'Дочерняя сессия завершилась без SESSION_STOPPED'
                                )
                            )
                        return
                    continue

                self._session_event_handler(session_event)
        except asyncio.CancelledError:
            self._logger.debug('Задача чтения response_queue отменена')
            raise
        except ComPortReaderException as err:
            self._handle_background_failure(err)
        except Exception as err:
            self._logger.exception(f'Неожиданная ошибка чтения response_queue: {err}')
            self._handle_background_failure(
                ComPortReaderException(f'Неожиданная ошибка response_queue: {err}')
            )
        finally:
            self._logger.debug('Остановка async-чтения response_queue')

    async def _reading_data_queue(self) -> None:
        """Читает `data_queue` и сохраняет только последний пакет для GUI."""
        self._logger.debug('Запуск async-чтения data_queue')
        try:
            while True:
                package = await self._transport.receive_data()
                if package is None:
                    if not self.is_active:
                        return
                    continue

                if self._received_data.full():
                    self._received_data.get_nowait()
                self._received_data.put_nowait(package)
        except asyncio.CancelledError:
            self._logger.debug('Задача чтения data_queue отменена')
            raise
        except ComPortReaderException as err:
            self._handle_background_failure(err)
        except Exception as err:
            self._logger.exception(f'Неожиданная ошибка чтения data_queue: {err}')
            self._handle_background_failure(
                ComPortReaderException(f'Неожиданная ошибка data_queue: {err}')
            )
        finally:
            self._logger.debug('Остановка async-чтения data_queue')

    # =============================================================
    # ===================== Обработка событий =====================
    # =============================================================

    def _session_event_handler(self, session_event: SessionEvent) -> None:
        """Маршрутизирует результат команды или самостоятельное событие."""
        self._logger.debug(f'Получено событие сессии: {session_event.event}')

        if session_event.event in self._result_event_names:
            self._command_result_handler(session_event)
            return

        if session_event.event is SessionEventName.SESSION_ERROR:
            self._session_error_handler(session_event)
            return

        if session_event.event is SessionEventName.SESSION_STOPPED:
            self._session_stopped_received = True
            self._session_events.put_nowait(session_event)
            self._schedule_shutdown()
            return

        if session_event.event is SessionEventName.STATIC_INIT_COMPLETED:
            self._session_events.put_nowait(session_event)
            return

        self._handle_protocol_error(
            SessionProtocolError(
                f'Получено неизвестное событие сессии: {session_event.event}'
            )
        )

    def _command_result_handler(self, session_event: SessionEvent) -> None:
        """Проверяет и завершает ожидающий командный `Future`."""
        future = self._pending_result
        expected_event = self._expected_result_event
        if future is None or expected_event is None:
            self._handle_protocol_error(
                SessionProtocolError(
                    f'Получен неожидаемый результат команды {session_event.event}'
                )
            )
            return
        if session_event.event is not expected_event:
            error = SessionProtocolError(
                f'Ожидалось событие {expected_event}, получено {session_event.event}'
            )
            if not future.done():
                future.set_exception(error)
            self._handle_protocol_error(error)
            return

        try:
            self._validate_command_result(session_event)
        except SessionProtocolError as err:
            if not future.done():
                future.set_exception(err)
            self._handle_protocol_error(err)
            return

        if future.done():
            self._handle_protocol_error(
                SessionProtocolError(
                    f'Результат {session_event.event} получен повторно'
                )
            )
            return

        future.set_result(session_event)

    def _validate_command_result(self, session_event: SessionEvent) -> None:
        """Проверяет общие обязательные параметры результата команды."""
        success = session_event.params.get('success')
        error_info = session_event.params.get('error_info')
        if not isinstance(success, bool) or not isinstance(error_info, str):
            raise SessionProtocolError(
                f'Событие {session_event.event} не содержит корректные '
                'параметры success и error_info'
            )

        if session_event.event is SessionEventName.SET_SAVING_FILE_RESULT:
            filepath = session_event.params.get('filepath')
            if not isinstance(filepath, str):
                raise SessionProtocolError(
                    'SET_SAVING_FILE_RESULT не содержит строковый filepath'
                )

    def _session_error_handler(self, session_event: SessionEvent) -> None:
        """Обрабатывает фатальную ошибку, сообщённую дочерней сессией."""
        error_code = session_event.params.get('error_code')
        error_info = session_event.params.get('error_info')
        if not isinstance(error_code, str) or not isinstance(error_info, str):
            self._handle_protocol_error(
                SessionProtocolError(
                    'SESSION_ERROR не содержит строковые error_code и error_info'
                )
            )
            return

        message = error_code if not error_info else f'{error_code}: {error_info}'
        error = SessionReportedError(message)
        self._session_events.put_nowait(session_event)
        self._handle_background_failure(error)

    def _handle_protocol_error(self, error: SessionProtocolError) -> None:
        """Помечает сессию рассинхронизированной и запускает её остановку."""
        self._handle_background_failure(error)

    def _handle_background_failure(self, error: ComPortReaderException) -> None:
        """Завершает pending-команду и запускает аварийную остановку сессии."""
        self._logger.error(str(error))
        self._is_synchronized = False
        self._fail_pending_result(error)
        self._report_background_error(error)
        self._schedule_shutdown()

    def _fail_pending_result(self, error: ComPortReaderException) -> None:
        """Завершает ожидающий `Future` исключением, если он ещё активен."""
        future = self._pending_result
        if future is not None and not future.done():
            future.set_exception(error)

    def _report_background_error(self, error: ComPortReaderException) -> None:
        """Публикует фоновую ошибку для будущего GUI-потребителя."""
        self._errors.put_nowait(error)

    # =============================================================
    # ======================== Завершение =========================
    # =============================================================

    def _schedule_shutdown(self) -> None:
        """Создаёт одну контролируемую задачу аварийного завершения."""
        if not self._transport.has_resources:
            return
        if (
                self._background_shutdown_task is not None
                and not self._background_shutdown_task.done()
        ):
            return

        task = asyncio.create_task(
            self.shutdown(),
            name='telega_session_shutdown',
        )
        self._background_shutdown_task = task
        task.add_done_callback(self._background_shutdown_done)

    def _background_shutdown_done(self, task: asyncio.Task[None]) -> None:
        """Получает результат фонового завершения и журналирует его ошибку."""
        if self._background_shutdown_task is task:
            self._background_shutdown_task = None
        if task.cancelled():
            return

        error = task.exception()
        if error is not None:
            self._logger.error(
                f'Ошибка фонового завершения ComPortReader: {error}',
                exc_info=(type(error), error, error.__traceback__),
            )
            reported_error = (
                error
                if isinstance(error, ComPortReaderException)
                else ComPortReaderException(str(error))
            )
            self._report_background_error(reported_error)

    async def _wait_background_shutdown(self) -> None:
        """Дожидается ранее запущенного аварийного завершения."""
        task = self._background_shutdown_task
        if task is None or task.done():
            return
        await asyncio.shield(task)

    async def _wait_reader_tasks(self, timeout_ms: int) -> None:
        """Ожидает естественную остановку readers и отменяет их по таймауту."""
        tasks = [
            task
            for task in (self._response_reader_task, self._data_reader_task)
            if task is not None
        ]
        if not tasks:
            return

        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout_ms / 1000,
            )
        except asyncio.TimeoutError as err:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise ComPortReaderException(
                'Задачи чтения IPC-очередей не остановились вовремя'
            ) from err

    async def _shutdown_after_configuration_error(self) -> None:
        """Освобождает частично созданные ресурсы после ошибки запуска."""
        try:
            await self.shutdown()
        except Exception as err:
            self._logger.exception(
                f'Не удалось очистить ресурсы после ошибки конфигурирования: {err}'
            )

    def _reset_session_state(self) -> None:
        """Сбрасывает состояние завершённой сессии для следующего запуска."""
        self._is_configured = False
        self._is_synchronized = True
        self._is_shutting_down = False
        self._session_stopped_received = False
        self._pending_result = None
        self._expected_result_event = None

    def _clear_received_items(self) -> None:
        """Удаляет события, данные и ошибки предыдущей сессии."""
        self._clear_async_queue(self._session_events)
        self._clear_async_queue(self._received_data)
        self._clear_async_queue(self._errors)

    @staticmethod
    def _clear_async_queue(source_queue: asyncio.Queue[Any]) -> None:
        """Удаляет все доступные элементы одной локальной async-очереди."""
        while True:
            try:
                source_queue.get_nowait()
            except asyncio.QueueEmpty:
                return
