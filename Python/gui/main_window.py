"""Главное окно приложения путеизмерительной тележки."""

# System imports
import asyncio
import logging
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Optional

# External imports
from PyQt5.QtGui import QCloseEvent, QIcon, QIntValidator
from PyQt5.QtWidgets import (
    QMainWindow, QToolButton,
    QPushButton, QApplication, QMessageBox,
    QComboBox, QLineEdit, QLCDNumber,
    QCheckBox, QListWidget
)
from PyQt5.uic import loadUi

# User imports
from app_config import AppConfig, config_path
from gui.com_port_reader import (
    ComPortReader,
    ComPortReaderCallbacks,
    ComPortReaderException,
    ComPortSessionConfig,
)
from gui.com_port_settings import ComPortSettings
from gui.data_visualization import DataVisualizer
from gui.indicator_blinker import IndicatorBlinker
from gui.program_stages import (
    MeasuringStage,
    ProgramStage,
    ReadyForMeasurementStage,
    ReadyForStaticInitStage,
    SettingStage,
    StaticInitStage,
)
from gui.saving_params import SavingParams
from logger import AppLogger
from telega_session import TelegaData

##########################################################


class _PendingOperation(Enum):
    """Командная операция, результата которой ожидает главное окно."""

    CONFIGURE = auto()
    START_STATIC_INIT = auto()
    START_MEASURING = auto()
    STOP_MEASURING = auto()


