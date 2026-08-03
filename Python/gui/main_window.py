"""Главное окно приложения путеизмерительной тележки."""

# System imports
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# External imports
from PyQt5.QtWidgets import (
    QMainWindow, QToolButton,
    QPushButton, QApplication, QMessageBox,
    QComboBox, QLineEdit, QLCDNumber,
    QCheckBox, QListWidget
)
from PyQt5.uic import loadUi
from PyQt5.QtGui import QCloseEvent, QIcon, QIntValidator

# User imports
from logger import AppLogger
from app_config import AppConfig, config_path
from gui.saving_params import SavingParams
from gui.com_port_settings import ComPortSettings
from gui.com_port_reader import ComPortReader, ComPortReaderException
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
from telega_session import TelegaData

##########################################################

class MainWindow(QMainWindow):
    """Координирует интерфейс и пользовательские стадии работы приложения."""

    # Пути к ресурсам и ограничения интерфейса
    _main_window_path: Path = Path(__file__).parent / "ui" / "main_window.ui"
    _app_icon_path: Path = Path(__file__).parent / "ui" / "telega.png"
    _messages_limit: int = 500

    # Конфигурация и журналирование приложения
    _app_logger: logging.Logger
    _app_config: AppConfig

    # Стадии пользовательского сценария
    _setting_stage: SettingStage
    _ready_for_static_init_stage: ReadyForStaticInitStage
    _static_init_stage: StaticInitStage
    _ready_for_measurement_stage: ReadyForMeasurementStage
    _measuring_stage: MeasuringStage
    _current_stage: ProgramStage

    # Изменяемое состояние текущей сессии
    _saving_path: Optional[Path]
    _template_filename: Optional[str]
    _pending_saving_stage: Optional[str]
    _pending_saving_file: Optional[Path]
    _measurement_stop_requested: bool
    _session_configuration_started: bool

    # Виджеты главного окна
    _apply_settings_button: QPushButton
    _start_static_init_button: QPushButton
    _start_measuring_button: QPushButton
    _stop_measuring_button: QPushButton
    _msg_text_edit: QListWidget
    _passage_num_edit: QLineEdit
    _indicator_check_box: QCheckBox

    # Компоненты интерфейса и взаимодействия с сессией
    _saving_params: SavingParams
    _com_port_settings: ComPortSettings
    _com_port_reader: ComPortReader
    _data_visualizer: DataVisualizer
    _indicator_blinker: IndicatorBlinker

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
        self._app_config = AppConfig.load(config_path)
        self._app_config.logger_config.log_filename = "app_logger.log"
        self._app_config.logger_config.log_level = logging.DEBUG
        self._app_config.logger_config.use_console = False
        self._app_logger = AppLogger(self._app_config).get_child_logger("MainWindow")

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
        """Задаёт начальные значения изменяемого состояния окна."""
        self._saving_path = None
        self._template_filename = None
        self._pending_saving_stage = None
        self._pending_saving_file = None
        self._measurement_stop_requested = False
        self._session_configuration_started = False

    def _create_components(self) -> None:
        """Создаёт компоненты интерфейса и взаимодействия с сессией."""
        self._saving_params = SavingParams(
            app_config=self._app_config,
            saving_path_edit=self.findChild(QLineEdit, "SavingPathEdit"),
            choose_saving_path_button=self.findChild(
                QToolButton,
                "ChooseSavingPathButton",
            ),
            template_filename_edit=self.findChild(QLineEdit, "TemplateFilenameEdit"),
            template_info_button=self.findChild(QPushButton, "TemplateInfoButton"),
        )
        self._com_port_settings = ComPortSettings(
            app_config=self._app_config,
            com_port_combo_box=self.findChild(QComboBox, "ComPortComboBox"),
            com_port_info_button=self.findChild(QPushButton, "ComPortInfoButton"),
            update_com_ports_button=self.findChild(QToolButton, "UpdateComPortsButton"),
        )
        self._com_port_reader = ComPortReader(self._app_logger)
        self._data_visualizer = DataVisualizer(
            value_acc_x=self.findChild(QLCDNumber, "Value_Acc_X"),
            value_acc_y=self.findChild(QLCDNumber, "Value_Acc_Y"),
            value_acc_z=self.findChild(QLCDNumber, "Value_Acc_Z"),
            value_gyro_x=self.findChild(QLCDNumber, "Value_Gyro_X"),
            value_gyro_y=self.findChild(QLCDNumber, "Value_Gyro_Y"),
            value_gyro_z=self.findChild(QLCDNumber, "Value_Gyro_Z"),
            dpp_code_value=self.findChild(QLCDNumber, "DppCodeValue"),
        )
        self._indicator_blinker = IndicatorBlinker(
            indicator=self._indicator_check_box,
            period_ms=1000,
            logger=self._app_logger,
        )

    def _create_program_stages(self) -> None:
        """Создаёт стадии пользовательского сценария программы."""
        self._setting_stage = SettingStage(self)
        self._ready_for_static_init_stage = ReadyForStaticInitStage(self)
        self._static_init_stage = StaticInitStage(self)
        self._ready_for_measurement_stage = ReadyForMeasurementStage(self)
        self._measuring_stage = MeasuringStage(self)
        self._current_stage = self._setting_stage

    def _configure_controls(self) -> None:
        """Задаёт начальные параметры элементов управления."""
        self._passage_num_edit.setValidator(QIntValidator(1, 999999, self))
        self._passage_num_edit.setReadOnly(True)
        self._set_passage_num(1)

    def _connect_signals(self) -> None:
        """Подключает сигналы интерфейса, сессии и приложения."""
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

        self._com_port_reader.data_received.connect(self._data_received)
        self._com_port_reader.handshake_done.connect(self._handshake_done)
        self._com_port_reader.handshake_failed.connect(self._handshake_failed)
        self._com_port_reader.connection_failed.connect(self._connection_failed)
        self._com_port_reader.saving_file_result.connect(self._saving_file_result)
        self._com_port_reader.static_init_done.connect(self._static_init_done)
        self._com_port_reader.measuring_stopped.connect(self._measuring_stopped)
        self._com_port_reader.error_occurred.connect(self._error_handler)
        self._com_port_reader.finished.connect(self._com_port_reader_finished)

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
        """Завершает фоновые компоненты перед закрытием окна.

        Args:
            event: Событие закрытия главного окна.
        """
        self.hide()
        try:
            self._indicator_blinker.stop()
            self._shutdown_com_port_reader()
            self._app_logger.info('Корректное завершение работы приложения')
        except Exception as err:
            self._app_logger.exception(f'Ошибка при завершении работы ComPortReader: {err}')
        finally:
            event.accept()

    # =============================================================
    # ================ Настройка и стадии сессии ==================
    # =============================================================

    def configure_session(self,
                          saving_path: Path,
                          template_filename: str,
                          com_port_name: str) -> None:
        """Применяет настройки и запускает сессию связи с МК.

        Args:
            saving_path: Директория сохранения данных.
            template_filename: Шаблон имени файлов текущей сессии.
            com_port_name: Имя используемого COM-порта.

        Raises:
            ComPortReaderException: Не удалось запустить сессию связи.
            OSError: Не удалось сохранить настройки приложения.
            TypeError: Переданы параметры неподдерживаемого типа.
        """
        bin_file = saving_path / f'{template_filename}.bin'
        self._app_logger.info(
            f'Применение настроек: COM-порт={com_port_name}, файл потока={bin_file}'
        )
        self._com_port_reader.configure(
            logger_config=self._app_config.logger_config,
            com_port_name=com_port_name,
            bin_file=bin_file,
        )
        try:
            self._saving_path = saving_path
            self._template_filename = template_filename
            self._set_passage_num(1)
            self._saving_params.save_config()
            self._com_port_settings.save_config()
            self.add_info_message('Ожидание рукопожатия с МК')
        except Exception:
            self._saving_path = None
            self._template_filename = None
            self._shutdown_com_port_reader()
            raise

    def _set_stage(self, stage: ProgramStage) -> None:
        """ Переключает текущую стадию программы. """
        if self._current_stage is stage:
            return

        self._current_stage = stage
        self._app_logger.info(f'Стадия программы изменена: {stage.name}')

    # =============================================================
    # ================= Пользовательский журнал ===================
    # =============================================================

    def _add_user_message(self, level: str, message: str) -> None:
        """ Добавляет сообщение в пользовательский журнал главного окна. """
        timestamp = datetime.now().strftime('%H:%M:%S')
        self._msg_text_edit.addItem(f'[{timestamp}] {level}:\n{message}')
        while self._msg_text_edit.count() > self._messages_limit:
            self._msg_text_edit.takeItem(0)
        self._msg_text_edit.scrollToBottom()

    def add_info_message(self, message: str) -> None:
        """Добавляет информационное сообщение в пользовательский журнал.

        Args:
            message: Текст сообщения.
        """
        self._add_user_message('Инфо', message)

    def add_warning_message(self, title: str, message: str) -> None:
        """Добавляет предупреждение в пользовательский журнал.

        Args:
            title: Заголовок предупреждения.
            message: Текст предупреждения.
        """
        self._add_user_message('Предупреждение', f'{title}: {message}')

    def add_error_message(self, title: str, message: str) -> None:
        """Добавляет сообщение об ошибке в пользовательский журнал.

        Args:
            title: Заголовок ошибки.
            message: Описание ошибки.
        """
        self._add_user_message('Ошибка', f'{title}: {message}')

    # =============================================================
    # ================= Управление измерениями ====================
    # =============================================================

    def start_static_init(self) -> None:
        """Запрашивает подготовку CSV-файла для набора статического буфера."""
        try:
            self._request_saving_file('static_init')
        except (ComPortReaderException, OSError, TypeError, ValueError) as err:
            self.add_error_message('Ошибка подготовки статического буфера', f'{err}')
            QMessageBox.warning(self, 'Ошибка подготовки статического буфера', f'{err}')

    def start_measuring(self) -> None:
        """Запрашивает подготовку CSV-файла для измерительного проезда."""
        try:
            self._request_saving_file('measuring')
        except (ComPortReaderException, OSError, TypeError, ValueError) as err:
            self.add_error_message('Ошибка подготовки измерений', f'{err}')
            QMessageBox.warning(self, 'Ошибка подготовки измерений', f'{err}')

    def stop_measuring(self) -> None:
        """Запрашивает завершение сбора данных во время проезда."""
        if self._measurement_stop_requested:
            return

        try:
            passage_num = self._get_passage_num()
            self._app_logger.info(f'Завершение измерений для проезда {passage_num}')
            self._com_port_reader.stop_measuring()
            self._measurement_stop_requested = True
            self.add_info_message(f'Ожидание завершения измерений для проезда #{passage_num}')
        except ComPortReaderException as err:
            self.add_error_message('Ошибка завершения сбора данных', f'{err}')
            QMessageBox.warning(self, 'Ошибка завершения сбора данных', f'{err}')

    def _request_saving_file(self, stage_name: str) -> None:
        """Запрашивает подготовку CSV-файла и запоминает ожидающий запуска этап.

        Этап запускается только после успешного получения результата
        SET_SAVING_FILE, поэтому его имя сохраняется до обработки ответа.

        Args:
            stage_name: Имя этапа для формирования имени файла и последующего запуска.

        Raises:
            ComPortReaderException: Если параметры сохранения не заданы или
                предыдущая команда SET_SAVING_FILE ещё не завершилась.
        """
        if self._saving_path is None or self._template_filename is None:
            raise ComPortReaderException('Не заданы параметры сохранения данных')
        if self._pending_saving_stage is not None:
            raise ComPortReaderException('Ожидается результат предыдущей команды SET_SAVING_FILE')

        file_path = (
            self._saving_path
            / f'{self._template_filename}_{stage_name}_{self._get_passage_num()}.csv'
        ).resolve()

        self._pending_saving_stage = stage_name
        self._pending_saving_file = file_path
        self._app_logger.info(f'Запрошена подготовка CSV-файла: {file_path}')
        self._com_port_reader.set_saving_file(file_path)

    # =============================================================
    # ============= Обработка ошибок и сброс сессии ===============
    # =============================================================

    def _handle_session_failure(self,
                                title: str,
                                message: str,
                                log_message: Optional[str] = None,
                                dialog_title: Optional[str] = None) -> None:
        """Завершает аварийную сессию и сообщает пользователю об ошибке.

        Args:
            title: Заголовок сообщения в пользовательском журнале.
            message: Описание ошибки для журнала и диалога.
            log_message: Отдельный текст для журнала приложения.
            dialog_title: Отдельный заголовок диалога ошибки.
        """
        self._app_logger.error(log_message or message)
        self.add_error_message(title, message)
        self._shutdown_com_port_reader()
        self._reset_to_setting_stage()
        QMessageBox.critical(self, dialog_title or title, message)

    def _error_handler(self, error_info: str) -> None:
        """ Обработка аварийной ошибки текущей сессии. """
        self._handle_session_failure(
            title='Ошибка выполнения',
            message=error_info,
            log_message=f'Получена ошибка {error_info}',
            dialog_title='Ошибка выполнения!',
        )

    def _reset_to_setting_stage(self) -> None:
        """ Возвращает главное окно к стадии настройки параметров. """
        self._com_port_settings.unlock_input()
        self._saving_params.unlock_input()
        self._apply_settings_button.setEnabled(True)
        self._saving_path = None
        self._template_filename = None
        self._pending_saving_stage = None
        self._pending_saving_file = None
        self._measurement_stop_requested = False
        self._session_configuration_started = False
        self._data_visualizer.reset()
        self._set_stage(self._setting_stage)

    def _shutdown_com_port_reader(self) -> None:
        """Завершает текущую сессию ComPortReader.

        Raises:
            ComPortReaderException: Не удалось полностью освободить ресурсы сессии.
        """
        self._app_logger.info('Завершение текущей сессии ComPortReader')
        self._com_port_reader.shutdown()

    # =============================================================
    # ================ Обработка сигналов сессии ==================
    # =============================================================

    def _data_received(self, package: TelegaData) -> None:
        """Отображает последний пакет, полученный от дочерней сессии."""
        self._data_visualizer.visualize_package(package)

    def _saving_file_result(self, success: bool, filepath: str, error_info: str) -> None:
        """Обрабатывает результат подготовки CSV-файла в дочерней сессии."""
        stage_name = self._pending_saving_stage
        expected_file_path = self._pending_saving_file
        self._pending_saving_stage = None
        self._pending_saving_file = None

        if stage_name is None or expected_file_path is None:
            self._app_logger.warning(f'Получен неожиданный результат SET_SAVING_FILE: {filepath}')
            return
        if filepath != str(expected_file_path):
            self._app_logger.warning(
                f'Получен результат SET_SAVING_FILE для другого файла: {filepath}'
            )
            return
        if not success:
            message = error_info or f'Не удалось подготовить CSV-файл {filepath}'
            self._app_logger.error(message)
            self.add_error_message('Ошибка подготовки CSV-файла', message)
            QMessageBox.warning(self, 'Ошибка подготовки CSV-файла', message)
            return

        try:
            if stage_name == 'static_init':
                self._app_logger.info(
                    f'Запуск набора статического буфера для проезда {self._get_passage_num()}'
                )
                self._com_port_reader.start_static_init()
                self._set_stage(self._static_init_stage)
                self.add_info_message(
                    f'Набор статического буфера запущен для проезда #{self._get_passage_num()}'
                )
                return

            if stage_name == 'measuring':
                self._app_logger.info(f'Запуск измерений для проезда {self._get_passage_num()}')
                self._com_port_reader.start_measuring()
                self._set_stage(self._measuring_stage)
                self.add_info_message(f'Измерения запущены для проезда #{self._get_passage_num()}')
                return

            raise RuntimeError(f'Неизвестный этап подготовки CSV-файла: {stage_name}')
        except ComPortReaderException as err:
            self._error_handler(f'Не удалось запустить этап после подготовки CSV-файла: {err}')

    def _static_init_done(self) -> None:
        """ Обработка завершения набора статического буфера. """
        title = 'Статический буфер набран'
        message = 'Набор статического буфера завершён'
        self._app_logger.info(message)
        self.add_info_message(message)
        self._set_stage(self._ready_for_measurement_stage)
        QMessageBox.information(self, title, message)

    def _measuring_stopped(self) -> None:
        """Обрабатывает завершение измерения после закрытия CSV-файла."""
        passage_num = self._get_passage_num()
        self._measurement_stop_requested = False
        self._app_logger.info(f'Измерения завершены для проезда {passage_num}')
        self.add_info_message(f'Измерения завершены для проезда #{passage_num}')
        self._increment_passage_num()
        self._set_stage(self._ready_for_static_init_stage)

    def _handshake_done(self) -> None:
        """ Обработка успешного рукопожатия с МК. """
        self._app_logger.info('Рукопожатие с МК выполнено успешно')
        self.add_info_message('Рукопожатие с МК выполнено успешно')
        self._set_stage(self._ready_for_static_init_stage)

    def _handshake_failed(self) -> None:
        """ Обработка ошибки рукопожатия с МК. """
        self._handle_session_failure(
            title='Ошибка подключения',
            message='Не удалось выполнить рукопожатие с МК',
            log_message='Ошибка рукопожатия с МК',
        )

    def _connection_failed(self, error_info: str) -> None:
        """ Обработка ошибки запуска подключения к МК. """
        title = 'Ошибка подключения'
        message = f'Не удалось подключиться к COM-порту:\n{error_info}'
        self._handle_session_failure(title=title, message=message)

    def _com_port_reader_finished(self) -> None:
        """ Обработка завершения работы ComPortReader. """
        self._app_logger.info('ComPortReader завершил работу')

    # =============================================================
    # ================ Управление номером проезда =================
    # =============================================================

    def _get_passage_num(self) -> int:
        """ Возвращает номер текущего проезда. """
        passage_num = self._passage_num_edit.text().strip()
        if not passage_num:
            return 1
        try:
            return max(1, int(passage_num))
        except ValueError:
            self._app_logger.warning(f'Некорректный номер проезда: {passage_num}')
            self.add_warning_message(
                'Некорректный номер проезда',
                f'Некорректный номер проезда {passage_num}; установлен номер 1'
            )
            self._set_passage_num(1)
            return 1

    def _set_passage_num(self, passage_num: int) -> None:
        """ Задаёт номер текущего проезда. """
        self._passage_num_edit.setText(str(max(1, passage_num)))

    def _increment_passage_num(self) -> None:
        """ Увеличивает номер текущего проезда. """
        next_passage_num = self._get_passage_num() + 1
        self._set_passage_num(next_passage_num)
        self._app_logger.info(f'Номер текущего проезда изменён: {next_passage_num}')
        self.add_info_message(f'Текущий проезд: #{next_passage_num}')
