"""Стадия набора статического буфера."""

# System imports

# External imports

# User imports
from gui.program_stages.program_stage import ProgramStage

##########################################################


class StaticInitStage(ProgramStage):
    """Набор статического буфера уже начат."""

    name = 'набор статического буфера уже начат'

    def apply_settings(self) -> None:
        """Отклоняет изменение настроек активной сессии."""
        self._show_settings_locked_warning()

    def start_static_init(self) -> None:
        """Отклоняет повторный запуск статического буфера."""
        self._show_warning(
            'Ошибка начала набора статического буфера',
            'Набор статического буфера уже запущен'
        )

    def start_measuring(self) -> None:
        """Отклоняет измерения до завершения статической инициализации."""
        self._show_warning(
            'Ошибка начала сбора данных',
            'Необходимо завершить набор статического буфера'
        )

    def stop_measuring(self) -> None:
        """Отклоняет завершение ещё не запущенных измерений."""
        self._show_warning(
            'Ошибка завершения сбора данных',
            'Измерения ещё не запущены'
        )
