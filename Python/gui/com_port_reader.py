# -*- coding: utf-8 -*-
"""Интеграция GUI с асинхронной сессией обмена с МК.

Модуль предоставляет :class:`ComPortReader` — Qt-фасад для главного окна.
Он запускает сессию работы с МК в отдельном процессе, передаёт ей команды и
доставляет в GUI декодированные пакеты и события сессии.

Ответственности разделены между тремя уровнями:

* :class:`ComPortReader` предоставляет API и Qt-сигналы GUI;
* :class:`_SessionProcessTransport` владеет процессом и IPC-ресурсами;
* :class:`_QueueReader` читает одну multiprocessing-очередь в Python-потоке.
"""

# System imports
import logging
from multiprocessing import get_context
from multiprocessing.context import BaseContext, Process
from multiprocessing.queues import Queue
from pathlib import Path
from queue import Empty
from threading import Event, Thread
from typing import Callable, Optional

# External imports
from PyQt5.QtCore import QObject, pyqtSignal
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


# =============================================================
# ======================== Исключения ==========================
# =============================================================


class ComPortReaderException(RuntimeError):
    """Базовое исключение модуля чтения данных с МК."""


class SessionNotRunning(ComPortReaderException):
    """Дочерняя сессия с МК не выполняется."""


class NeedConfiguration(ComPortReaderException):
    """Параметры подключения к МК не заданы."""


# =============================================================
# ===================== Чтение IPC-очереди =====================
# =============================================================


class _QueueReader:
    """Читает одну multiprocessing-очередь в выделенном Python-потоке.

    Класс не зависит от Qt. Владелец задаёт обработчики элементов и ошибок,
    поэтому потоковая логика отделена от доставки событий в GUI.

    Args:
        source_queue: Очередь, из которой нужно получать элементы.
        logger: Логгер транспорта.
        queue_name: Имя очереди в сообщениях журнала.
        is_process_active: Проверка активности дочернего процесса.
        item_handler: Обработчик очередного элемента.
        error_handler: Обработчик ошибки чтения или обработки элемента.
    """

    def __init__(self,
                 source_queue: Queue,
                 logger: logging.Logger,
                 queue_name: str,
                 is_process_active: Callable[[], bool],
                 item_handler: Callable[[object], None],
                 error_handler: Callable[[str], None]):
        self._source_queue: Queue = source_queue
        self._logger: logging.Logger = logger
        self._queue_name: str = queue_name
        self._is_process_active: Callable[[], bool] = is_process_active
        self._item_handler: Callable[[object], None] = item_handler
        self._error_handler: Callable[[str], None] = error_handler
        self._stop_event: Event = Event()

    def stop(self) -> None:
        """Запрашивает остановку цикла чтения очереди."""
        self._stop_event.set()

    def run(self) -> None:
        """Читает очередь до запроса остановки или завершения процесса."""
        self._logger.debug(f'Запуск чтения очереди {self._queue_name}')
        try:
            while not self._stop_event.is_set():
                try:
                    item = self._source_queue.get(timeout=0.1)
                except Empty:
                    if not self._is_process_active():
                        return
                    continue
                except (EOFError, OSError, ValueError) as err:
                    self._report_error(f'Ошибка чтения очереди {self._queue_name}: {err}')
                    return

                if self._stop_event.is_set():
                    return

                try:
                    self._item_handler(item)
                except Exception as err:
                    self._logger.exception(
                        f'Ошибка обработки элемента очереди {self._queue_name}: {err}'
                    )
                    self._report_error(
                        f'Ошибка обработки элемента очереди {self._queue_name}: {err}'
                    )
        finally:
            self._logger.debug(f'Остановка чтения очереди {self._queue_name}')

    def _report_error(self, message: str) -> None:
        """Передаёт ошибку владельцу, не прерывая завершение читателя."""
        try:
            self._error_handler(message)
        except Exception as err:
            self._logger.exception(
                f'Не удалось передать ошибку читателя очереди {self._queue_name}: {err}'
            )


