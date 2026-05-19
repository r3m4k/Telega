# System imports
import asyncio
from typing import Optional
import logging

# External imports

# User imports
from async_mc_controller.signal_bus import McBus
from async_mc_controller.logger import McLogger
from async_mc_controller.byte_source.com_port.com_port import AsyncComPort
from async_mc_controller.byte_source.com_port.com_port_error import ComPortReadError

#########################


_RESPONSE_TIMEOUT: float = 2.0    # Таймаут ответа на рукопожатие и heartbeat (сек)
_HEARTBEAT_PERIOD: float = 10.0   # Период отправки heartbeat (сек)


class AsyncComPortDevice(AsyncComPort):
    """Асинхронный класс для работы с платой МК без конкретизации под протокол общения с МК.

    Расширяет AsyncComPort процедурой обмена сигналами через шину для управления
    режимами работы платы:
    - При START_MEASURING эмиттит HANDSHAKE_INIT, отправляет команду
      рукопожатия и ждёт ACK через Event.
    - При HANDSHAKE_DONE устанавливает событие рукопожатия, переводит плату
      в режим измерения и запускает heartbeat loop.
    - Heartbeat loop периодически отправляет команду и ждёт ACK через Event.
    - При таймауте рукопожатия эмиттит HANDSHAKE_FAILED.
    - При таймауте heartbeat эмиттит DEVICE_LOST.

    Команды на МК должны быть определены в наследнике, описывающий протокол взаимодействия с МК.

    Attributes:
        _handshake_req_command (bytes):     Команда инициализации рукопожатия.
        _heartbeat_req_command (bytes):          Команда проверки на зависание.
    """

    _handshake_req_command: Optional[bytes] = None
    _heartbeat_req_command: Optional[bytes] = None

    def __init__(self, port_name: str, baudrate: int,
                 bus: McBus, mc_logger: McLogger):
        super().__init__(port_name, baudrate)

        self._bus = bus

        self._com_port_logger = mc_logger.get_child_logger("ComPort")
        self._device_logger: logging.Logger = mc_logger.get_child_logger("ComPort.Device")

        if not self._handshake_req_command or not self._heartbeat_req_command:
            raise RuntimeError("Определите в наследнике сигнатуру _handshake_req_command и _heartbeat_req_command!")

        self._handshake_ack_event: asyncio.Event = asyncio.Event()   # Событие получения ACK рукопожатия
        self._heartbeat_ack_event: asyncio.Event = asyncio.Event()   # Событие получения ACK heartbeat
        self._command_ack_event: asyncio.Event   = asyncio.Event()   # Событие получения подтверждения команды

        self._command_lock = asyncio.Lock()     # Блокировка для последовательной отправки команд с ожиданием ACK.

        self._heartbeat_task: Optional[asyncio.Task] = None     # Задача heartbeat loop
        self._stop_flag: bool = False     # Флаг «остановка уже выполнена»

    # =============================================================
    # ======= Методы для работы в контекстном менеджере ===========
    # =============================================================

    async def __aenter__(self) -> 'AsyncComPortDevice':
        """ Вызов родительского __aenter__, самостоятельная
        подписка на события шины и выполнение процедуры рукопожатия
        """
        await super().__aenter__()

        # Самостоятельная подписка на сигналы шины
        self._bus.stop_executing.subscribe(self)
        self._bus.handshake_init.subscribe(self)
        self._bus.handshake_done.subscribe(self)
        self._bus.heartbeat_ack.subscribe(self)
        self._bus.command_ack.subscribe(self)
        self._bus.command_rejected.subscribe(self)
        self._bus.interrupt_measuring.subscribe(self)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        Выставление флага self._stopped в True, завершение _heartbeat_task и
        вызов AsyncComPort.__aexit__ для остановки чтения порта.
        """
        # Выставим флаг остановки и отменим _heartbeat_task
        self._stop_flag = True
        await self._cancel_task(self._heartbeat_task)
        self._heartbeat_task = None

        # Отпишемся от событий шины
        self._bus.stop_executing.unsubscribe(self)
        self._bus.handshake_init.unsubscribe(self)
        self._bus.handshake_done.unsubscribe(self)
        self._bus.heartbeat_ack.unsubscribe(self)
        self._bus.command_ack.unsubscribe(self)
        self._bus.command_rejected.unsubscribe(self)
        self._bus.interrupt_measuring.unsubscribe(self)

        await super().__aexit__(exc_type, exc_val, exc_tb)

        return False

    # =============================================================
    # =================== Обработчики сигналов ====================
    # =============================================================

    async def on_stop_executing(self) -> None:
        """Обработчик сигнала STOP_EXECUTING от контроллера.

        Завершение задачи _heartbeat_task и выставление флага _stop_flag.
        """
        await self._cancel_task(self._heartbeat_task)
        self._heartbeat_task = None

        await self._cancel_task(self._reading_task)
        self._reading_task = None

        self._stop_flag = True

    async def on_handshake_init(self) -> None:
        """Обработчик сигнала HANDSHAKE_INIT от контроллера.

        Инициирует процедуру рукопожатия.
        """
        self._device_logger.debug(f'Инициализация рукопожатия по порту {self._port_name}')
        await self._send_command(self._handshake_req_command)

        self._handshake_ack_event.clear()
        try:
            await asyncio.wait_for(
                self._handshake_ack_event.wait(),
                timeout=_RESPONSE_TIMEOUT
            )

            # Запустим _heartbeat_loop
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        except asyncio.TimeoutError:
            self._device_logger.error(
                f'Таймаут рукопожатия по порту {self._port_name} '
                f'({_RESPONSE_TIMEOUT} сек) — рукопожатие не выполнено'
            )
            await self._bus.handshake_failed.emit()

    async def on_handshake_done(self) -> None:
        """Обработчик сигнала HANDSHAKE_DONE от декодера.

        Устанавливает событие рукопожатия.
        """
        self._handshake_ack_event.set()
        self._device_logger.info(f'Рукопожатие по порту {self._port_name} выполнено успешно')

    async def on_heartbeat_ack(self) -> None:
        """Обработчик сигнала HEARTBEAT_ACK от декодера."""
        self._heartbeat_ack_event.set()
        self._device_logger.debug(f'ACK heartbeat получен по порту {self._port_name}')

    async def on_command_ack(self) -> None:
        """Обработчик сигнала COMMAND_ACK от декодера.

        Устанавливает событие подтверждения команды, снимая ожидание
        в _send_command_with_ack.
        """
        self._command_ack_event.set()
        self._device_logger.debug(f'Подтверждение команды получено по порту {self._port_name}')

    async def on_command_rejected(self) -> None:
        """Обработчик сигнала COMMAND_REJECTED от декодера.

        МК ответил, но команду не распознал. Снимает ожидание в
        _send_command_with_ack тем же _command_ack_event — самой эмиссии
        исхода наружу здесь не делаем (её уже сделал декодер). Логику
        аварийной остановки выполняет Controller, подписанный на тот же
        сигнал.
        """
        self._command_ack_event.set()
        self._device_logger.debug(
            f'Ожидание ACK команды прервано по порту {self._port_name}: МК отверг команду'
        )

    async def on_interrupt_measuring(self) -> None:
        """Обработчик сигнала INTERRUPT_MEASURING.

        Аварийная остановка: связь с МК нарушена, протокольное
        взаимодействие невозможно.

        Heartbeat останавливается через _cancel_task — CancelledError
        чисто прервёт его внутренний wait_for, без ложного DEVICE_LOST.
        Чтение прерывается при выходе из контекстного менеджера.

        Идемпотентен: повторный вызов после уже выполненной остановки — no-op.
        Это нужно для случая «штатная остановка → сбой команды → повторный
        INTERRUPT_MEASURING из Controller.stop() или аналогичного метода»:
        ресурсы уже освобождены, повторный проход тут не должен ничего ломать.
        """
        if self._stop_flag:
            self._device_logger.debug(
                f'INTERRUPT_MEASURING для порта {self._port_name} проигнорирован: '
                f'остановка уже выполнена'
            )
            return

        self._stop_flag = True
        self._device_logger.warning(f'Аварийная остановка работы с портом {self._port_name}')
        await self._cancel_task(self._heartbeat_task)
        self._heartbeat_task = None

        self._command_ack_event.set()

    # =============================================================
    # =================== Внутренняя логика =======================
    # =============================================================

    async def _heartbeat_loop(self) -> None:
        """Периодическая отправка heartbeat команды и ожидание ACK.

        Каждые _HEARTBEAT_PERIOD секунд отправляет команду на МК
        и ждёт ACK через asyncio.Event в течение _RESPONSE_TIMEOUT секунд.
        При таймауте эмиттит DEVICE_LOST.
        Завершается корректно при отмене (asyncio.CancelledError).
        """
        self._device_logger.debug(f'Запуск heartbeat loop по порту {self._port_name}')
        try:
            while True:
                await asyncio.sleep(_HEARTBEAT_PERIOD)

                self._device_logger.debug(f'Отправка heartbeat по порту {self._port_name}')
                self._heartbeat_ack_event.clear()
                await self._bus.heartbeat_sent.emit()
                await self._send_command(self._heartbeat_req_command)
                try:
                    await asyncio.wait_for(
                        self._heartbeat_ack_event.wait(),
                        timeout=_RESPONSE_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    self._device_logger.error(
                        f'Таймаут heartbeat по порту {self._port_name} '
                        f'({_RESPONSE_TIMEOUT} сек) — устройство не отвечает'
                    )
                    self._stop_flag = True
                    await self._bus.device_lost.emit()
                    return

        except asyncio.CancelledError:
            self._device_logger.debug(f'Heartbeat loop остановлен по порту {self._port_name}')
            raise

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

    async def _send_command(self, command: bytes) -> None:
        """Отправка команды по COM-порту без ожидания подтверждения.

        Args:
            command (bytes): Команда для отправки на плату МК.
        """
        self._device_logger.debug(f'Отправка команды {command}')
        self._port_writer.write(command)
        await self._port_writer.drain()

    async def _send_command_with_ack(self, command: bytes) -> None:
        """Отправка команды с ожиданием подтверждения от МК.

        Метод сериализует отправку команд с помощью `self._command_lock`:
        одновременно может выполняться только одна команда, ожидающая ACK.
        Это исключает гонки за `_command_ack_event` и перепутывание
        подтверждений от разных команд.

        Если установлен флаг `self._stop_flag`, команда не отправляется,
        а в лог выводится предупреждение.

        Эмиттит COMMAND_SENT (декодер сохраняет состояние),
        отправляет команду и ждёт пока _command_ack_event будет выставлен.
        Событие может быть выставлено тремя путями:
          1. on_command_ack          — штатный ACK (декодер уже эмиттнул COMMAND_ACK);
          2. on_command_rejected     — МК отверг команду (декодер уже эмиттнул COMMAND_REJECTED);
          3. on_interrupt_measuring  — аварийная остановка (контроллер уже эмиттнул INTERRUPT_MEASURING).

        Во всех трёх случаях исход доставлен наружу другим путём — здесь
        ничего не эмиттим. Эмиссия делается только если истёк таймаут:
        COMMAND_ACK_TIMEOUT означает «МК не ответил вообще никак».

        Args:
            command (bytes): Команда для отправки на плату МК.
        """
        async with self._command_lock:
            if self._stop_flag:
                self._device_logger.warning(f"Общение с МК остановлено, команда {command} не отправлена")
                return

            self._command_ack_event.clear()
            await self._bus.command_sent.emit()

            self._device_logger.debug(f'Отправка команды с подтверждением {command}')
            self._port_writer.write(command)
            await self._port_writer.drain()

            try:
                await asyncio.wait_for(
                    self._command_ack_event.wait(),
                    timeout=_RESPONSE_TIMEOUT
                )
            except asyncio.TimeoutError:
                self._device_logger.error(
                    f'Таймаут подтверждения команды по порту {self._port_name} '
                    f'({_RESPONSE_TIMEOUT} сек)'
                )
                self._stop_flag = True
                await self._bus.command_ack_timeout.emit()

    async def new_byte_callback(self, bt: bytes) -> None:
        """Отработка получения нового байта из порта.

        Эмитирование сигнала new_byte.
        """
        await self._bus.new_byte.emit(bt)

    async def read_error_callback(self, err: ComPortReadError) -> None:
        """Отработка ошибки чтения данных из порта.

        Эмитирование сигнала read_error.
        """
        await self._bus.read_error.emit(err)
