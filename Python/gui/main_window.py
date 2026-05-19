# System imports
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# External imports
from abc import ABC, abstractmethod
from PyQt5.QtWidgets import (
    QMainWindow, QToolButton,
    QPushButton, QApplication, QMessageBox,
    QComboBox, QLineEdit, QLCDNumber,
    QCheckBox, QListWidget
)
from PyQt5.uic import loadUi
from PyQt5.QtGui import QIcon, QIntValidator

# User imports
from logger import AppLogger
from app_config import AppConfig, config_path
from gui.saving_params import SavingParams, InvalidPathError, InvalidTemplateFilenameError
from gui.com_port_settings import ComPortSettings, ComPortSettingsError
from gui.com_port_reader import ComPortReader, ComPortReaderException
from gui.data_storage import DataStorage
from gui.data_visualization import DataVisualizer
from gui.indicator_blinker import IndicatorBlinker
from telega_session import TelegaData

##########################################################

class ProgramStage(ABC):
    """
    Класс для описания логики отработки нажатия кнопок пользователем
    при различных стадиях программы.
    Реализует паттерн "Состояние" (State)
    """
    name: str = 'неизвестная стадия'

    def __init__(self, main_window: 'MainWindow'):
        self._main_window = main_window

    def _show_warning(self, title: str, message: str) -> None:
        """ Показывает пользователю предупреждение текущей стадии. """
        self._main_window._add_warning_message(title, message)
        QMessageBox.warning(self._main_window, title, message)

    def _show_settings_locked_warning(self) -> None:
        """ Предупреждает о запрете изменения настроек после запуска работы. """
        self._show_warning(
            'Ошибка изменения параметров сохранения',
            'Параметры сохранения и настройки com порта '
            'не могут быть изменены во время работы программы'
        )

    @abstractmethod
    def apply_settings(self) -> None:
        """ Сохранение настроек com порта и параметров сохранения """
        ...

    @abstractmethod
    def start_calibration(self) -> None:
        """ Запуск калибровки датчиков """
        ...

    @abstractmethod
    def start_static_init(self) -> None:
        """ Запуск сбора статического буфера """
        ...

    @abstractmethod
    def start_measuring(self) -> None:
        """ Запуск сбора данных """
        ...

    @abstractmethod
    def stop_measuring(self) -> None:
        """ Завершение сбора данных """
        ...

# =============================================================

