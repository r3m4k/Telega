# -*- coding: utf-8 -*-
"""Модуль мерцания трёхпозиционного индикатора."""

# System imports
import logging
from typing import Optional

# External imports
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QCheckBox

##########################################################

class IndicatorBlinker(QThread):
    """Поток для циклического изменения состояния индикатора."""

    state_changed = pyqtSignal(int)

    def __init__(self,
                 indicator: QCheckBox,
                 period_ms: int = 1000,
                 logger: Optional[logging.Logger] = None):
        super().__init__()
        if not isinstance(indicator, QCheckBox):
            raise TypeError(f"Ожидается indicator: QCheckBox, получен {type(indicator)}")

        self._indicator = indicator
        self._period_ms = period_ms
        self._logger = logger
        self._stop_requested = False
        self._configure_indicator()

    def stop(self) -> None:
        """Останавливает мерцание индикатора."""
        if not self.isRunning():
            return

        self._stop_requested = True
        if not self.wait(1500):
            if self._logger is not None:
                self._logger.warning('Поток мерцания индикатора не остановился вовремя')
            self.terminate()
            self.wait(500)

    def run(self) -> None:
        """Циклически отправляет три состояния QCheckBox."""
        self._stop_requested = False
        states = (Qt.Unchecked, Qt.PartiallyChecked, Qt.Checked)
        state_index = 0

        while not self._stop_requested:
            self.state_changed.emit(states[state_index])
            state_index = (state_index + 1) % len(states)
            self._sleep_with_stop_check()

    def _configure_indicator(self) -> None:
        """Настраивает QCheckBox для работы как индикатор."""
        self._indicator.setTristate(True)
        self._indicator.setCheckState(Qt.Unchecked)
        self._indicator.setFocusPolicy(Qt.NoFocus)
        self._indicator.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.state_changed.connect(self._set_indicator_state)

    def _set_indicator_state(self, state: int) -> None:
        """Задаёт состояние индикатора в GUI-потоке."""
        self._indicator.setCheckState(Qt.CheckState(state))

    def _sleep_with_stop_check(self) -> None:
        """Ожидает период мерцания с проверкой остановки."""
        elapsed_ms = 0
        while elapsed_ms < self._period_ms and not self._stop_requested:
            sleep_ms = min(50, self._period_ms - elapsed_ms)
            self.msleep(sleep_ms)
            elapsed_ms += sleep_ms
