"""Стадия ожидания настроек программы."""

# System imports

# External imports
from PyQt5.QtWidgets import QMessageBox

# User imports
from gui.com_port_reader import ComPortReaderException
from gui.com_port_settings import ComPortSettingsError
from gui.program_stages.program_stage import ProgramStage
from gui.saving_params import InvalidPathError, InvalidTemplateFilenameError

##########################################################


class SettingStage(ProgramStage):
    """Ожидание настроек сохранения и параметров порта."""

    name = 'ожидание подтверждения настроек'

    def apply_settings(self) -> None:
        """Сохраняет настройки COM-порта и параметры сохранения."""
        try:
            saving_path = self._main_window._saving_params.get_saving_path()
            template_filename = self._main_window._saving_params.get_template_filename()
            com_port_name = self._main_window._com_port_settings.get_port_name()

            self._main_window.configure_session(
                saving_path,
                template_filename,
                com_port_name,
            )

        except (InvalidPathError, InvalidTemplateFilenameError,
                ComPortSettingsError, ComPortReaderException, OSError, TypeError) as err:
            self._main_window.add_error_message('Ошибка задания параметров', f'{err}')
            QMessageBox.critical(
                self._main_window,
                'Ошибка задания параметров!',
                f'{err}',
            )

    def start_static_init(self) -> None:
        """Отклоняет запуск статического буфера до настройки программы."""
        self._show_warning(
            'Ошибка начала набора статического буфера',
            'Для начала задайте настройки com порта и параметры сохранения'
        )

    def start_measuring(self) -> None:
        """Отклоняет запуск измерений до настройки программы."""
        self._show_warning(
            'Ошибка начала сбора данных',
            'Для начала задайте настройки com порта и параметры сохранения'
        )

    def stop_measuring(self) -> None:
        """Отклоняет завершение ещё не запущенных измерений."""
        self._show_warning(
            'Ошибка завершения сбора данных',
            'Измерения ещё не запущены'
        )
