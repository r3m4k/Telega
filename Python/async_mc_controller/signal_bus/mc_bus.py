# System imports
import logging
import sys
from typing import Any, Optional

# External imports

# User imports
from async_mc_controller.logger import McLogger
from .signals import Signals
from .signal_bus import SignalBus
from .subscribers import (
    NewByteSubscriber,
    PackageReadySubscriber,
    StopExecutingSubscriber,
    StartMeasuringSubscriber,
    StopMeasuringSubscriber,
    StartCalibrationSubscriber,
    StopCalibrationSubscriber,
    StartStaticInitSubscriber,
    StopStaticInitSubscriber,
    InterruptMeasuringSubscriber,
    ReadErrorSubscriber,
    HandshakeInitSubscriber,
    HandshakeDoneSubscriber,
    HeartbeatSentSubscriber,
    HeartbeatAckSubscriber,
    HandshakeFailedSubscriber,
    DeviceLostSubscriber,
    CommandSentSubscriber,
    CommandAckSubscriber,
    CommandAckTimeoutSubscriber,
    CommandRejectedSubscriber,
)

from async_mc_controller.byte_source.read_error import ReadError

#########################

class McBus:
    """Типизированная обёртка над SignalBus для конкретного приложения.

    Каждый сигнал представлен отдельным вложенным классом-дескриптором,
    который инкапсулирует методы subscribe, unsubscribe и emit.

    Пример использования:
        bus = McBus()

        class Decoder:
            async def on_byte_received(self, bt: bytes) -> None:
                self._queue.put_nowait(bt)

        decoder = Decoder()
        bus.new_byte.subscribe(decoder)
        await bus.new_byte.emit(b'\\xff')
    """

    # Используемая сигнальная шина
    _signal_bus: SignalBus = SignalBus()

    # Используемый логгер
    _logger: Optional[logging.Logger] = None

    # Сигналы, эмиссия которых логируется на уровне DEBUG.
    # Высокочастотные сигналы (NEW_BYTE, PACKAGE_READY) намеренно исключены.
    _logged_signals: set[Signals] = {
        Signals.STOP_EXECUTING,
        Signals.START_MEASURING,
        Signals.STOP_MEASURING,
        Signals.START_CALIBRATION,
        Signals.START_STATIC_INIT,
        Signals.STOP_CALIBRATION,
        Signals.STOP_STATIC_INIT,
        Signals.INTERRUPT_MEASURING,
        Signals.READ_ERROR,
        Signals.HANDSHAKE_INIT,
        Signals.HANDSHAKE_DONE,
        Signals.HANDSHAKE_FAILED,
        Signals.HEARTBEAT_SENT,
        Signals.HEARTBEAT_ACK,
        Signals.DEVICE_LOST,
        Signals.COMMAND_SENT,
        Signals.COMMAND_ACK,
        Signals.COMMAND_ACK_TIMEOUT,
        Signals.COMMAND_REJECTED,
    }

    @staticmethod
    async def _emit(signal: Signals, *args: Any, **kwargs: Any) -> None:
        """Внутренняя обёртка над _signal_bus.emit с опциональным логированием.
    
        Логирует эмиссию сигнала если он входит в _logged_signals
        и уровень логирования равен DEBUG. Отправитель определяется
        через sys._getframe() — только при необходимости логирования.
        Используется всеми дескрипторами McBus вместо прямого вызова _signal_bus.emit.
        """
        if signal in McBus._logged_signals and McBus._logger.isEnabledFor(logging.DEBUG):
            frame  = sys._getframe(2)   # 0=_emit, 1=дескриптор emit, 2=реальный вызывающий код
            caller = frame.f_locals.get('self', None)
            sender = type(caller).__name__ if caller else frame.f_code.co_name
            McBus._logger.debug(f'[{sender}] → {signal.value}')
        await McBus._signal_bus.emit(signal, *args, **kwargs)


    # =============================================================
    # ===================== Передача данных =======================
    # =============================================================

    class NewByteSignal:
        """Эмиттится ComPort при получении байта."""

        @staticmethod
        def subscribe(subscriber: NewByteSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.NEW_BYTE, subscriber.on_byte_received)

        @staticmethod
        def unsubscribe(subscriber: NewByteSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.NEW_BYTE, subscriber.on_byte_received)

        @staticmethod
        async def emit(bt: bytes) -> None:
            await McBus._emit(Signals.NEW_BYTE, bt)

    # ------------------------------------------

    class PackageReadySignal:
        """Эмиттится Decoder при успешной сборке пакета."""

        @staticmethod
        def subscribe(subscriber: PackageReadySubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.PACKAGE_READY, subscriber.on_package_ready)

        @staticmethod
        def unsubscribe(subscriber: PackageReadySubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.PACKAGE_READY, subscriber.on_package_ready)

        @staticmethod
        async def emit(data) -> None:
            await McBus._emit(Signals.PACKAGE_READY, data)

    # =============================================================
    # =================== Управление измерением ===================
    # =============================================================

    class StopExecutingSignal:
        """Эмиттится контроллером для штатного завершения работы"""

        @staticmethod
        def subscribe(subscriber: StopExecutingSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.STOP_EXECUTING, subscriber.on_stop_executing)

        @staticmethod
        def unsubscribe(subscriber: StopExecutingSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.STOP_EXECUTING, subscriber.on_stop_executing)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.STOP_EXECUTING)

    class StartMeasuringSignal:
        """Эмиттится контроллером для запуска чтения."""

        @staticmethod
        def subscribe(subscriber: StartMeasuringSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.START_MEASURING, subscriber.on_start_measuring)

        @staticmethod
        def unsubscribe(subscriber: StartMeasuringSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.START_MEASURING, subscriber.on_start_measuring)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.START_MEASURING)

    # ------------------------------------------

    class StopMeasuringSignal:
        """Эмиттится контроллером для остановки чтения."""

        @staticmethod
        def subscribe(subscriber: StopMeasuringSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.STOP_MEASURING, subscriber.on_stop_measuring)

        @staticmethod
        def unsubscribe(subscriber: StopMeasuringSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.STOP_MEASURING, subscriber.on_stop_measuring)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.STOP_MEASURING)

    # ------------------------------------------

    class StartCalibrationSignal:
        """Эмиттится контроллером для запуска калибровки датчиков."""

        @staticmethod
        def subscribe(subscriber: StartCalibrationSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.START_CALIBRATION, subscriber.on_start_calibration)

        @staticmethod
        def unsubscribe(subscriber: StartCalibrationSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.START_CALIBRATION, subscriber.on_start_calibration)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.START_CALIBRATION)

    # ------------------------------------------

    class StopCalibrationSignal:
        """Эмиттится контроллером при завершении калибровки датчиков."""

        @staticmethod
        def subscribe(subscriber: StopCalibrationSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.STOP_CALIBRATION, subscriber.on_stop_calibration)

        @staticmethod
        def unsubscribe(subscriber: StopCalibrationSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.STOP_CALIBRATION, subscriber.on_stop_calibration)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.STOP_CALIBRATION)

    # ------------------------------------------

    class StartStaticInitSignal:
        """Эмиттится контроллером для запуска сбора статического буфера."""

        @staticmethod
        def subscribe(subscriber: StartStaticInitSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.START_STATIC_INIT, subscriber.on_start_static_init)

        @staticmethod
        def unsubscribe(subscriber: StartStaticInitSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.START_STATIC_INIT, subscriber.on_start_static_init)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.START_STATIC_INIT)

    # ------------------------------------------

    class StopStaticInitSignal:
        """Эмиттится контроллером при завершении сбора статического буфера."""

        @staticmethod
        def subscribe(subscriber: StopStaticInitSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.STOP_STATIC_INIT, subscriber.on_stop_static_init)

        @staticmethod
        def unsubscribe(subscriber: StopStaticInitSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.STOP_STATIC_INIT, subscriber.on_stop_static_init)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.STOP_STATIC_INIT)

    # ------------------------------------------

    class InterruptMeasuringSignal:
        """Эмиттится контроллером при аварийной остановке (HANDSHAKE_FAILED,
        DEVICE_LOST, COMMAND_ACK_TIMEOUT, COMMAND_REJECTED, READ_ERROR).

        В отличие от STOP_MEASURING, означает «связь с МК нарушена —
        не пытаться послать ему завершающие команды»."""

        @staticmethod
        def subscribe(subscriber: InterruptMeasuringSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.INTERRUPT_MEASURING, subscriber.on_interrupt_measuring)

        @staticmethod
        def unsubscribe(subscriber: InterruptMeasuringSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.INTERRUPT_MEASURING, subscriber.on_interrupt_measuring)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.INTERRUPT_MEASURING)

    # ------------------------------------------

    class ReadErrorSignal:
        """Эмиттится AsyncComPort.reading_loop при перехвате ComPortReadError.

        Слушает только контроллером — выставляет _force_stop. Сам ComPort на
        этот сигнал не подписан: о необходимости остановки он узнаёт через
        INTERRUPT_MEASURING, который контроллером эмиттит из stop()."""

        @staticmethod
        def subscribe(subscriber: ReadErrorSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.READ_ERROR, subscriber.on_read_error)

        @staticmethod
        def unsubscribe(subscriber: ReadErrorSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.READ_ERROR, subscriber.on_read_error)

        @staticmethod
        async def emit(err: 'ReadError') -> None:
            await McBus._emit(Signals.READ_ERROR, err)

    # =============================================================
    # ====================== Рукопожатие =========================
    # =============================================================

    class HandshakeInitSignal:
        """Эмиттится AsyncComPortImu в начале процедуры рукопожатия.

        Семантика: «начинается работа с неизвестным МК — обнулить
        накопленное состояние, чтобы первый байт нового сеанса
        разбирался с чистого листа»."""

        @staticmethod
        def subscribe(subscriber: HandshakeInitSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.HANDSHAKE_INIT, subscriber.on_handshake_init)

        @staticmethod
        def unsubscribe(subscriber: HandshakeInitSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.HANDSHAKE_INIT, subscriber.on_handshake_init)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.HANDSHAKE_INIT)

    # ------------------------------------------

    class HandshakeDoneSignal:
        """Эмиттится Decoder при получении ACK рукопожатия."""

        @staticmethod
        def subscribe(subscriber: HandshakeDoneSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.HANDSHAKE_DONE, subscriber.on_handshake_done)

        @staticmethod
        def unsubscribe(subscriber: HandshakeDoneSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.HANDSHAKE_DONE, subscriber.on_handshake_done)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.HANDSHAKE_DONE)

    # ------------------------------------------

    class HandshakeFailedSignal:
        """Эмиттится AsyncComPortImu при таймауте рукопожатия."""

        @staticmethod
        def subscribe(subscriber: HandshakeFailedSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.HANDSHAKE_FAILED, subscriber.on_handshake_failed)

        @staticmethod
        def unsubscribe(subscriber: HandshakeFailedSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.HANDSHAKE_FAILED, subscriber.on_handshake_failed)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.HANDSHAKE_FAILED)

    # =============================================================
    # ======================== Heartbeat ==========================
    # =============================================================

    class HeartbeatSentSignal:
        """Эмиттится AsyncComPortImu перед отправкой heartbeat."""

        @staticmethod
        def subscribe(subscriber: HeartbeatSentSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.HEARTBEAT_SENT, subscriber.on_heartbeat_sent)

        @staticmethod
        def unsubscribe(subscriber: HeartbeatSentSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.HEARTBEAT_SENT, subscriber.on_heartbeat_sent)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.HEARTBEAT_SENT)

    # ------------------------------------------

    class HeartbeatAckSignal:
        """Эмиттится Decoder при получении heartbeat ACK от МК."""

        @staticmethod
        def subscribe(subscriber: HeartbeatAckSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.HEARTBEAT_ACK, subscriber.on_heartbeat_ack)

        @staticmethod
        def unsubscribe(subscriber: HeartbeatAckSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.HEARTBEAT_ACK, subscriber.on_heartbeat_ack)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.HEARTBEAT_ACK)

    # ------------------------------------------

    class DeviceLostSignal:
        """Эмиттится AsyncComPortImu при таймауте heartbeat."""

        @staticmethod
        def subscribe(subscriber: DeviceLostSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.DEVICE_LOST, subscriber.on_device_lost)

        @staticmethod
        def unsubscribe(subscriber: DeviceLostSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.DEVICE_LOST, subscriber.on_device_lost)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.DEVICE_LOST)

    # =============================================================
    # ==================== Подтверждение команд ===================
    # =============================================================

    class CommandSentSignal:
        """Эмиттится AsyncComPortImu перед отправкой команды с подтверждением."""

        @staticmethod
        def subscribe(subscriber: CommandSentSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.COMMAND_SENT, subscriber.on_command_sent)

        @staticmethod
        def unsubscribe(subscriber: CommandSentSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.COMMAND_SENT, subscriber.on_command_sent)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.COMMAND_SENT)

    # ------------------------------------------

    class CommandAckSignal:
        """Эмиттится Decoder при получении подтверждения команды от МК."""

        @staticmethod
        def subscribe(subscriber: CommandAckSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.COMMAND_ACK, subscriber.on_command_ack)

        @staticmethod
        def unsubscribe(subscriber: CommandAckSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.COMMAND_ACK, subscriber.on_command_ack)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.COMMAND_ACK)

    # ------------------------------------------

    class CommandAckTimeoutSignal:
        """Эмиттится AsyncComPortImu при таймауте подтверждения команды."""

        @staticmethod
        def subscribe(subscriber: CommandAckTimeoutSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.COMMAND_ACK_TIMEOUT, subscriber.on_command_ack_timeout)

        @staticmethod
        def unsubscribe(subscriber: CommandAckTimeoutSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.COMMAND_ACK_TIMEOUT, subscriber.on_command_ack_timeout)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.COMMAND_ACK_TIMEOUT)

    # ------------------------------------------

    class CommandRejectedSignal:
        """Эмиттится ImuDecoder при получении от МК сообщения 'UNKNOWN_COMMAND'.

        Семантически — третий исход команды от ПК (наряду с COMMAND_ACK и
        COMMAND_ACK_TIMEOUT): МК ответил, но не понял команду — программная
        ошибка контракта ПК↔МК."""

        @staticmethod
        def subscribe(subscriber: CommandRejectedSubscriber) -> None:
            McBus._signal_bus.subscribe(Signals.COMMAND_REJECTED, subscriber.on_command_rejected)

        @staticmethod
        def unsubscribe(subscriber: CommandRejectedSubscriber) -> None:
            McBus._signal_bus.unsubscribe(Signals.COMMAND_REJECTED, subscriber.on_command_rejected)

        @staticmethod
        async def emit() -> None:
            await McBus._emit(Signals.COMMAND_REJECTED)

    # =============================================================
    # ===================== Интроспекция ==========================
    # =============================================================

    @staticmethod
    def get_subscribers() -> dict[Signals, list[object]]:
        """Возвращает текущих подписчиков всех сигналов в виде объектов-владельцев.

        Тонкая делегирующая обёртка над `SignalBus.get_subscribers()`,
        чтобы пользователи `McBus.` могли пользоваться им как единой точкой
        входа и не обращались к приватному модульному `McBus._bus` напрямую.

        Returns:
            dict[Signals, list[object]]: Словарь {сигнал: [объекты-подписчики]}.
                Сигналы без подписчиков попадают в результат с пустым списком.
        """
        return McBus._signal_bus.get_subscribers()

    # =============================================================

    def __init__(self, mc_logger: McLogger):
        McBus._logger = mc_logger.get_child_logger("McBus")

        # Передача данных
        self.new_byte = McBus.NewByteSignal()
        self.package_ready = McBus.PackageReadySignal()

        # Управление измерением
        self.stop_executing = McBus.StopExecutingSignal()
        self.start_measuring = McBus.StartMeasuringSignal()
        self.stop_measuring = McBus.StopMeasuringSignal()
        self.interrupt_measuring = McBus.InterruptMeasuringSignal()
        self.start_calibration = McBus.StartCalibrationSignal()
        self.start_static_init = McBus.StartStaticInitSignal()
        self.stop_calibration = McBus.StopCalibrationSignal()
        self.stop_static_init = McBus.StopStaticInitSignal()

        # Ошибки чтения
        self.read_error = McBus.ReadErrorSignal()

        # Рукопожатие
        self.handshake_init = McBus.HandshakeInitSignal()
        self.handshake_done = McBus.HandshakeDoneSignal()
        self.handshake_failed = McBus.HandshakeFailedSignal()

        # Heartbeat
        self.heartbeat_sent = McBus.HeartbeatSentSignal()
        self.heartbeat_ack = McBus.HeartbeatAckSignal()
        self.device_lost = McBus.DeviceLostSignal()

        # Подтверждение команд
        self.command_sent = McBus.CommandSentSignal()
        self.command_ack = McBus.CommandAckSignal()
        self.command_ack_timeout = McBus.CommandAckTimeoutSignal()
        self.command_rejected = McBus.CommandRejectedSignal()