class MainWindow(QMainWindow):
    """Координирует интерфейс и пользовательские стадии приложения."""

    _main_window_path: Path = Path(__file__).parent / 'ui' / 'main_window.ui'
    _app_icon_path: Path = Path(__file__).parent / 'ui' / 'telega.png'
    _messages_limit: int = 500

    def __init__(self) -> None:
        super().__init__(parent=None)

        self._init_app_context()
        self._load_window_ui()
        self._bind_widgets()
        self._init_runtime_state()
        self._create_components()
        self._create_program_stages()
        self._configure_controls()
        self._connect_signals()
        self._start_indicator()

    # =============================================================
    # ================= Инициализация главного окна ================
    # =============================================================

    def _init_app_context(self) -> None:
        """Загружает конфигурацию и создаёт логгер главного окна."""
        self._app_config: AppConfig = AppConfig.load(config_path)
        self._app_config.logger_config.log_filename = 'app_logger.log'
        self._app_config.logger_config.log_level = logging.DEBUG
        self._app_config.logger_config.use_console = False
        self._app_logger: logging.Logger = AppLogger(
            self._app_config
        ).get_child_logger('MainWindow')

    def _load_window_ui(self) -> None:
        """Загружает разметку и задаёт параметры главного окна."""
        loadUi(self._main_window_path, self)
        self.setWindowTitle('Путеизмерительная тележка')
        self.setWindowIcon(QIcon(str(self._app_icon_path)))

    def _bind_widgets(self) -> None:
        """Связывает поля главного окна с виджетами загруженной разметки."""
        self._apply_settings_button = self.findChild(QPushButton, "ApplySettingsButton")
        self._start_static_init_button = self.findChild(QPushButton, "StartStaticInitButton")
        self._start_measuring_button = self.findChild(QPushButton, "StartMeasuringButton")
        self._stop_measuring_button = self.findChild(QPushButton, "StopMeasuringButton")
        self._msg_text_edit = self.findChild(QListWidget, "MessagesTextEdit")
        self._passage_num_edit = self.findChild(QLineEdit, "Passage_Num")
        self._indicator_check_box = self.findChild(QCheckBox, "Indicator")

    def _init_runtime_state(self) -> None:
        """Задаёт начальное изменяемое состояние окна."""
        self._saving_path: Optional[Path] = None
        self._template_filename: Optional[str] = None
        self._pending_operation: Optional[_PendingOperation] = None
        self._session_resetting: bool = False
        self._close_ready: bool = False
        self._close_task: Optional[asyncio.Task[None]] = None
        self._fatal_recovery_task: Optional[asyncio.Task[None]] = None

    def _create_components(self) -> None:
        """Создаёт компоненты интерфейса и взаимодействия с сессией."""
        self._saving_params: SavingParams = SavingParams(
            app_config=self._app_config,
            saving_path_edit=self.findChild(QLineEdit, 'SavingPathEdit'),
            choose_saving_path_button=self.findChild(
                QToolButton,
                'ChooseSavingPathButton',
            ),
            template_filename_edit=self.findChild(
                QLineEdit,
                'TemplateFilenameEdit',
            ),
            template_info_button=self.findChild(
                QPushButton,
                'TemplateInfoButton',
            ),
        )
        self._com_port_settings: ComPortSettings = ComPortSettings(
            app_config=self._app_config,
            com_port_combo_box=self.findChild(QComboBox, 'ComPortComboBox'),
            com_port_info_button=self.findChild(
                QPushButton,
                'ComPortInfoButton',
            ),
            update_com_ports_button=self.findChild(
                QToolButton,
                'UpdateComPortsButton',
            ),
        )
        self._data_visualizer: DataVisualizer = DataVisualizer(
            value_acc_x=self.findChild(QLCDNumber, 'Value_Acc_X'),
            value_acc_y=self.findChild(QLCDNumber, 'Value_Acc_Y'),
            value_acc_z=self.findChild(QLCDNumber, 'Value_Acc_Z'),
            value_gyro_x=self.findChild(QLCDNumber, 'Value_Gyro_X'),
            value_gyro_y=self.findChild(QLCDNumber, 'Value_Gyro_Y'),
            value_gyro_z=self.findChild(QLCDNumber, 'Value_Gyro_Z'),
            dpp_code_value=self.findChild(QLCDNumber, 'DppCodeValue'),
        )
        self._indicator_blinker: IndicatorBlinker = IndicatorBlinker(
            indicator=self._indicator_check_box,
            period_ms=1000,
            logger=self._app_logger,
        )

        callbacks = ComPortReaderCallbacks(
            on_handshake_done=self._handshake_done,
            on_static_init_started=self._static_init_started,
            on_static_init_completed=self._static_init_completed,
            on_measuring_started=self._measuring_started,
            on_measuring_stopped=self._measuring_stopped,
            on_data=self._data_received,
            on_error=self._error_handler,
        )
        self._com_port_reader: ComPortReader = ComPortReader(
            logger=self._app_logger,
            callbacks=callbacks,
        )

    def _create_program_stages(self) -> None:
        """Создаёт устойчивые стадии пользовательского сценария."""
        self._setting_stage: SettingStage = SettingStage(self)
        self._ready_for_static_init_stage: ReadyForStaticInitStage = (
            ReadyForStaticInitStage(self)
        )
        self._static_init_stage: StaticInitStage = StaticInitStage(self)
        self._ready_for_measurement_stage: ReadyForMeasurementStage = (
            ReadyForMeasurementStage(self)
        )
        self._measuring_stage: MeasuringStage = MeasuringStage(self)
        self._current_stage: ProgramStage = self._setting_stage

    def _configure_controls(self) -> None:
        """Задаёт начальные параметры элементов управления."""
        self._passage_num_edit.setValidator(QIntValidator(1, 999999, self))
        self._passage_num_edit.setReadOnly(True)
        self._set_passage_num(1)
        self._update_controls()

    def _connect_signals(self) -> None:
        """Подключает сигналы интерфейса и приложения."""
        self._start_static_init_button.clicked.connect(
            lambda: self._current_stage.start_static_init()
        )
        self._start_measuring_button.clicked.connect(
            lambda: self._current_stage.start_measuring()
        )
        self._stop_measuring_button.clicked.connect(
            lambda: self._current_stage.stop_measuring()
        )
        self._apply_settings_button.clicked.connect(
            lambda: self._current_stage.apply_settings()
        )

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._indicator_blinker.stop)

    def _start_indicator(self) -> None:
        """Запускает индикатор активности приложения."""
        self._indicator_blinker.start()

    # =============================================================
    # =============== Завершение работы приложения ================
    # =============================================================

    def closeEvent(self, event: QCloseEvent) -> None:
        """Асинхронно освобождает сессию перед закрытием окна.

        Args:
            event: Событие закрытия главного окна.
        """
        if self._close_ready:
            event.accept()
            return

        event.ignore()
        self.hide()
        self._indicator_blinker.stop()
        if self._close_task is None:
            self._close_task = asyncio.create_task(
                self._shutdown_and_close(),
                name='main_window_shutdown',
            )
        self._update_controls()

    async def _shutdown_and_close(self) -> None:
        """Дожидается освобождения ресурсов и повторно закрывает окно."""
        try:
            recovery_task = self._fatal_recovery_task
            if recovery_task is not None and not recovery_task.done():
                await recovery_task
            await self._com_port_reader.shutdown()
            self._app_logger.info('Корректное завершение работы приложения')
        except Exception as err:
            self._app_logger.exception(
                f'Ошибка при завершении работы ComPortReader: {err}'
            )
        finally:
            self._close_ready = True
            self.close()

    # =============================================================
    # ================ Настройка и стадии сессии ==================
    # =============================================================

    def configure_session(self,
                          saving_path: Path,
                          template_filename: str,
                          com_port_name: str) -> None:
        """Сохраняет настройки и запускает рукопожатие с МК.

        Args:
            saving_path: Директория сохранения данных.
            template_filename: Шаблон имени файлов текущей сессии.
            com_port_name: Имя используемого COM-порта.

        Raises:
            OSError: Настройки приложения не удалось сохранить.
            TypeError: Переданы параметры неподдерживаемого типа.
        """
        if not self._begin_operation(_PendingOperation.CONFIGURE):
            return

        try:
            resolved_saving_path = saving_path.resolve()
            raw_stream_file = (
                resolved_saving_path / f'{template_filename}.bin'
            ).resolve()
            self._saving_params.save_config()
            self._com_port_settings.save_config()
            session_config = ComPortSessionConfig(
                logger_config=self._app_config.logger_config.model_copy(deep=True),
                com_port_name=com_port_name,
                raw_stream_file=raw_stream_file,
            )
        except Exception:
            self._finish_operation(_PendingOperation.CONFIGURE)
            raise

        self._saving_path = resolved_saving_path
        self._template_filename = template_filename
        self._set_passage_num(1)
        self._saving_params.lock_input()
        self._com_port_settings.lock_input()
        self.add_info_message(
            f'Настройки применены:\n'
            f'COM-порт: {com_port_name}\n'
            f'Шаблонное название файлов: {template_filename}\n'
            f'Директория сохранения: {resolved_saving_path}'
        )
        self.add_info_message('Ожидание рукопожатия с МК')
        self._app_logger.info(
            f'Применение настроек: COM-порт={com_port_name}, '
            f'файл потока={raw_stream_file}'
        )

        self._com_port_reader.configure(session_config)

    def _set_stage(self, stage: ProgramStage) -> None:
        """Переключает устойчивую стадию пользовательского сценария."""
        if self._current_stage is not stage:
            self._current_stage = stage
            self._app_logger.info(f'Стадия программы изменена: {stage.name}')
        self._update_controls()

    def _begin_operation(self, operation: _PendingOperation) -> bool:
        """Синхронно устанавливает маркер ожидания результата операции."""
        if self._pending_operation is not None or self._session_resetting:
            return False
        self._pending_operation = operation
        self._update_controls()
        return True

    def _finish_operation(self, expected_operation: _PendingOperation) -> bool:
        """Снимает маркер только для ожидаемого предметного результата."""
        if self._pending_operation is not expected_operation:
            self._error_handler(
                ComPortReaderException(
                    'Получен результат операции, которая не ожидалась главным окном'
                )
            )
            return False
        self._pending_operation = None
        self._update_controls()
        return True

    def _update_controls(self) -> None:
        """Централизованно вычисляет доступность командных кнопок."""
        controls_available = (
            self._pending_operation is None
            and not self._session_resetting
            and self._close_task is None
        )
        self._apply_settings_button.setEnabled(
            controls_available and self._current_stage is self._setting_stage
        )
        self._start_static_init_button.setEnabled(
            controls_available
            and self._current_stage is self._ready_for_static_init_stage
        )
        self._start_measuring_button.setEnabled(
            controls_available
            and self._current_stage is self._ready_for_measurement_stage
        )
        self._stop_measuring_button.setEnabled(
            controls_available and self._current_stage is self._measuring_stage
        )

    # =============================================================
    # ================= Управление измерениями ====================
    # =============================================================

    def start_static_init(self) -> None:
        """Запрашивает подготовку CSV и запуск статического набора."""
        if not self._begin_operation(_PendingOperation.START_STATIC_INIT):
            return
        try:
            saving_file = self._build_saving_file('static_init')
        except ComPortReaderException as err:
            self._error_handler(err)
            return
        self._app_logger.info(f'Запуск статического набора: {saving_file}')
        self.add_info_message(
            f'Ожидание запуска статического набора для проезда '
            f'#{self._get_passage_num()}'
        )
        self._com_port_reader.start_static_init(saving_file)

    def start_measuring(self) -> None:
        """Запрашивает подготовку CSV и запуск измерений."""
        if not self._begin_operation(_PendingOperation.START_MEASURING):
            return
        try:
            saving_file = self._build_saving_file('measuring')
        except ComPortReaderException as err:
            self._error_handler(err)
            return
        self._app_logger.info(f'Запуск измерений: {saving_file}')
        self.add_info_message(
            f'Ожидание запуска измерений для проезда #{self._get_passage_num()}'
        )
        self._com_port_reader.start_measuring(saving_file)

    def stop_measuring(self) -> None:
        """Запрашивает остановку измерений и закрытие CSV-файла."""
        if not self._begin_operation(_PendingOperation.STOP_MEASURING):
            return
        passage_num = self._get_passage_num()
        self._app_logger.info(f'Остановка измерений для проезда {passage_num}')
        self.add_info_message(
            f'Ожидание завершения измерений для проезда #{passage_num}'
        )
        self._com_port_reader.stop_measuring()

    def _build_saving_file(self, stage_name: str) -> Path:
        """Формирует абсолютный путь CSV для текущего проезда.

        Args:
            stage_name: Имя этапа, включаемое в имя результата.

        Returns:
            Абсолютный путь CSV-файла.

        Raises:
            ComPortReaderException: Параметры сохранения ещё не заданы.
        """
        if self._saving_path is None or self._template_filename is None:
            raise ComPortReaderException('Не заданы параметры сохранения данных')
        return (
            self._saving_path
            / f'{self._template_filename}_{stage_name}_{self._get_passage_num()}.csv'
        ).resolve()

    # =============================================================
    # ================ Высокоуровневые callback'и =================
    # =============================================================

    def _handshake_done(self) -> None:
        """Обрабатывает успешное рукопожатие с МК."""
        if not self._finish_operation(_PendingOperation.CONFIGURE):
            return
        self._app_logger.info('Рукопожатие с МК выполнено успешно')
        self.add_info_message('Рукопожатие с МК выполнено успешно')
        self._set_stage(self._ready_for_static_init_stage)

    def _static_init_started(self) -> None:
        """Обрабатывает подтверждение запуска статического набора."""
        if not self._finish_operation(_PendingOperation.START_STATIC_INIT):
            return
        self._set_stage(self._static_init_stage)
        self.add_info_message(
            f'Статический набор запущен для проезда #{self._get_passage_num()}'
        )

    def _static_init_completed(self) -> None:
        """Обрабатывает самостоятельное завершение статического набора."""
        if self._current_stage is not self._static_init_stage:
            self._error_handler(
                ComPortReaderException(
                    'Завершение статического набора получено в неверной стадии'
                )
            )
            return

        title = 'Статический буфер набран'
        message = 'Набор статического буфера завершён'
        self._app_logger.info(message)
        self.add_info_message(message)
        self._set_stage(self._ready_for_measurement_stage)
        QMessageBox.information(self, title, message)

    def _measuring_started(self) -> None:
        """Обрабатывает подтверждение запуска измерений."""
        if not self._finish_operation(_PendingOperation.START_MEASURING):
            return
        self._set_stage(self._measuring_stage)
        self.add_info_message(
            f'Измерения запущены для проезда #{self._get_passage_num()}'
        )

    def _measuring_stopped(self) -> None:
        """Обрабатывает остановку измерений после закрытия CSV-файла."""
        if not self._finish_operation(_PendingOperation.STOP_MEASURING):
            return
        passage_num = self._get_passage_num()
        self._app_logger.info(f'Измерения завершены для проезда {passage_num}')
        self.add_info_message(f'Измерения завершены для проезда #{passage_num}')
        self._increment_passage_num()
        self._set_stage(self._ready_for_static_init_stage)

    def _data_received(self, package: TelegaData) -> None:
        """Отображает пакет данных, не раскрывая GUI детали IPC."""
        self._data_visualizer.visualize_package(package)

    # =============================================================
    # ============= Обработка ошибок и сброс сессии ===============
    # =============================================================

    def _error_handler(self, error: ComPortReaderException) -> None:
        """Снимает ожидание и обрабатывает recoverable или фатальную ошибку."""
        failed_operation = self._pending_operation
        self._pending_operation = None
        self._update_controls()

        self._app_logger.error(f'Получена ошибка ComPortReader: {error}')
        self.add_error_message('Ошибка выполнения', str(error))
        if not error.fatal_error:
            if failed_operation is _PendingOperation.CONFIGURE:
                self._saving_params.unlock_input()
                self._com_port_settings.unlock_input()
            QMessageBox.warning(self, 'Ошибка выполнения', str(error))
            return

        QMessageBox.critical(self, 'Ошибка выполнения', str(error))
        if self._fatal_recovery_task is None or self._fatal_recovery_task.done():
            self._session_resetting = True
            self._update_controls()
            self._fatal_recovery_task = asyncio.create_task(
                self._recover_from_fatal_error(),
                name='com_port_reader_fatal_recovery',
            )

    async def _recover_from_fatal_error(self) -> None:
        """Штатно освобождает аварийную сессию и возвращает настройки."""
        try:
            await self._com_port_reader.reset()
        except Exception as err:
            self._app_logger.exception(
                f'Не удалось полностью освободить аварийную сессию: {err}'
            )
            self.add_error_message('Ошибка сброса сессии', str(err))
        finally:
            self._session_resetting = False
            self._reset_to_setting_stage()

    def _reset_to_setting_stage(self) -> None:
        """Очищает состояние сценария и возвращает стадию настройки."""
        self._saving_path = None
        self._template_filename = None
        self._pending_operation = None
        self._saving_params.unlock_input()
        self._com_port_settings.unlock_input()
        self._data_visualizer.reset()
        self._set_stage(self._setting_stage)

    # =============================================================
    # ================= Пользовательский журнал ===================
    # =============================================================

    def _add_user_message(self, level: str, message: str) -> None:
        """Добавляет сообщение в пользовательский журнал окна."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self._msg_text_edit.addItem(f'[{timestamp}] {level}:\n{message}')
        while self._msg_text_edit.count() > self._messages_limit:
            self._msg_text_edit.takeItem(0)
        self._msg_text_edit.scrollToBottom()

    def add_info_message(self, message: str) -> None:
        """Добавляет информационное сообщение.

        Args:
            message: Текст сообщения.
        """
        self._add_user_message('Инфо', message)

    def add_warning_message(self, title: str, message: str) -> None:
        """Добавляет предупреждение.

        Args:
            title: Заголовок предупреждения.
            message: Текст предупреждения.
        """
        self._add_user_message('Предупреждение', f'{title}: {message}')

    def add_error_message(self, title: str, message: str) -> None:
        """Добавляет сообщение об ошибке.

        Args:
            title: Заголовок ошибки.
            message: Описание ошибки.
        """
        self._add_user_message('Ошибка', f'{title}: {message}')

    # =============================================================
    # ================ Управление номером проезда =================
    # =============================================================

    def _get_passage_num(self) -> int:
        """Возвращает номер текущего проезда."""
        passage_num = self._passage_num_edit.text().strip()
        if not passage_num:
            return 1
        try:
            return max(1, int(passage_num))
        except ValueError:
            self._app_logger.warning(f'Некорректный номер проезда: {passage_num}')
            self.add_warning_message(
                'Некорректный номер проезда',
                f'Некорректный номер {passage_num}; установлен номер 1',
            )
            self._set_passage_num(1)
            return 1

    def _set_passage_num(self, passage_num: int) -> None:
        """Задаёт номер текущего проезда."""
        self._passage_num_edit.setText(str(max(1, passage_num)))

    def _increment_passage_num(self) -> None:
        """Увеличивает номер текущего проезда."""
        next_passage_num = self._get_passage_num() + 1
        self._set_passage_num(next_passage_num)
        self._app_logger.info(f'Номер текущего проезда изменён: {next_passage_num}')
        self.add_info_message(f'Текущий проезд: #{next_passage_num}')
