"""Стадия готовности к измерениям."""

# System imports

# External imports

# User imports
from gui.program_stages.program_stage import ProgramStage

##########################################################


class ReadyForMeasurementStage(ProgramStage):
    """Готовность начать измерение."""

    name = 'готовность начать измерение'

    def apply_settings(self) -> None:
        """Отклоняет изменение настроек активной сессии."""
        self._show_settings_locked_warning()

    def start_static_init(self) -> None:
        """Отклоняет повторный набор статического буфера."""
        self._show_warning(
            'Ошибка начала набора статического буфера',
            'Статический буфер уже набран. Начните измерения или завершите текущий цикл'
        )

    def start_measuring(self) -> None:
        """Запускает сбор данных."""
        self._main_window.start_measuring()

    def stop_measuring(self) -> None:
        """Отклоняет завершение ещё не запущенных измерений."""
        self._show_warning(
            'Ошибка завершения сбора данных',
            'Измерения ещё не запущены'
        )
