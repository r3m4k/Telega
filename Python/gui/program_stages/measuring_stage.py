"""Стадия активных измерений."""

# System imports

# External imports

# User imports
from gui.program_stages.program_stage import ProgramStage

##########################################################


class MeasuringStage(ProgramStage):
    """Измерения уже начаты."""

    name = 'измерения уже начаты'

    def apply_settings(self) -> None:
        """Отклоняет изменение настроек активной сессии."""
        self._show_settings_locked_warning()

    def start_static_init(self) -> None:
        """Отклоняет набор статического буфера во время измерений."""
        self._show_warning(
            'Ошибка начала набора статического буфера',
            'Нельзя запускать набор статического буфера во время измерений'
        )

    def start_measuring(self) -> None:
        """Отклоняет повторный запуск измерений."""
        self._show_warning(
            'Ошибка начала сбора данных',
            'Измерения уже запущены'
        )

    def stop_measuring(self) -> None:
        """Завершает сбор данных."""
        self._main_window.stop_measuring()