# =============================================================
# ================= Транспорт дочерней сессии ==================
# =============================================================


class _SessionProcessTransport(QObject):
    """Управляет дочерней сессией МК и межпроцессорными очередями.

    Транспорт не содержит правил пользовательского сценария. Он запускает
    процесс, передаёт команды и доставляет из IPC пакеты и события сессии.

    Сигналы:
        data_received(PackageType): Получен корректный пакет измерений.
        session_event_received(SessionEvent): Получено событие сессии.
        error_occurred(str): Возникла ошибка транспорта или IPC.
        finished(): Ресурсы процесса и IPC освобождены.
    """

    data_received = pyqtSignal(PackageType)
    session_event_received = pyqtSignal(object)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, logger: logging.Logger):
        super().__init__()
        self._logger: logging.Logger = logger
        self._mp_context: BaseContext = get_context('spawn')
        self._mc_session_process: Optional[Process] = None
        self._command_queue: Optional[Queue] = None
        self._response_queue: Optional[Queue] = None
        self._data_queue: Optional[Queue] = None
        self._response_queue_reader: Optional[_QueueReader] = None
        self._data_queue_reader: Optional[_QueueReader] = None
        self._response_queue_thread: Optional[Thread] = None
        self._data_queue_thread: Optional[Thread] = None

    @property
    def is_active(self) -> bool:
        """Возвращает ``True``, когда дочерний процесс ещё выполняется."""
        process = self._mc_session_process
        if process is None:
            return False

        try:
            return process.is_alive()
        except ValueError:
            return False

    @property
    def has_resources(self) -> bool:
        """Возвращает ``True``, если транспорт владеет незакрытыми ресурсами."""
        return any((
            self._mc_session_process is not None,
            self._command_queue is not None,
            self._response_queue is not None,
            self._data_queue is not None,
            self._response_queue_thread is not None,
            self._data_queue_thread is not None,
        ))

    # =============================================================
    # ======================== Публичный API ======================
    # =============================================================

    def start(self,
              logger_config: LoggerConfig,
              com_port_config: ComPortConfig,
              bin_file: Path) -> None:
        """Запускает дочернюю сессию и читателей IPC-очередей.

        Завершившаяся сессия очищается до создания нового процесса.

        Args:
            logger_config: Конфигурация логирования дочернего процесса.
            com_port_config: Конфигурация COM-порта дочернего процесса.
            bin_file: Файл записи исходного байтового потока.

        Raises:
            ComPortReaderException: Сессия уже запущена.
        """
        if self.is_active:
            raise ComPortReaderException('Сессия взаимодействия с МК уже запущена!')

        if self.has_resources:
            self._logger.debug('Очистка ресурсов завершившейся сессии МК')
            self.shutdown()

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
        self._start_queue_readers()

    def send_command(self, command_request: CommandRequest) -> None:
        """Передаёт команду дочерней сессии.

        Args:
            command_request: Команда для контроллера дочернего процесса.

        Raises:
            SessionNotRunning: Дочерний процесс не запущен.
        """
        if not self.is_active or self._command_queue is None:
            raise SessionNotRunning('Для отправки команды сначала запустите процесс!')

        self._logger.debug(f'Отправка команды {command_request.command}')
        self._command_queue.put(command_request.model_dump())

    def shutdown(self,
                 process_timeout_ms: int = 3000,
                 thread_timeout_ms: int = 1000) -> None:
        """Блокирующе освобождает ресурсы дочерней сессии.

        Args:
            process_timeout_ms: Время ожидания штатного завершения процесса.
            thread_timeout_ms: Время ожидания каждого читателя очереди.

        Raises:
            ComPortReaderException: Не удалось полностью остановить транспорт.
        """
        if not self.has_resources:
            return

        self._logger.debug('Начало завершения транспорта сессии МК')
        self._request_session_stop()
        self._wait_session_process(process_timeout_ms)
        if self.is_active:
            raise ComPortReaderException('Не удалось завершить дочерний процесс сессии МК!')

        if not self._stop_queue_readers(thread_timeout_ms):
            raise ComPortReaderException('Не удалось остановить читатели IPC-очередей!')

        self._close_ipc_queues()
        self._close_session_process()
        self._logger.debug('Завершение транспорта сессии МК выполнено')
        self.finished.emit()

    # =============================================================
    # ======================= Работа с IPC ========================
    # =============================================================

    def _start_queue_readers(self) -> None:
        """Создаёт и запускает читатели очередей событий и данных."""
        if self._response_queue is None or self._data_queue is None:
            raise ComPortReaderException('IPC-очереди не были созданы!')

        self._response_queue_thread, self._response_queue_reader = self._start_queue_reader(
            source_queue=self._response_queue,
            queue_name='response_queue',
            item_handler=self._handle_session_event_data,
        )
        self._data_queue_thread, self._data_queue_reader = self._start_queue_reader(
            source_queue=self._data_queue,
            queue_name='data_queue',
            item_handler=self._handle_package_data,
        )

    def _start_queue_reader(self,
                            source_queue: Queue,
                            queue_name: str,
                            item_handler: Callable[[object], None]) -> tuple[Thread, _QueueReader]:
        """Создаёт и запускает читатель одной очереди.

        Args:
            source_queue: Очередь для чтения.
            queue_name: Имя очереди в журнале.
            item_handler: Обработчик каждого полученного элемента.

        Returns:
            Запущенный поток и его читатель очереди.
        """
        reader = _QueueReader(
            source_queue=source_queue,
            logger=self._logger,
            queue_name=queue_name,
            is_process_active=lambda: self.is_active,
            item_handler=item_handler,
            error_handler=self.error_occurred.emit,
        )
        thread = Thread(
            target=reader.run,
            name=f'{queue_name}_reader',
            daemon=True,
        )
        thread.start()
        return thread, reader

    def _handle_session_event_data(self, session_event_data: object) -> None:
        """Валидирует событие из response_queue и передаёт его GUI."""
        try:
            session_event = SessionEvent.model_validate(session_event_data)
        except ValidationError as err:
            self.error_occurred.emit(
                f'Получено некорректное событие из response_queue: {err}'
            )
            return

        self.session_event_received.emit(session_event)

    def _handle_package_data(self, package_data: object) -> None:
        """Проверяет тип пакета из data_queue и передаёт его GUI."""
        if not isinstance(package_data, PackageType):
            self.error_occurred.emit(
                'Получен некорректный пакет из data_queue: '
                f'ожидается {PackageType.__name__}, получен {type(package_data).__name__}'
            )
            return

        self.data_received.emit(package_data)

    # =============================================================
    # ===================== Завершение ресурсов ===================
    # =============================================================

    def _request_session_stop(self) -> None:
        """Отправляет дочерней сессии команду штатной остановки."""
        if not self.is_active:
            return

        try:
            self.send_command(CommandRequest(command=CommandName.STOP_RUNNING))
        except (OSError, ValueError, SessionNotRunning) as err:
            self._logger.warning(f'Не удалось отправить команду остановки сессии МК: {err}')

    def _wait_session_process(self, timeout_ms: int) -> None:
        """Ожидает процесс и при необходимости завершает его принудительно."""
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

    def _stop_queue_readers(self, timeout_ms: int) -> bool:
        """Останавливает читатели очередей и возвращает успешность остановки."""
        self._request_queue_reader_stop(self._response_queue_reader, 'response_queue')
        self._request_queue_reader_stop(self._data_queue_reader, 'data_queue')

        response_stopped = self._wait_queue_reader_thread(
            self._response_queue_thread,
            'response_queue',
            timeout_ms,
        )
        data_stopped = self._wait_queue_reader_thread(
            self._data_queue_thread,
            'data_queue',
            timeout_ms,
        )
        if not response_stopped or not data_stopped:
            return False

        self._response_queue_reader = None
        self._data_queue_reader = None
        self._response_queue_thread = None
        self._data_queue_thread = None
        return True

    def _request_queue_reader_stop(self,
                                   reader: Optional[_QueueReader],
                                   queue_name: str) -> None:
        """Запрашивает остановку одного читателя очереди."""
        if reader is None:
            return

        self._logger.debug(f'Запрос остановки чтения очереди {queue_name}')
        reader.stop()

    def _wait_queue_reader_thread(self,
                                  thread: Optional[Thread],
                                  queue_name: str,
                                  timeout_ms: int) -> bool:
        """Ожидает один поток чтения очереди.

        Args:
            thread: Ожидаемый поток.
            queue_name: Имя очереди в журнале.
            timeout_ms: Максимальное время ожидания.

        Returns:
            ``True``, если поток остановлен или не создавался.
        """
        if thread is None:
            return True

        if thread.is_alive():
            self._logger.debug(f'Ожидание остановки потока чтения очереди {queue_name}')
            thread.join(timeout_ms / 1000)

        if thread.is_alive():
            self._logger.warning(f'Поток чтения очереди {queue_name} не остановился вовремя')
            return False

        self._logger.debug(f'Поток чтения очереди {queue_name} остановлен')
        return True

    def _close_ipc_queues(self) -> None:
        """Закрывает IPC-очереди после остановки их читателей."""
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
# ======================== Qt-фасад ===========================
# =============================================================


