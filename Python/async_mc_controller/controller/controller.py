# System imports
import asyncio
from abc import ABC, abstractmethod
import logging
from typing import Any, Optional

# External imports

# User imports
from async_mc_controller.signal_bus import McBus
from async_mc_controller.logger import McLogger
from async_mc_controller.byte_source.read_error import ReadError

#########################

class Controller(ABC):
    """Контроллер приложения — управляет жизненным циклом измерения."""

    def __init__(self, bus: McBus, mc_logger: McLogger):
        self._bus: McBus = bus
        self._controller_logger: logging.Logger = mc_logger.get_child_logger("Controller")

        # Флаг аварийной остановки и таска для проверки флага
        self._force_stop: bool = False
        self._checking_force_stop_flag_task: Optional[asyncio.Task] = None

    # =============================================================
    # ======= Методы для работы в контекстном менеджере ===========
    # =============================================================

    async def __aenter__(self) -> 'Controller':
        """ Самостоятельная подписка на события шины и
        запуск отслеживания флага _force_stop
        """
        self._bus.package_ready.subscribe(self)
        self._bus.read_error.subscribe(self)
        self._bus.handshake_failed.subscribe(self)
        self._bus.device_lost.subscribe(self)
        self._bus.command_ack_timeout.subscribe(self)
        self._bus.command_rejected.subscribe(self)

        # self._checking_force_stop_flag_task = asyncio.create_task(self._checking_force_stop_flag())

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """ Отписка от всех сигналов шины и
        остановка отслеживания флага _force_stop
        """
        self._bus.package_ready.unsubscribe(self)
        self._bus.read_error.unsubscribe(self)
        self._bus.handshake_failed.unsubscribe(self)
        self._bus.device_lost.unsubscribe(self)
        self._bus.command_ack_timeout.unsubscribe(self)
        self._bus.command_rejected.unsubscribe(self)

        await self._cancel_task(self._checking_force_stop_flag_task)
        self._checking_force_stop_flag_task = None

        return False

    # =============================================================
    # =================== Внутренняя логика =======================
    # =============================================================

    @staticmethod
    async def _cancel_task(task: Optional[asyncio.Task]) -> None:
        """Отмена задачи, ожидание её завершения и присвоение ей None.

        Args:
            task: Задача для отмены. Если None или завершена — ничего не делает.
        """
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _checking_force_stop_flag(self) -> None:
        try:
            while True:
                if self._force_stop:
                    self._controller_logger.warning("Выставлен флаг _force_stop! "
                                                    "Эмитирование сигнала INTERRUPT_MEASURING...")
                    await self._bus.interrupt_measuring.emit()
                    return
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            self._controller_logger.debug("Таска для отслеживания _force_stop отменена")

    # =============================================================
    # =================== Обработчики сигналов ====================
    # =============================================================

    @abstractmethod
    async def on_package_ready(self, data: Any) -> None:
        """Обработчик сигнала PACKAGE_READY.

        Должен быть определён в классе наследнике!
        """
        ...

    async def on_read_error(self, err: ReadError) -> None:
        """Обработчик сигнала READ_ERROR — выставляет _force_stop.

        Эмиттится AsyncComPort.reading_loop при перехвате ошибки чтения
        (физический обрыв соединения, сбой последовательного порта и т.п.).
        Цикл чтения уже завершился самостоятельно; дальнейшая остановка
        ресурсов произойдёт через INTERRUPT_MEASURING из stop().

        Args:
            err (ReadError): Исключение, которое привело к остановке чтения.
                             Сохраняется в логе для последующего анализа.
        """
        self._controller_logger.critical(f'Ошибка чтения из источника: {err} — аварийная остановка')
        self._force_stop = True

    async def on_handshake_failed(self) -> None:
        """Обработчик сигнала HANDSHAKE_FAILED — выставляет _force_stop.

        Вызывается когда рукопожатие с МК не выполнено за отведённое время.
        STOP_MEASURING будет эмиттирован из stop() после выхода из цикла.
        """
        self._controller_logger.critical('Рукопожатие с МК не выполнено — аварийная остановка')
        self._force_stop = True

    async def on_device_lost(self) -> None:
        """Обработчик сигнала DEVICE_LOST — выставляет _force_stop.

        Вызывается когда МК не ответил на heartbeat за отведённое время.
        STOP_MEASURING будет эмиттирован из stop() после выхода из цикла.
        """
        self._controller_logger.critical('Устройство не отвечает — аварийная остановка')
        self._force_stop = True

    async def on_command_ack_timeout(self) -> None:
        """Обработчик сигнала COMMAND_ACK_TIMEOUT — выставляет _force_stop.

        Вызывается когда МК не подтвердил выполнение отправленной команды
        за отведённое время. Трактуется как некорректное поведение устройства.
        STOP_MEASURING будет эмиттирован из stop() после выхода из цикла.
        """
        self._controller_logger.critical('МК не подтвердил команду — аварийная остановка')
        self._force_stop = True

    async def on_command_rejected(self) -> None:
        """Обработчик сигнала COMMAND_REJECTED — выставляет _force_stop.

        Вызывается когда МК ответил, но не распознал отправленную команду
        (прислал 'UNKNOWN_COMMAND'). Это программная ошибка контракта
        ПК↔МК — продолжение работы небезопасно. INTERRUPT_MEASURING будет
        эмиттирован из stop() после выхода из цикла.
        """
        self._controller_logger.critical('МК не распознал команду — программная ошибка ПК↔МК, аварийная остановка')
        self._force_stop = True