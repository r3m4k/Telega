# -*- coding: utf-8 -*-
"""Асинхронное мерцание трёхпозиционного Qt-индикатора."""

# System imports
import asyncio
import logging
from typing import Optional

# External imports
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox

# User imports

##########################################################


class IndicatorBlinker:
    """Циклически изменяет состояние индикатора в GUI event loop.

    Класс не создаёт отдельный поток. Метод :meth:`start` должен вызываться
    внутри работающего Qt/asyncio loop, чтобы изменения `QCheckBox` выполнялись
    в GUI-потоке.

    Args:
        indicator: Трёхпозиционный индикатор.
        period_ms: Период переключения состояния в миллисекундах.
        logger: Логгер приложения.

    Raises:
        TypeError: Передан объект неправильного типа.
        ValueError: Период не является положительным целым числом.
    """

    def __init__(self,
                 indicator: QCheckBox,
                 period_ms: int = 1000,
                 logger: Optional[logging.Logger] = None):
        if not isinstance(indicator, QCheckBox):
            raise TypeError(f'Ожидается indicator: QCheckBox, получен {type(indicator)}')
        if not isinstance(period_ms, int) or isinstance(period_ms, bool):
            raise TypeError(f'Ожидается period_ms: int, получен {type(period_ms)}')
        if period_ms <= 0:
            raise ValueError('Период мерцания должен быть больше нуля')

        self._indicator: QCheckBox = indicator
        self._period_seconds: float = period_ms / 1000
        self._logger: logging.Logger = logger or logging.getLogger(__name__)
        self._blinking_task: Optional[asyncio.Task[None]] = None
        self._configure_indicator()

    @property
    def is_running(self) -> bool:
        """Возвращает наличие активной задачи мерцания."""
        task = self._blinking_task
        return task is not None and not task.done()

    def start(self) -> None:
        """Запускает мерцание в текущем работающем asyncio event loop.

        Raises:
            RuntimeError: Метод вызван вне работающего asyncio event loop.
        """
        if self.is_running:
            return

        task = asyncio.create_task(
            self._blinking_loop(),
            name='indicator_blinker',
        )
        self._blinking_task = task
        task.add_done_callback(self._blinking_done)

    async def stop(self) -> None:
        """Отменяет задачу мерцания и дожидается её завершения."""
        task = self._blinking_task
        if task is None:
            return

        if not task.done():
            task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        finally:
            if self._blinking_task is task:
                self._blinking_task = None

    async def _blinking_loop(self) -> None:
        """Циклически устанавливает три состояния `QCheckBox`."""
        states = (Qt.Unchecked, Qt.PartiallyChecked, Qt.Checked)
        state_index = 0
        try:
            while True:
                self._indicator.setCheckState(states[state_index])
                state_index = (state_index + 1) % len(states)
                await asyncio.sleep(self._period_seconds)
        except asyncio.CancelledError:
            self._logger.debug('Задача мерцания индикатора отменена')
            raise

    def _configure_indicator(self) -> None:
        """Настраивает `QCheckBox` для использования как индикатора."""
        self._indicator.setTristate(True)
        self._indicator.setCheckState(Qt.Unchecked)
        self._indicator.setFocusPolicy(Qt.NoFocus)
        self._indicator.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def _blinking_done(self, task: asyncio.Task[None]) -> None:
        """Получает результат фоновой задачи и журналирует её ошибку."""
        if self._blinking_task is task:
            self._blinking_task = None
        if task.cancelled():
            return

        error = task.exception()
        if error is not None:
            self._logger.error(
                f'Ошибка задачи мерцания индикатора: {error}',
                exc_info=(type(error), error, error.__traceback__),
            )
