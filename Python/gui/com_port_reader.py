# -*- coding: utf-8 -*-
"""Модуль для асинхронного чтения данных из COM-порта.

Содержит класс `ComPortReader`, который управляет фоновым потоком для
непрерывного чтения байтов из COM-порта, их декодирования с помощью
`Decoder` и передачи полученных пакетов в главный поток через сигналы.
"""
# System imports
import logging
from queue import Empty
from threading import Thread
from typing import Optional, Callable
from pathlib import Path
from multiprocessing import get_context
from multiprocessing.context import BaseContext, Process
from multiprocessing.queues import Queue

# External imports
from PyQt5.QtCore import QObject, pyqtSignal

# User imports
from async_mc_controller.config import LoggerConfig, ComPortConfig
from telega_session import start_telega_session
from telega_session import TelegaData as PackageType

##########################################################

# =============================================================
# === Исключения, которые могут быть выброшены в ходе работы ==
# =============================================================

class ComPortReaderException(RuntimeError):
    pass

class SessionNotRunning(ComPortReaderException):
    pass

class NeedConfiguration(ComPortReaderException):
    pass

class CalibrationRunning(ComPortReaderException):
    pass

class StaticInitRunning(ComPortReaderException):
    pass

class MeasuringRunning(ComPortReaderException):
    pass

class MeasuringNotRunning(ComPortReaderException):
    pass

# -------------------------------------------------------------