class ComPortReader(QObject):
    """Предоставляет GUI доступ к сессии обмена с МК.

    Класс не определяет пользовательский сценарий. Порядок вызова команд
    задаётся состояниями :class:`ProgramStage` главного окна. Фасад проверяет
    только конфигурацию и активность дочерней сессии.

    Сигналы:
        data_received(PackageType): Последний пакет измерений для отображения.
        handshake_done(): Рукопожатие успешно завершено.
        handshake_failed(): Рукопожатие завершилось ошибкой.
        connection_failed(str): Не удалось открыть COM-порт.
        saving_file_result(bool, str, str): Результат подготовки CSV-файла.
        static_init_done(): Набор статического буфера завершён.
        measuring_stopped(): Измерения завершены, CSV-файл закрыт.
        error_occurred(str): Возникла аварийная ошибка сессии или транспорта.
        finished(): Ресурсы процесса и IPC освобождены.

    Args:
        _logger: Логгер приложения.
    """

    data_received = pyqtSignal(PackageType)
    handshake_done = pyqtSignal()
    handshake_failed = pyqtSignal()
    connection_failed = pyqtSignal(str)
    saving_file_result = pyqtSignal(bool, str, str)
    static_init_done = pyqtSignal()
    measuring_stopped = pyqtSignal()
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    _session_error_messages: dict[SessionEventName, str] = {
        SessionEventName.UNKNOWN_ERROR: 'Получена неизвестная ошибка при работе с МК',
        SessionEventName.READ_ERROR: 'Ошибка чтения данных из COM-порта',
        SessionEventName.DEVICE_LOST: 'Потеряна связь с устройством',
        SessionEventName.COMMAND_ACK_TIMEOUT: 'Таймаут подтверждения команды от МК',
        SessionEventName.COMMAND_REJECTED: 'МК отклонил отправленную команду',
        SessionEventName.STORAGE_ERROR: 'Ошибка работы с CSV-файлом',
    }

    def __init__(self, _logger: logging.Logger):
        super().__init__()
        self._logger: logging.Logger = _logger
        self._transport: _SessionProcessTransport = _SessionProcessTransport(_logger)
        self._is_configured: bool = False
        self._simple_event_handlers: dict[SessionEventName, Callable[[], None]] = {
            SessionEventName.HANDSHAKE_DONE: self.handshake_done.emit,
            SessionEventName.HANDSHAKE_FAILED: self.handshake_failed.emit,
            SessionEventName.STOP_STATIC_INIT: self.static_init_done.emit,
            SessionEventName.MEASURING_STOPPED: self.measuring_stopped.emit,
        }

        self._transport.data_received.connect(self.data_received.emit)
        self._transport.session_event_received.connect(self._session_event_handler)
        self._transport.error_occurred.connect(self.error_occurred.emit)
        self._transport.finished.connect(self.finished.emit)

    @property
    def is_active(self) -> bool:
        """Возвращает ``True``, когда дочерняя сессия с МК активна."""
        return self._transport.is_active

    # =============================================================
    # ======================== Публичный API ======================
    # =============================================================

    def configure(self,
                  logger_config: LoggerConfig,
                  com_port_name: str,
                  bin_file: Path) -> None:
        """Запускает сессию с МК и инициирует рукопожатие.

        Args:
            logger_config: Конфигурация логирования дочернего процесса.
            com_port_name: Имя COM-порта для подключения к МК.
            bin_file: Путь к файлу сохранения исходного байтового потока.

        Raises:
            ComPortReaderException: Сессия уже запущена.
            NeedConfiguration: Не задан COM-порт.
            TypeError: ``bin_file`` не является :class:`pathlib.Path`.
        """
        if self.is_active:
            raise ComPortReaderException(
                'Нельзя изменить параметры при запущенной сессии взаимодействия с МК!'
            )
        if not com_port_name:
            raise NeedConfiguration('Не задан COM-порт для подключения к МК!')
        if not isinstance(bin_file, Path):
            raise TypeError(f'Ожидается bin_file: Path, получен {type(bin_file)}')

        com_port_config = ComPortConfig(name=com_port_name, baudrate=115200)
        self._logger.debug(
            f'Конфигурирование ComPortReader: port={com_port_name}, bin_file={bin_file}'
        )
        try:
            self._transport.start(logger_config, com_port_config, bin_file)
            self._transport.send_command(CommandRequest(command=CommandName.HANDSHAKE_INIT))
        except Exception:
            self._logger.exception(
                'Ошибка конфигурирования ComPortReader, выполняется очистка ресурсов'
            )
            self._cleanup_after_configuration_error()
            self._is_configured = False
            raise

        self._is_configured = True

    def start_static_init(self) -> None:
        """Передаёт МК команду начала набора статического буфера.

        Raises:
            NeedConfiguration: Параметры подключения ещё не заданы.
            SessionNotRunning: Дочерняя сессия не выполняется.
        """
        self._send_session_command(CommandName.START_STATIC_INIT)

    def set_saving_file(self, file_path: Path) -> None:
        """Передаёт сессии путь нового CSV-файла.

        Args:
            file_path: Абсолютный путь к подготавливаемому CSV-файлу.

        Raises:
            TypeError: Если ``file_path`` не является :class:`Path`.
            ValueError: Если путь не абсолютный.
            NeedConfiguration: Параметры подключения ещё не заданы.
            SessionNotRunning: Дочерняя сессия не выполняется.
        """
        if not isinstance(file_path, Path):
            raise TypeError(f'Ожидается file_path: Path, получен {type(file_path)}')
        if not file_path.is_absolute():
            raise ValueError('Путь к CSV-файлу должен быть абсолютным')

        self._send_session_command(
            CommandName.SET_SAVING_FILE,
            params={'filepath': str(file_path)},
        )

    def start_measuring(self) -> None:
        """Передаёт МК команду начала измерений.

        Raises:
            NeedConfiguration: Параметры подключения ещё не заданы.
            SessionNotRunning: Дочерняя сессия не выполняется.
        """
        self._send_session_command(CommandName.START_MEASURING)

    def stop_measuring(self) -> None:
        """Передаёт МК команду остановки измерений.

        Raises:
            NeedConfiguration: Параметры подключения ещё не заданы.
            SessionNotRunning: Дочерняя сессия не выполняется.
        """
        self._send_session_command(CommandName.STOP_MEASURING)

    def stop_running(self) -> None:
        """Запрашивает штатное завершение дочерней сессии.

        Raises:
            NeedConfiguration: Параметры подключения ещё не заданы.
            SessionNotRunning: Дочерняя сессия не выполняется.
        """
        self._send_session_command(CommandName.STOP_RUNNING)

    def shutdown(self,
                 process_timeout_ms: int = 3000,
                 thread_timeout_ms: int = 1000) -> None:
        """Блокирующе освобождает ресурсы сессии для закрытия приложения.

        Args:
            process_timeout_ms: Время ожидания штатного завершения процесса.
            thread_timeout_ms: Время ожидания каждого потока чтения очереди.

        Raises:
            ComPortReaderException: Не удалось полностью освободить ресурсы.
        """
        self._logger.debug('Завершение работы ComPortReader')
        self._transport.shutdown(
            process_timeout_ms=process_timeout_ms,
            thread_timeout_ms=thread_timeout_ms,
        )
        self._is_configured = False

    def close(self) -> None:
        """Блокирующе закрывает ComPortReader."""
        self.shutdown()

    # =============================================================
    # ======================= Внутренняя логика ===================
    # =============================================================

    def _send_session_command(self,
                              command: CommandName,
                              params: Optional[dict[str, object]] = None) -> None:
        """Проверяет сессию и передаёт ей одну команду."""
        self._ensure_session_running()
        self._transport.send_command(CommandRequest(command=command, params=params or {}))

    def _ensure_session_running(self) -> None:
        """Проверяет, что сессия сконфигурирована и выполняется.

        Raises:
            NeedConfiguration: Параметры подключения ещё не заданы.
            SessionNotRunning: Дочерняя сессия завершилась или не была запущена.
        """
        if not self._is_configured:
            raise NeedConfiguration('Перед началом работы задайте параметры подключения!')
        if not self.is_active:
            raise SessionNotRunning('Сессия взаимодействия с МК не запущена!')

    def _cleanup_after_configuration_error(self) -> None:
        """Освобождает транспорт, сохраняя исходную ошибку конфигурации."""
        try:
            self._transport.shutdown()
        except Exception as err:
            self._logger.exception(
                f'Не удалось очистить ресурсы после ошибки конфигурирования: {err}'
            )

    # =============================================================
    # ===================== Обработка событий =====================
    # =============================================================

    def _session_event_handler(self, session_event: SessionEvent) -> None:
        """Преобразует событие дочерней сессии в публичный Qt-сигнал."""
        self._logger.debug(f'Получено событие сессии: {session_event.event}')
        simple_handler = self._simple_event_handlers.get(session_event.event)
        if simple_handler is not None:
            simple_handler()
            return

        if session_event.event is SessionEventName.CONNECTION_FAILED:
            self._connection_failed_handler(session_event)
            return

        if session_event.event is SessionEventName.SET_SAVING_FILE_RESULT:
            self._saving_file_result_handler(session_event)
            return

        error_message = self._session_error_messages.get(session_event.event)
        if error_message is not None:
            error_info = session_event.params.get('error_info')
            if isinstance(error_info, str) and error_info:
                error_message = f'{error_message}: {error_info}'
            self.error_occurred.emit(error_message)
            return

        self._logger.warning(f'Получено неизвестное событие сессии: {session_event.event}')

    def _connection_failed_handler(self, session_event: SessionEvent) -> None:
        """Извлекает описание ошибки подключения из события сессии."""
        error_info = session_event.params.get('error_info')
        message = (
            error_info
            if isinstance(error_info, str) and error_info
            else 'Не удалось подключиться к COM-порту'
        )
        self.connection_failed.emit(message)

    def _saving_file_result_handler(self, session_event: SessionEvent) -> None:
        """Извлекает результат команды SET_SAVING_FILE из события сессии."""
        success = session_event.params.get('success')
        filepath = session_event.params.get('filepath')
        error_info = session_event.params.get('error_info')

        if not isinstance(success, bool) or not isinstance(filepath, str):
            self.error_occurred.emit('Получен некорректный результат команды SET_SAVING_FILE')
            return

        self.saving_file_result.emit(
            success,
            filepath,
            error_info if isinstance(error_info, str) else '',
        )