class MainWindow(QMainWindow):
    _main_window_path: Path = Path(__file__).parent / "ui" / "main_window.ui"
    _app_icon_path: Path = Path(__file__).parent / "ui" / "telega.png"
    _messages_limit: int = 500
    _app_logger: logging.Logger
    _app_config: AppConfig

    # =============================================================
    # ===================== Внутренние классы =====================
    # ============== для описания состояний программы =============
    # =============================================================

    class SettingStage(ProgramStage):
        """ Ожидание настроек сохранения и параметров порта """
        name = 'ожидание подтверждения настроек'

        def apply_settings(self) -> None:
            """ Сохранение настроек com порта и параметров сохранения """
            if self._main_window._session_configuration_started:
                self._show_warning(
                    'Настройка уже запущена',
                    'Настройка подключения уже выполняется. Дождитесь результата рукопожатия с МК'
                )
                return

            try:
                saving_path = self._main_window._saving_params.get_saving_path()
                template_filename = self._main_window._saving_params.get_template_filename()
                com_port_name = self._main_window._com_port_settings.get_port_name()

                # Применим полученные параметры и заблокируем их изменение
                self._main_window._session_configuration_started = True
                self._main_window._add_info_message(
                    f'Настройки применены:\n'
                    f'COM-порт: {com_port_name}\n'
                    f'Шаблонное название файлов: {template_filename}\n'
                    f'Директория сохранения: {saving_path.resolve()}'
                )
                self._main_window._configure_session(saving_path, template_filename, com_port_name)
                self._main_window._saving_params.lock_input()
                self._main_window._com_port_settings.lock_input()
                self._main_window._apply_settings_button.setEnabled(False)

            except (InvalidPathError, InvalidTemplateFilenameError,
                    ComPortSettingsError, ComPortReaderException, OSError, TypeError) as err:
                self._main_window._session_configuration_started = False
                self._main_window._shutdown_com_port_reader()
                self._main_window._add_error_message('Ошибка задания параметров', f'{err}')
                QMessageBox.critical(self._main_window, 'Ошибка задания параметров!', f'{err}')

        def start_calibration(self) -> None:
            """ Запуск калибровки датчиков """
            self._show_warning(
                'Ошибка начала калибровки',
                'Для начала задайте настройки com порта и параметры сохранения'
            )

        def start_static_init(self) -> None:
            """ Запуск сбора статического буфера """
            self._show_warning(
                'Ошибка начала набора статического буфера',
                'Для начала задайте настройки com порта и параметры сохранения'
            )

        def start_measuring(self) -> None:
            """ Запуск сбора данных """
            self._show_warning(
                'Ошибка начала сбора данных',
                'Для начала задайте настройки com порта и параметры сохранения'
            )

        def stop_measuring(self) -> None:
            """ Завершение сбора данных """
            self._show_warning(
                'Ошибка завершения сбора данных',
                'Измерения ещё не запущены'
            )

    # -------------------------------------------------------------

    class CalibrationState(ProgramStage):
        """ Ожидание выполнения калибровки датчиков. """
        name = 'ожидание выполнения калибровки'

        def apply_settings(self) -> None:
            """ Сохранение настроек com порта и параметров сохранения """
            self._show_settings_locked_warning()

        def start_calibration(self) -> None:
            """ Запуск калибровки датчиков """
            self._main_window._start_calibration()

        def start_static_init(self) -> None:
            """ Запуск сбора статического буфера """
            self._show_warning(
                'Ошибка начала набора статического буфера',
                'Необходимо провести калибровку датчиков'
            )

        def start_measuring(self) -> None:
            """ Запуск сбора данных """
            self._show_warning(
                'Ошибка начала сбора данных',
                'Необходимо провести калибровку датчиков'
            )

        def stop_measuring(self) -> None:
            """ Завершение сбора данных """
            self._show_warning(
                'Ошибка завершения сбора данных',
                'Измерения ещё не запущены'
            )

    # -------------------------------------------------------------

    class ReadyForStaticInitState(ProgramStage):
        """ Готовность начать набор статического буфера. """
        name = 'готовность начать набор статического буфера'

        def apply_settings(self) -> None:
            """ Сохранение настроек com порта и параметров сохранения """
            self._show_settings_locked_warning()

        def start_calibration(self) -> None:
            """ Запуск калибровки датчиков """
            title = 'Повторная калибровка датчиков'
            message = (
                'Повторная калибровка сбросит текущий цикл подготовки к измерениям. '
                'После неё потребуется заново набрать статический буфер. Продолжить?'
            )
            self._main_window._add_warning_message(title, message)
            answer = QMessageBox.warning(
                self._main_window,
                title,
                message,
                QMessageBox.Ok | QMessageBox.Cancel,
                QMessageBox.Cancel
            )
            if answer == QMessageBox.Ok:
                self._main_window._add_info_message('Повторный запуск калибровки')
                self._main_window._start_calibration()

        def start_static_init(self) -> None:
            """ Запуск сбора статического буфера """
            self._main_window._start_static_init()

        def start_measuring(self) -> None:
            """ Запуск сбора данных """
            self._show_warning(
                'Ошибка начала сбора данных',
                'Необходимо завершить набор статического буфера'
            )

        def stop_measuring(self) -> None:
            """ Завершение сбора данных """
            self._show_warning(
                'Ошибка завершения сбора данных',
                'Измерения ещё не запущены'
            )

    # -------------------------------------------------------------

    class StaticInitState(ProgramStage):
        """ Набор статического буфера уже начат. """
        name = 'набор статического буфера уже начат'

        def apply_settings(self) -> None:
            """ Сохранение настроек com порта и параметров сохранения """
            self._show_settings_locked_warning()

        def start_calibration(self) -> None:
            """ Запуск калибровки датчиков """
            self._show_warning(
                'Ошибка начала калибровки',
                'Нельзя запускать калибровку во время набора статического буфера'
            )

        def start_static_init(self) -> None:
            """ Запуск сбора статического буфера """
            self._show_warning(
                'Ошибка начала набора статического буфера',
                'Набор статического буфера уже запущен'
            )

        def start_measuring(self) -> None:
            """ Запуск сбора данных """
            self._show_warning(
                'Ошибка начала сбора данных',
                'Необходимо завершить набор статического буфера'
            )

        def stop_measuring(self) -> None:
            """ Завершение сбора данных """
            self._show_warning(
                'Ошибка завершения сбора данных',
                'Измерения ещё не запущены'
            )

    # -------------------------------------------------------------

    class ReadyForMeasurementState(ProgramStage):
        """ Готовность начать измерение. """
        name = 'готовность начать измерение'

        def apply_settings(self) -> None:
            """ Сохранение настроек com порта и параметров сохранения """
            self._show_settings_locked_warning()

        def start_calibration(self) -> None:
            """ Запуск калибровки датчиков """
            self._show_warning(
                'Ошибка начала калибровки',
                'Нельзя запускать калибровку между набором статического буфера и началом измерений'
            )

        def start_static_init(self) -> None:
            """ Запуск сбора статического буфера """
            self._show_warning(
                'Ошибка начала набора статического буфера',
                'Статический буфер уже набран. Начните измерения или завершите текущий цикл'
            )

        def start_measuring(self) -> None:
            """ Запуск сбора данных """
            self._main_window._start_measuring()

        def stop_measuring(self) -> None:
            """ Завершение сбора данных """
            self._show_warning(
                'Ошибка завершения сбора данных',
                'Измерения ещё не запущены'
            )

    # -------------------------------------------------------------

    class MeasuringState(ProgramStage):
        """ Измерения уже начаты. """
        name = 'измерения уже начаты'

        def apply_settings(self) -> None:
            """ Сохранение настроек com порта и параметров сохранения """
            self._show_settings_locked_warning()

        def start_calibration(self) -> None:
            """ Запуск калибровки датчиков """
            self._show_warning(
                'Ошибка начала калибровки',
                'Нельзя запускать калибровку во время измерений'
            )

        def start_static_init(self) -> None:
            """ Запуск сбора статического буфера """
            self._show_warning(
                'Ошибка начала набора статического буфера',
                'Нельзя запускать набор статического буфера во время измерений'
            )

        def start_measuring(self) -> None:
            """ Запуск сбора данных """
            self._show_warning(
                'Ошибка начала сбора данных',
                'Измерения уже запущены'
            )

        def stop_measuring(self) -> None:
            """ Завершение сбора данных """
            self._main_window._stop_measuring()

    # =============================================================

    def __init__(self):
        super().__init__(parent=None)

        # Создадим конфигурацию приложения
        self._app_config = AppConfig.load(config_path)
        self._app_config.logger_config.log_filename = "app_logger.log"
        self._app_config.logger_config.log_level = logging.DEBUG

        # Зададим логгер приложения
        self._app_logger = AppLogger(self._app_config).get_child_logger("MainWindow")

        # Загрузим разметку страницы
        loadUi(self._main_window_path, self)

        # Зададим название окна и иконку
        self.setWindowTitle('Путеизмерительная тележка')
        self.setWindowIcon(QIcon(str(self._app_icon_path)))

        # Зададим стадии программы
        self._setting_stage: MainWindow.SettingStage = self.SettingStage(self)
        self._calibration_stage: MainWindow.CalibrationState = self.CalibrationState(self)
        self._ready_for_static_init_stage: MainWindow.ReadyForStaticInitState = self.ReadyForStaticInitState(self)
        self._static_init_stage: MainWindow.StaticInitState = self.StaticInitState(self)
        self._ready_for_measuring_stage: MainWindow.ReadyForMeasurementState = self.ReadyForMeasurementState(self)
        self._measuring_stage: MainWindow.MeasuringState = self.MeasuringState(self)

        self._current_stage: ProgramStage = self._setting_stage
        self._saving_path: Optional[Path] = None
        self._template_filename: Optional[str] = None
        self._session_configuration_started: bool = False
        self._indicator_blinker: Optional[IndicatorBlinker] = None

        # ------------------------------
        # Кнопка сохранения настроек com порта и параметров сохранения
        self._apply_settings_button: QPushButton = self.findChild(QPushButton, "ApplySettingsButton")

        # Кнопки управления измерениями
        self._start_calibration_button: QPushButton = self.findChild(QPushButton, "StartCalibrationButton")
        self._start_static_init_button: QPushButton = self.findChild(QPushButton, "StartStaticInitButton")
        self._start_measuring_button: QPushButton = self.findChild(QPushButton, "StartMeasuringButton")
        self._stop_measuring_button:  QPushButton = self.findChild(QPushButton, "StopMeasuringButton")
        # ------------------------------
        self._msg_text_edit: QListWidget = self.findChild(QListWidget, "MessagesTextEdit")
        self._passage_num_edit: QLineEdit = self.findChild(QLineEdit, "Passage_Num")
        self._indicator_check_box: QCheckBox = self.findChild(QCheckBox, "Indicator")
        # ------------------------------
        self._saving_params = SavingParams(
            app_config=self._app_config,
            saving_path_edit = self.findChild(QLineEdit, "SavingPathEdit"),
            choose_saving_path_button = self.findChild(QToolButton, "ChooseSavingPathButton"),
            template_filename_edit = self.findChild(QLineEdit, "TemplateFilenameEdit"),
            template_info_button = self.findChild(QPushButton, "TemplateInfoButton")
        )
        # ------------------------------
        self._com_port_settings = ComPortSettings(
            app_config=self._app_config,
            com_port_combo_box = self.findChild(QComboBox, "ComPortComboBox"),
            com_port_info_button = self.findChild(QPushButton, "ComPortInfoButton"),
            update_com_ports_button = self.findChild(QToolButton, "UpdateComPortsButton")
        )
        # ------------------------------
        self._com_port_reader: ComPortReader = ComPortReader(self._app_logger)
        # ------------------------------
        self._data_storage = DataStorage()
        # ------------------------------
        self._data_visualizer = DataVisualizer(
            value_acc_x=self.findChild(QLCDNumber, "Value_Acc_X"),
            value_acc_y=self.findChild(QLCDNumber, "Value_Acc_Y"),
            value_acc_z=self.findChild(QLCDNumber, "Value_Acc_Z"),
            value_gyro_x=self.findChild(QLCDNumber, "Value_Gyro_X"),
            value_gyro_y=self.findChild(QLCDNumber, "Value_Gyro_Y"),
            value_gyro_z=self.findChild(QLCDNumber, "Value_Gyro_Z"),
            dpp_code_value=self.findChild(QLCDNumber, "DppCodeValue")
        )
        # ------------------------------
        # Настроим интерфейс
        if not self._check_UI():
            self._app_logger.error("Неправильно настроен main_window!")
            QMessageBox.critical(self, "Ошибка", "Неправильно настроен main_window")
            QApplication.quit()
            exit(10)

        self._init_UI()
        # ------------------------------

    def closeEvent(self, event)-> None:
        """ Дополнительная логика перед закрытием окна """
        self.hide()
        try:
            if self._indicator_blinker is not None:
                self._indicator_blinker.stop()
            self._shutdown_com_port_reader()
            self._app_logger.info('Корректное завершение работы приложения')
        except Exception as err:
            self._app_logger.exception(f'Ошибка при завершении работы ComPortReader: {err}')
        finally:
            event.accept()

    def _quit_app(self) -> None:
        """ Метод для завершения работы программы """
        if not self._com_port_reader.is_active:
            self._app_logger.info('Корректное завершение работы приложения')
        else:
            self._app_logger.warning('Принудительное завершение приложения до полной остановки ComPortReader')
        QApplication.quit()

    def _init_UI(self) -> None:
        # Подключим нажатие кнопок и другие сигналы к соответствующим функциям-обработчикам
        self._start_calibration_button.clicked.connect(lambda: self._current_stage.start_calibration())
        self._start_static_init_button.clicked.connect(lambda: self._current_stage.start_static_init())
        self._start_measuring_button.clicked.connect(lambda: self._current_stage.start_measuring())
        self._stop_measuring_button.clicked.connect(lambda: self._current_stage.stop_measuring())
        self._apply_settings_button.clicked.connect(lambda: self._current_stage.apply_settings())

        self._com_port_reader.data_received.connect(self._data_received)
        self._com_port_reader.handshake_done.connect(self._handshake_done)
        self._com_port_reader.handshake_failed.connect(self._handshake_failed)
        self._com_port_reader.connection_failed.connect(self._connection_failed)
        self._com_port_reader.calibration_done.connect(self._calibration_done)
        self._com_port_reader.static_init_done.connect(self._static_init_done)
        self._com_port_reader.error_occurred.connect(self._error_handler)
        self._com_port_reader.finished.connect(self._com_port_reader_finished)

        self._passage_num_edit.setValidator(QIntValidator(1, 999999, self))
        self._passage_num_edit.setReadOnly(True)
        self._set_passage_num(1)
        self._indicator_blinker = IndicatorBlinker(
            indicator=self._indicator_check_box,
            period_ms=1000,
            logger=self._app_logger,
        )
        self._indicator_blinker.start()

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._indicator_blinker.stop)

    def _check_UI(self) -> bool:
        return (isinstance(self._start_measuring_button, QPushButton) and
                isinstance(self._stop_measuring_button, QPushButton) and
                isinstance(self._start_calibration_button, QPushButton) and
                isinstance(self._start_static_init_button, QPushButton) and
                isinstance(self._apply_settings_button, QPushButton) and
                isinstance(self._msg_text_edit, QListWidget) and
                isinstance(self._passage_num_edit, QLineEdit) and
                isinstance(self._indicator_check_box, QCheckBox))

    def reset(self) -> None:
        """ Сброс состояния главного окна """
        self._shutdown_com_port_reader()
        self._com_port_settings.reset()
        self._set_passage_num(1)
        self._reset_to_setting_stage()
        self._add_info_message('Состояние главного окна сброшено')

    # =============================================================
    # =================== Внутренняя логика =======================
    # =============================================================

    def _configure_session(self,
                           saving_path: Path,
                           template_filename: str,
                           com_port_name: str) -> None:
        bin_file = saving_path / f'{template_filename}.bin'
        self._app_logger.info(
            f'Применение настроек: COM-порт={com_port_name}, файл потока={bin_file}'
        )
        self._com_port_reader.configure(
            logger_config=self._app_config.logger_config,
            com_port_name=com_port_name,
            bin_file=bin_file,
        )
        self._saving_path = saving_path
        self._template_filename = template_filename
        self._set_passage_num(1)
        self._saving_params.save_config()
        self._com_port_settings.save_config()
        self._add_info_message('Ожидание рукопожатия с МК')

    def _set_stage(self, stage: ProgramStage) -> None:
        """ Переключает текущую стадию программы. """
        if self._current_stage is stage:
            return

        self._current_stage = stage
        self._app_logger.info(f'Стадия программы изменена: {stage.name}')

    def _add_user_message(self, level: str, message: str) -> None:
        """ Добавляет сообщение в пользовательский журнал главного окна. """
        timestamp = datetime.now().strftime('%H:%M:%S')
        self._msg_text_edit.addItem(f'[{timestamp}] {level}:\n{message}')
        while self._msg_text_edit.count() > self._messages_limit:
            self._msg_text_edit.takeItem(0)
        self._msg_text_edit.scrollToBottom()

    def _add_info_message(self, message: str) -> None:
        """ Добавляет информационное сообщение в пользовательский журнал. """
        self._add_user_message('Инфо', message)

    def _add_warning_message(self, title: str, message: str) -> None:
        """ Добавляет предупреждение в пользовательский журнал. """
        self._add_user_message('Предупреждение', f'{title}: {message}')

    def _add_error_message(self, title: str, message: str) -> None:
        """ Добавляет сообщение об ошибке в пользовательский журнал. """
        self._add_user_message('Ошибка', f'{title}: {message}')

    def _start_calibration(self) -> None:
        """ Запускает калибровку датчиков. """
        try:
            self._app_logger.info('Запуск калибровки датчиков')
            self._com_port_reader.start_calibration()
            self._set_stage(self._calibration_stage)
            self._add_info_message('Калибровка датчиков запущена')
        except ComPortReaderException as err:
            self._add_error_message('Ошибка запуска калибровки', f'{err}')
            QMessageBox.warning(self, 'Ошибка запуска калибровки', f'{err}')

    def _start_static_init(self) -> None:
        """ Запускает набор статического буфера. """
        storage_opened = False
        try:
            storage_opened = self._prepare_static_init_storage()
            self._app_logger.info(
                f'Запуск набора статического буфера для проезда {self._get_passage_num()}'
            )
            self._com_port_reader.start_static_init()
            self._set_stage(self._static_init_stage)
            self._add_info_message(
                f'Набор статического буфера запущен для проезда #{self._get_passage_num()}'
            )
        except (ComPortReaderException, OSError, TypeError) as err:
            if storage_opened:
                self._close_current_data_file()
            self._add_error_message('Ошибка запуска набора статического буфера', f'{err}')
            QMessageBox.warning(self, 'Ошибка запуска набора статического буфера', f'{err}')

    def _start_measuring(self) -> None:
        """ Запускает сбор данных во время проезда. """
        storage_opened = False
        try:
            storage_opened = self._prepare_measuring_storage()
            self._app_logger.info(f'Запуск измерений для проезда {self._get_passage_num()}')
            self._com_port_reader.start_measuring()
            self._set_stage(self._measuring_stage)
            self._add_info_message(f'Измерения запущены для проезда #{self._get_passage_num()}')
        except (ComPortReaderException, OSError, TypeError) as err:
            if storage_opened:
                self._close_current_data_file()
            self._add_error_message('Ошибка запуска сбора данных', f'{err}')
            QMessageBox.warning(self, 'Ошибка запуска сбора данных', f'{err}')

    def _stop_measuring(self) -> None:
        """ Завершает сбор данных во время проезда. """
        try:
            passage_num = self._get_passage_num()
            self._app_logger.info(f'Завершение измерений для проезда {passage_num}')
            self._com_port_reader.stop_measuring()
            self._close_current_data_file()
            self._add_info_message(f'Измерения завершены для проезда #{passage_num}')
            self._increment_passage_num()
            self._set_stage(self._ready_for_static_init_stage)
        except ComPortReaderException as err:
            self._add_error_message('Ошибка завершения сбора данных', f'{err}')
            QMessageBox.warning(self, 'Ошибка завершения сбора данных', f'{err}')

    def _prepare_static_init_storage(self) -> bool:
        """ Задаёт файл хранилища для набора статического буфера. """
        return self._set_data_storage_file('static_init')

    def _prepare_measuring_storage(self) -> bool:
        """ Задаёт файл хранилища для измерений. """
        return self._set_data_storage_file('measuring')

    def _set_data_storage_file(self, stage_name: str) -> bool:
        """ Задаёт файл данных для текущего проезда и стадии. """
        if self._saving_path is None or self._template_filename is None:
            raise ComPortReaderException('Не заданы параметры сохранения данных')

        file_path = self._saving_path / f'{self._template_filename}_{stage_name}_{self._get_passage_num()}.csv'
        if self._data_storage.file_path == file_path and self._data_storage.is_open:
            return False

        self._app_logger.info(f'Задан файл сохранения данных: {file_path}')
        self._data_storage.set_file(file_path)
        return True

    def _close_current_data_file(self) -> None:
        """ Закрывает текущий файл сохранения данных. """
        if not self._data_storage.is_open:
            return

        try:
            file_path = self._data_storage.file_path
            packages_count = self._data_storage.count
            self._data_storage.close()
            self._app_logger.info(f'Файл данных закрыт: {file_path}; записано пакетов: {packages_count}')
        except OSError as err:
            self._app_logger.exception(f'Ошибка закрытия файла данных: {err}')
            self._add_error_message('Ошибка закрытия файла данных', f'{err}')
            QMessageBox.critical(self, 'Ошибка закрытия файла данных', f'{err}')

    def _get_passage_num(self) -> int:
        """ Возвращает номер текущего проезда. """
        passage_num = self._passage_num_edit.text().strip()
        if not passage_num:
            return 1
        try:
            return max(1, int(passage_num))
        except ValueError:
            self._app_logger.warning(f'Некорректный номер проезда: {passage_num}')
            self._add_warning_message(
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
        self._set_passage_num(self._get_passage_num() + 1)
        self._app_logger.info(f'Номер текущего проезда изменён: {self._get_passage_num()}')
        self._add_info_message(f'Текущий проезд: #{self._get_passage_num()}')

    def _error_handler(self, error_info: str) -> None:
        """ Обработка аварийной ошибки текущей сессии. """
        self._app_logger.error(f'Получена ошибка {error_info}')
        self._add_error_message('Ошибка выполнения', error_info)
        self._shutdown_com_port_reader()
        self._reset_to_setting_stage()
        QMessageBox.critical(self, "Ошибка выполнения!", error_info)

    def _reset_to_setting_stage(self) -> None:
        """ Возвращает главное окно к стадии настройки параметров. """
        self._com_port_settings.unlock_input()
        self._saving_params.unlock_input()
        self._apply_settings_button.setEnabled(True)
        self._saving_path = None
        self._template_filename = None
        self._session_configuration_started = False
        self._data_visualizer.reset()
        self._set_stage(self._setting_stage)

    def _shutdown_com_port_reader(self) -> None:
        """ Завершает текущую сессию ComPortReader. """
        try:
            self._app_logger.info('Завершение текущей сессии ComPortReader')
            self._com_port_reader.shutdown()
        except Exception as err:
            self._app_logger.exception(f'Ошибка при завершении работы ComPortReader: {err}')
            self._add_error_message('Ошибка при завершении работы ComPortReader', f'{err}')
        finally:
            self._close_current_data_file()

    # =============================================================
    # =============== Методы для обработки сигналов ===============
    # =============================================================

    def _data_received(self, package: TelegaData) -> None:
        """ Обработка полученного пакета данных от МК. """
        try:
            self._data_storage.add_package(package)
            self._data_visualizer.visualize_package(package)
        except OSError:
            self._error_handler('Ошибка записи CSV...')

    def _calibration_done(self) -> None:
        """ Обработка завершения калибровки датчиков. """
        title = 'Калибровка завершена'
        message = 'Калибровка датчиков завершена'
        self._app_logger.info(message)
        self._add_info_message(message)
        self._set_stage(self._ready_for_static_init_stage)
        QMessageBox.information(self, title, message)

    def _static_init_done(self) -> None:
        """ Обработка завершения набора статического буфера. """
        title = 'Статический буфер набран'
        message = 'Набор статического буфера завершён'
        self._app_logger.info(message)
        self._add_info_message(message)
        self._close_current_data_file()
        self._set_stage(self._ready_for_measuring_stage)
        QMessageBox.information(self, title, message)

    def _handshake_done(self) -> None:
        """ Обработка успешного рукопожатия с МК. """
        self._app_logger.info('Рукопожатие с МК выполнено успешно')
        self._add_info_message('Рукопожатие с МК выполнено успешно')
        self._set_stage(self._calibration_stage)

    def _handshake_failed(self) -> None:
        """ Обработка ошибки рукопожатия с МК. """
        self._app_logger.error('Ошибка рукопожатия с МК')
        self._add_error_message('Ошибка подключения', 'Не удалось выполнить рукопожатие с МК')
        self._shutdown_com_port_reader()
        self._reset_to_setting_stage()
        QMessageBox.critical(self, 'Ошибка подключения', 'Не удалось выполнить рукопожатие с МК')

    def _connection_failed(self, error_info: str) -> None:
        """ Обработка ошибки запуска подключения к МК. """
        title = 'Ошибка подключения'
        message = f'Не удалось подключиться к COM-порту:\n{error_info}'
        self._app_logger.error(message)
        self._add_error_message(title, message)
        self._shutdown_com_port_reader()
        self._reset_to_setting_stage()
        QMessageBox.critical(self, title, message)

    def _com_port_reader_finished(self) -> None:
        """ Обработка завершения работы ComPortReader. """
        self._app_logger.info('ComPortReader завершил работу')
