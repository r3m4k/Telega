"""Стадия готовности к набору статического буфера."""

# System imports

# External imports

# User imports
from gui.program_stages.program_stage import ProgramStage

##########################################################


class ReadyForStaticInitStage(ProgramStage):
    """Готовность начать набор статического буфера."""

    name = 'готовность начать набор статического буфера'

    def apply_settings(self) -> None:
        """Отклоняет изменение настроек активной сессии."""
        self._show_settings_locked_warning()

    def start_static_init(self) -> None:
        """Запускает набор статического буфера."""
        self._main_window.start_static_init()

    def start_measuring(self) -> None:
        """Отклоняет измерения до набора статического буфера."""
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