class ComPortReader(QObject):
    """Класс для управления фоновым чтением данных из COM-порта.

    Сигналы:
        data_received(PackageType): Испускается при получении нового пакета данных.
        connection_failed(str): Испускается при ошибке запуска сессии подключения.
        error_occurred(str): Испускается при возникновении ошибки чтения или декодирования.
        finished(): Испускается после полной остановки потока и очистки ресурсов.
    """

    data_received = pyqtSignal(PackageType)
    handshake_done = pyqtSignal()
    handshake_failed = pyqtSignal()
    connection_failed = pyqtSignal(str)
    calibration_done = pyqtSignal()
    static_init_done = pyqtSignal()
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    # ------------------------------------------------------------------------------

    class _ComPortReaderWorker(QObject):
        """Внутренний класс, выполняющий низкоуровневое взаимодействие с МК.

        Сигналы:
            data_received(DataType): Пробрасывается наружу.
            error_occurred(str): Пробрасывается наружу.
            finished(): Испускается при завершении работы (всегда).
        """

        data_received = pyqtSignal(PackageType)
        message_received = pyqtSignal(str)
        error_occurred = pyqtSignal(str)
        finished = pyqtSignal()

        class _QueueReader(QObject):
            """Читатель multiprocessing.Queue для запуска в отдельном потоке."""
            item_received = pyqtSignal(object)
            error_occurred = pyqtSignal(str)
            finished = pyqtSignal()

            def __init__(self,
                         source_queue: Queue,
                         logger: logging.Logger,
                         queue_name: str,
                         is_process_active: Callable[[], bool]):
                super().__init__()
                self._source_queue = source_queue
                self._logger = logger
                self._queue_name = queue_name
                self._is_process_active = is_process_active
                self._stop_requested = False

            def stop(self) -> None:
                """Запрашивает остановку цикла чтения очереди."""
                self._stop_requested = True

            def run(self) -> None:
                """Читает очередь и отправляет элементы через Qt-сигнал."""
                self._logger.debug(f'Запуск чтения очереди {self._queue_name}')
                try:
                    while not self._stop_requested:
                        try:
                            item = self._source_queue.get(timeout=0.1)
                        except Empty:
                            if not self._is_process_active():
                                break
                            continue
                        except (EOFError, OSError) as err:
                            self.error_occurred.emit(f'Ошибка чтения очереди {self._queue_name}: {err}')
                            break

                        if self._stop_requested:
                            break
                        self.item_received.emit(item)
                finally:
                    self._logger.debug(f'Остановка чтения очереди {self._queue_name}')
                    self.finished.emit()

        def __init__(self, logger: logging.Logger):
            """ Инициализирует воркер для взаимодействия с МК """
            super().__init__()
            self._logger = logger
            self._mp_context: BaseContext = get_context("spawn")

            # Процесс, в котором будет запущена сессия для работы с МК
            self._mc_session_process: Optional[Process] = None

            # Очереди для межпроцессорного взаимодействия
            # Используем spawn, чтобы Windows и Debian создавали дочерний процесс одинаково
            # и он не наследовал внутреннее состояние Qt-приложения.
            self._command_queue: Queue = self._mp_context.Queue()
            self._response_queue: Queue = self._mp_context.Queue()
            self._data_queue: Queue = self._mp_context.Queue()

            # Потоки для чтения сообщений и данных от self._mc_session_process
            self._reading_response_queue_thread: Optional[Thread] = None
            self._reading_data_queue_thread: Optional[Thread] = None
            self._response_queue_reader: Optional[ComPortReader._ComPortReaderWorker._QueueReader] = None
            self._data_queue_reader: Optional[ComPortReader._ComPortReaderWorker._QueueReader] = None

        @property
        def is_active(self) -> bool:
            process = self._mc_session_process
            if process is None:
                return False

            try:
                return process.is_alive()
            except ValueError:
                return False

        def launch(self,
                   logger_config: LoggerConfig,
                   com_port_config: ComPortConfig,
                   bin_file: Path) -> None:
            """Запускает процесс сессии МК и потоки чтения IPC-очередей.

            Args:
                logger_config: Конфигурация логирования дочернего процесса.
                com_port_config: Конфигурация COM-порта дочернего процесса.
                bin_file: Файл для сохранения исходного байтового потока.

            Raises:
                ComPortReaderException: Если сессия взаимодействия с МК уже запущена.
            """
            if self.is_active:
                raise ComPortReaderException("Сессия взаимодействия с МК уже запущена!")

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
            self._start_queue_reader_threads()

        def _start_queue_reader_threads(self) -> None:
            """Запускает потоки чтения очередей ответов и данных."""
            self._reading_response_queue_thread, self._response_queue_reader = self._start_queue_reader_thread(
                source_queue=self._response_queue,
                queue_name='response_queue',
                item_handler=lambda msg: self.message_received.emit(str(msg)),
            )
            self._reading_data_queue_thread, self._data_queue_reader = self._start_queue_reader_thread(
                source_queue=self._data_queue,
                queue_name='data_queue',
                item_handler=lambda package: self.data_received.emit(package),
            )

        def _start_queue_reader_thread(self,
                                       source_queue: Queue,
                                       queue_name: str,
                                       item_handler: Callable[[object], None]
                                       ) -> tuple[Thread, 'ComPortReader._ComPortReaderWorker._QueueReader']:
            """Создаёт поток с читателем одной очереди.

            Args:
                source_queue: Очередь для чтения.
                queue_name: Имя очереди для сообщений лога.
                item_handler: Обработчик полученного элемента очереди.
            """
            reader = self._QueueReader(
                source_queue=source_queue,
                logger=self._logger,
                queue_name=queue_name,
                is_process_active=lambda: self.is_active,
            )
            reader.item_received.connect(item_handler)
            reader.error_occurred.connect(self.error_occurred.emit)

            thread = Thread(
                target=reader.run,
                name=f'{queue_name}_reader',
                daemon=True,
            )
            thread.start()
            return thread, reader

        def send_command(self, command: str) -> None:
            """Отправляет команду в self._command_queue.

            Args:
                command: Текстовая команда для контроллера дочернего процесса.

            Raises:
                SessionNotRunning: Если дочерний процесс сессии не запущен.
            """
            if self.is_active:
                self._logger.debug(f'Отправка команды {command}')
                self._command_queue.put(command)
            else:
                raise SessionNotRunning("Для отправки команды сначала запустите процесс!")

        def shutdown(self,
                     process_timeout_ms: int = 3000,
                     thread_timeout_ms: int = 1000
                     ) -> None:
            """Блокирующе завершает дочерний процесс и потоки чтения очередей.

            Args:
                process_timeout_ms: Время ожидания штатного завершения процесса.
                thread_timeout_ms: Время ожидания завершения каждого потока чтения очереди.
            """
            has_process = self._mc_session_process is not None
            has_threads = (self._reading_response_queue_thread is not None or
                           self._reading_data_queue_thread is not None)
            if not has_process and not has_threads:
                return

            self._logger.debug('Начало завершения работы ComPortReaderWorker')
            self._request_session_stop()
            self._wait_session_process(process_timeout_ms)
            self._stop_queue_reader_threads(thread_timeout_ms)
            self._close_ipc_queues()
            self._close_session_process()
            self._mc_session_process = None
            self._logger.debug('Завершение работы ComPortReaderWorker выполнено')
            self.finished.emit()

        def _request_session_stop(self) -> None:
            """Отправляет команду штатной остановки в дочерний процесс."""
            if not self.is_active:
                return

            try:
                self._logger.debug('Отправка команды штатного завершения сессии МК')
                self._command_queue.put("STOP_RUNNING")
            except (OSError, ValueError) as err:
                self._logger.warning(f'Не удалось отправить команду остановки сессии МК: {err}')

        def _wait_session_process(self, timeout_ms: int) -> None:
            """Ожидает завершения дочернего процесса и при необходимости останавливает его принудительно."""
            process = self._mc_session_process
            if process is None:
                return

            if process.is_alive():
                self._logger.debug('Ожидание завершения дочернего процесса сессии МК')
                process.join(timeout_ms / 1000)

            if process.is_alive():
                self._logger.warning('Дочерний процесс сессии МК не завершился штатно, выполняется terminate()')
                process.terminate()
                process.join(1)

            if process.is_alive() and hasattr(process, 'kill'):
                self._logger.warning('Дочерний процесс сессии МК не завершился после terminate(), выполняется kill()')
                process.kill()
                process.join(1)

            if process.is_alive():
                self._logger.error('Не удалось завершить дочерний процесс сессии МК')
            else:
                self._logger.debug(f'Дочерний процесс сессии МК завершён с кодом {process.exitcode}')

        def _close_session_process(self) -> None:
            """Закрывает дескриптор дочернего процесса после остановки читателей очередей."""
            process = self._mc_session_process
            if process is None:
                return

            try:
                process.close()
            except ValueError as err:
                self._logger.debug(f'Дескриптор дочернего процесса пока не закрыт: {err}')

        def _stop_queue_reader_threads(self, timeout_ms: int) -> None:
            """Запрашивает остановку читателей очередей и дожидается завершения потоков."""
            self._request_queue_reader_stop(self._response_queue_reader, 'response_queue')
            self._request_queue_reader_stop(self._data_queue_reader, 'data_queue')

            self._wait_queue_reader_thread(self._reading_response_queue_thread, 'response_queue', timeout_ms)
            self._wait_queue_reader_thread(self._reading_data_queue_thread, 'data_queue', timeout_ms)

            self._reading_response_queue_thread = None
            self._reading_data_queue_thread = None
            self._response_queue_reader = None
            self._data_queue_reader = None

        def _request_queue_reader_stop(self,
                                       reader: Optional['ComPortReader._ComPortReaderWorker._QueueReader'],
                                       queue_name: str
                                       ) -> None:
            """Запрашивает остановку одного читателя очереди."""
            if reader is None:
                return

            try:
                self._logger.debug(f'Запрос остановки чтения очереди {queue_name}')
                reader.stop()
            except RuntimeError:
                self._logger.debug(f'Читатель очереди {queue_name} уже удалён')

        def _wait_queue_reader_thread(self,
                                      thread: Optional[Thread],
                                      queue_name: str,
                                      timeout_ms: int
                                      ) -> None:
            """Ожидает остановки одного потока чтения очереди."""
            if thread is None:
                return

            if not thread.is_alive():
                self._logger.debug(f'Поток чтения очереди {queue_name} уже остановлен')
                return

            self._logger.debug(f'Ожидание остановки потока чтения очереди {queue_name}')
            thread.join(timeout_ms / 1000)
            if thread.is_alive():
                self._logger.warning(f'Поток чтения очереди {queue_name} не остановился вовремя')
            else:
                self._logger.debug(f'Поток чтения очереди {queue_name} остановлен')

        def _close_ipc_queues(self) -> None:
            """Закрывает IPC-очереди, созданные для дочернего процесса."""
            for queue_name, queue in (
                ('command_queue', self._command_queue),
                ('response_queue', self._response_queue),
                ('data_queue', self._data_queue),
            ):
                try:
                    queue.close()
                    queue.join_thread()
                    self._logger.debug(f'Очередь {queue_name} закрыта')
                except (OSError, ValueError) as err:
                    self._logger.debug(f'Очередь {queue_name} уже закрыта или недоступна: {err}')

    # ------------------------------------------------------------------------------

    def __init__(self, _logger: logging.Logger):
        super().__init__()
        self._logger = _logger
        self._worker = ComPortReader._ComPortReaderWorker(_logger)
        self._worker.data_received.connect(self.data_received.emit)
        self._worker.message_received.connect(self._message_handler)
        self._worker.error_occurred.connect(self.error_occurred.emit)
        self._worker.finished.connect(self.finished.emit)

        # Флаги состояния
        self._calibration_running_flag: bool = False
        self._static_init_running_flag: bool = False
        self._measuring_running_flag: bool = False
        self._is_configured: bool = False

        # Словарь соответствия полученного сообщения от контроллера и его обработчиком
        self._msg_to_handler: dict[str, Callable[[], None]] = {
            "HANDSHAKE_DONE": self._handshake_done_handler,
            "HANDSHAKE_FAILED": self._handshake_failed_handler,
            "STOP_CALIBRATION": self._stop_calibration_handler,
            "STOP_STATIC_INIT": self._stop_static_init_handler,
            "UNKNOWN_ERROR": self._unknown_error_handler,
            "READ_ERROR": self._read_error_handler,
            "DEVICE_LOST": self._device_lost_handler,
            "COMMAND_ACK_TIMEOUT": self._command_ack_timeout_handler,
            "COMMAND_REJECTED": self._command_rejected_handler,
        }

    @property
    def is_active(self) -> bool:
        return self._worker is not None and self._worker.is_active

    def _ensure_configured(self) -> None:
        """Проверяет, что параметры подключения были заданы.

        Raises:
            NeedConfiguration: Если configure() ещё не был вызван.
        """
        if not self._is_configured:
            raise NeedConfiguration("Перед началом работы задайте параметры подключения!")

    def _ensure_session_running(self) -> None:
        """Проверяет, что дочерний процесс сессии запущен.

        Raises:
            NeedConfiguration: Если configure() ещё не был вызван.
            SessionNotRunning: Если дочерний процесс не запущен или уже завершился.
        """
        self._ensure_configured()
        if not self.is_active:
            raise SessionNotRunning("Сессия взаимодействия с МК не запущена!")

    # =============================================================
    # ============== Методы для обработки полученных ==============
    # ================== сообщений от контроллера =================
    # =============================================================

    def _message_handler(self, msg: str) -> None:
        """ Обработка полученного сообщения от контроллера """
        self._logger.debug(f'Получено сообщение: {msg}')
        if msg.startswith("CONNECTION_FAILED"):
            _, _, error_info = msg.partition(":")
            self._connection_failed_handler(error_info.strip())
            return

        if msg in self._msg_to_handler.keys():
            handler = self._msg_to_handler[msg]
            handler()
        else:
            self._logger.warning(f'Получено сообщение от контроллера: {msg}')

    def _handshake_done_handler(self) -> None:
        """ Обработчик успешной процедуры рукопожатия """
        self.handshake_done.emit()

    def _handshake_failed_handler(self) -> None:
        """ Обработчик ошибки процедуры рукопожатия """
        self._reset_running_flags()
        self.handshake_failed.emit()

    def _connection_failed_handler(self, error_info: str) -> None:
        """ Обработчик ошибки запуска подключения к МК. """
        self._reset_running_flags()
        message = error_info or 'Не удалось подключиться к COM-порту'
        self.connection_failed.emit(message)

    def _stop_calibration_handler(self) -> None:
        """ Обработчик завершения калибровки датчиков """
        self._calibration_running_flag = False
        self.calibration_done.emit()

    def _stop_static_init_handler(self) -> None:
        """ Обработчик завершения набора статического буфера """
        self._static_init_running_flag = False
        self.static_init_done.emit()

    def _unknown_error_handler(self) -> None:
        """ Обработчик прерывания сбора данных """
        self._reset_running_flags()
        self.error_occurred.emit("Получена неизвестная ошибка при работе с МК")

    def _read_error_handler(self) -> None:
        """ Обработчик ошибки чтения данных """
        self._reset_running_flags()
        self.error_occurred.emit("Ошибка чтения данных из COM-порта")

    def _device_lost_handler(self) -> None:
        """ Обработчик потери связи с устройством """
        self._reset_running_flags()
        self.error_occurred.emit("Потеряна связь с устройством")

    def _command_ack_timeout_handler(self) -> None:
        """ Обработчик таймаута команды от МК """
        self._reset_running_flags()
        self.error_occurred.emit("Таймаут подтверждения команды от МК")

    def _command_rejected_handler(self) -> None:
        """ Обработчик отклонения команды МК """
        self._reset_running_flags()
        self.error_occurred.emit("МК отклонил отправленную команду")

    def _reset_running_flags(self) -> None:
        """Сбрасывает флаги активных процедур."""
        self._calibration_running_flag = False
        self._static_init_running_flag = False
        self._measuring_running_flag = False

    # =============================================================
    # =================== Публичные методы ========================
    # =============================================================

    def stop_running(self) -> None:
        """Завершает работу дочерней сессии с МК.

        Raises:
            NeedConfiguration: Если configure() ещё не был вызван.
            SessionNotRunning: Если дочерний процесс не запущен или уже завершился.
        """
        self._ensure_session_running()
        self._worker.send_command("STOP_RUNNING")

    def shutdown(self,
                 process_timeout_ms: int = 3000,
                 thread_timeout_ms: int = 1000
                 ) -> None:
        """Блокирующе освобождает ресурсы сессии для закрытия приложения.

        Args:
            process_timeout_ms: Время ожидания штатного завершения дочернего процесса.
            thread_timeout_ms: Время ожидания завершения каждого потока чтения очереди.
        """
        self._logger.debug('Завершение работы ComPortReader')
        try:
            self._worker.shutdown(
                process_timeout_ms=process_timeout_ms,
                thread_timeout_ms=thread_timeout_ms,
            )
        finally:
            self._reset_running_flags()
            self._is_configured = False

    def close(self) -> None:
        """Блокирующе закрывает ComPortReader."""
        self.shutdown()

    def configure(self, logger_config: LoggerConfig, com_port_name: str, bin_file: Path) -> None:
        """Конфигурирует сессию взаимодействия с МК и запускает рукопожатие.

        Args:
            logger_config: Конфигурация используемого логгера.
            com_port_name: Имя COM-порта для подключения к МК.
            bin_file: Путь к бинарному файлу для будущего сохранения сырого потока.

        Raises:
            ComPortReaderException: Если сессия уже запущена или имя COM-порта не задано.
        """
        if self.is_active:
            raise ComPortReaderException("Нельзя изменить параметры при запущенной сессии взаимодействия с МК!")
        if not com_port_name:
            raise NeedConfiguration("Не задан COM-порт для подключения к МК!")
        if not isinstance(bin_file, Path):
            raise TypeError(f"Ожидается bin_file: Path, получен {type(bin_file)}")

        com_port_config = ComPortConfig(name=com_port_name, baudrate=115200)

        self._calibration_running_flag = False
        self._static_init_running_flag = False
        self._measuring_running_flag = False

        self._logger.debug(f'Конфигурирование ComPortReader: port={com_port_name}, bin_file={bin_file}')
        try:
            self._worker.launch(logger_config, com_port_config, bin_file)
            self._worker.send_command("HANDSHAKE_INIT")
            self._is_configured = True
        except Exception:
            self._logger.exception('Ошибка конфигурирования ComPortReader, выполняется очистка ресурсов')
            self.shutdown()
            raise

    def start_calibration(self) -> None:
        """Запускает калибровку датчиков.

        Raises:
            NeedConfiguration: Если configure() ещё не был вызван.
            SessionNotRunning: Если дочерний процесс не запущен или уже завершился.
            CalibrationRunning: Если калибровка уже запущена.
        """
        self._ensure_session_running()
        if not self._calibration_running_flag:
            self._worker.send_command("START_CALIBRATION")
            self._calibration_running_flag = True
        else:
            self._logger.debug("Попытка повторного запуска калибровки")
            raise CalibrationRunning('Калибровка датчиков уже запущена!')

    def start_static_init(self) -> None:
        """Запускает набор статического буфера.

        Raises:
            NeedConfiguration: Если configure() ещё не был вызван.
            SessionNotRunning: Если дочерний процесс не запущен или уже завершился.
            StaticInitRunning: Если набор статического буфера уже запущен.
        """
        self._ensure_session_running()
        if not self._static_init_running_flag:
            self._worker.send_command("START_STATIC_INIT")
            self._static_init_running_flag = True
        else:
            self._logger.debug("Попытка повторного запуска набора статического буфера")
            raise StaticInitRunning('Набор статического буфера уже начат!')

    def start_measuring(self) -> None:
        """Запускает сбор данных с МК.

        Raises:
            NeedConfiguration: Если configure() ещё не был вызван.
            SessionNotRunning: Если дочерний процесс не запущен или уже завершился.
            MeasuringRunning: Если сбор данных уже запущен.
        """
        self._ensure_session_running()
        if not self._measuring_running_flag:
            self._worker.send_command("START_MEASURING")
            self._measuring_running_flag = True
        else:
            self._logger.debug("Попытка повторного запуска сбора данных")
            raise MeasuringRunning('Для начала нового сеанса сбора данных завершите предыдущий!')

    def stop_measuring(self) -> None:
        """Останавливает сбор данных с МК.

        Raises:
            NeedConfiguration: Если configure() ещё не был вызван.
            SessionNotRunning: Если дочерний процесс не запущен или уже завершился.
            MeasuringNotRunning: Если сбор данных ещё не был запущен.
        """
        self._ensure_session_running()
        if self._measuring_running_flag:
            self._worker.send_command("STOP_MEASURING")
            self._measuring_running_flag = False
        else:
            self._logger.debug("Попытка остановки чтения данных до запуска")
            raise MeasuringNotRunning('Для начала запустите чтение данных!')
