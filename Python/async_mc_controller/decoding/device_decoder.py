# -*- coding: utf-8 -*-
"""Модуль декодера протокола получения данных от МК
без привязки к протоколу передачи данных.

Содержит константы форматов пакетов и конкретную реализацию декодера
для протокола IMU, унаследованную от BaseDecoder.

Классы:
    PackageFormat: Константы форматов пакетов протокола IMU.
    DeviceDecoder: Декодер для работы с МК с помощью сигнальной шины.
"""

# System imports
from abc import abstractmethod
from collections.abc import Coroutine
from typing import Any, Callable, Optional, TypeAlias, Awaitable

# External imports

# User imports
from async_mc_controller.logger import McLogger
from async_mc_controller.signal_bus import McBus
from async_mc_controller.decoding.base_decoder import BaseDecoder, Stage, T

#############################################

# Тип сохранённого состояния автомата (см. DeviceDecoder._save_state)
SavedState: TypeAlias = tuple[
    Stage,
    list[bytes],
    int,
    int,
    Callable[[list[bytes]], Coroutine[Any, Any, None]],
]

# ------------------------------------------

class DeviceDecoder(BaseDecoder[T]):
    """Декодер передачи данных от МК без конкретного протокола.

    Расширяет BaseDecoder логикой взаимодействия с сигнальной шиной,
    добавляет форматы пакетов, методы декодирования данных / текстовых
    сообщений (ACK рукопожатия, heartbeat, подтверждения команды),
    а также механизм сохранения и восстановления состояния автомата
    на время обработки короткого ACK-пакета.
    """

    # Получаемые текстовые сообщения от МК
    _handshake_ack: Optional[str] = None           # Ожидаемое сообщение рукопожатия
    _heartbeat_ack: Optional[str] = None           # Ожидаемое сообщение heartbeat
    _command_ack: Optional[str] = None             # Ожидаемое подтверждение команды
    _command_rejected_msg: Optional[str] = None    # Отказ МК: команда не распознана

    # Константы форматов пакетов протокола
    _DataFormatBt: Optional[bytes] = None       # Пакет с данными
    _MessageFormatBt: Optional[bytes] = None    # Текстовое сообщение

    def __init__(self, signal_bus: McBus, mc_logger: McLogger):
        super().__init__(logger=mc_logger.get_child_logger("BaseDecoder"))

        # Проверим текстовые сообщения
        if any(msg is None for msg in [self._handshake_ack, self._heartbeat_ack,
                                       self._command_ack, self._command_rejected_msg]):
            raise RuntimeError("Задайте все текстовые сообщения, получаемые от МК!\n"
                               f"| _handshake_ack = {self._handshake_ack}\n"
                               f"| _heartbeat_ack = {self._heartbeat_ack}\n"
                               f"| _command_ack = {self._command_ack}\n"
                               f"| _command_rejected_msg = {self._command_rejected_msg}\n")

        # Проверим константы форматов пакетов
        if any(bt is None for bt in [self._DataFormatBt, self._MessageFormatBt]):
            raise RuntimeError("Задайте константы форматов пакетов протокола!")

        # Словарь для соответствия формата пакета и функции для его декодирования.
        # Может быть расширен в наследнике!
        self._fmt_to_decode_func: dict[bytes, Callable[[list[bytes]], Coroutine[Any, Any, None]]] = {
            self._DataFormatBt: self._bytes_to_data,
            self._MessageFormatBt: self._bytes_to_message
        }

        # Словарь для соответствия полученного сообщения и методом для отработки.
        # Может быть расширен в наследнике!
        self._msg_to_handler: dict[str, Callable[[], Awaitable[None]]] = {
            self._handshake_ack: self._handshake_ack_handler,
            self._heartbeat_ack: self._heartbeat_ack_handler,
            self._command_ack: self._command_ack_handler,
            self._command_rejected_msg: self._command_rejected_msg_handler,
        }

        self._device_decoder_logger = mc_logger.get_child_logger("BaseDecoder.DeviceDecoder")
        self._bus: McBus = signal_bus       # Используемая сигнальная шина
        self.received_data: list[T] = []    # Список полученных пакетов данных

        # Сохранённое состояние автомата на время обработки heartbeat / команды
        self._saved_state: Optional[SavedState] = None

        # Самостоятельная подписка на сигналы шины
        self._bus.new_byte.subscribe(self)
        self._bus.handshake_init.subscribe(self)
        self._bus.heartbeat_sent.subscribe(self)
        self._bus.command_sent.subscribe(self)
        self._bus.command_ack_timeout.subscribe(self)

    # =============================================================
    # ======= Методы для работы в контекстном менеджере ===========
    # =============================================================

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Отпишемся от всех сигналов шины."""
        self._bus.new_byte.unsubscribe(self)
        self._bus.handshake_init.unsubscribe(self)
        self._bus.heartbeat_sent.unsubscribe(self)
        self._bus.command_sent.unsubscribe(self)
        self._bus.command_ack_timeout.unsubscribe(self)

        return await super().__aexit__(exc_type, exc_val, exc_tb)

    # =============================================================
    # =================== Обработчики сигналов ====================
    # =============================================================

    async def on_byte_received(self, bt: bytes) -> None:
        """Обработчик сигнала NEW_BYTE — кладёт байт во внутреннюю очередь.

        Args:
            bt (bytes): Один полученный байт.
        """
        await self._byte_queue.put(bt)
        # self._device_decoder_logger.debug(f'Получен новый байт: bt = {bt}')

    async def on_handshake_init(self) -> None:
        """Обработчик сигнала HANDSHAKE_INIT — чистит состояние FSM.

        Семантика сигнала: «начинается работа с неизвестным МК», поэтому
        накопленное состояние декодера обнуляется, чтобы первый же байт
        нового сеанса разбирался с чистого листа.
        """
        self._clear()

    async def on_heartbeat_sent(self) -> None:
        """Обработчик сигнала HEARTBEAT_SENT — сохраняет состояние автомата.

        Переключает декодер в WantHeader для корректного приёма ACK пакета
        heartbeat. Состояние восстанавливается в _restore_state() после ACK.
        """
        self._save_state('heartbeat')

    async def on_command_sent(self) -> None:
        """Обработчик сигнала COMMAND_SENT — сохраняет состояние автомата.

        Переключает декодер в WantHeader для корректного приёма подтверждения
        команды от МК. Состояние восстанавливается в _restore_state() после ACK
        либо после COMMAND_ACK_TIMEOUT (через on_command_ack_timeout).
        """
        self._save_state('подтверждения команды')

    async def on_command_ack_timeout(self) -> None:
        """Обработчик сигнала COMMAND_ACK_TIMEOUT — восстанавливает состояние.

        Если ACK не пришёл за отведённое время, сохранённое состояние
        нужно откатить — иначе следующий on_command_sent / on_heartbeat_sent
        перепишет _saved_state и изначальное состояние будет потеряно.
        Декодер возвращается в исходный режим работы (до отправки команды).
        """
        if self._saved_state is None:
            self._device_decoder_logger.warning('COMMAND_ACK_TIMEOUT без предварительно сохранённого состояния')
            return
        self._restore_state()
        self._device_decoder_logger.warning('Состояние декодера восстановлено после таймаута команды')

    # =============================================================
    # =================== Публичные методы ========================
    # =============================================================

    @property
    def data_len(self) -> int:
        """Возвращает количество накопленных пакетов данных IMU."""
        return len(self.received_data)

    # =============================================================
    # ================= Внутренняя логика =========================
    # =============================================================

    async def _package_sending(self, data: T) -> None:
        """ Эмиттирование полученного пакета в сигнальную шины. """
        await self._bus.package_ready.emit(data)

    def _clear(self) -> None:
        """Очищает состояние DeviceDecoder.

        Расширяет BaseDecoder._clear() очисткой received_data и _saved_state.
        Используется list.clear() вместо переприсваивания, чтобы внешние
        ссылки на received_data (если они есть) оставались валидными.

        Вызывается:
          - из BaseDecoder._reset() при входе в контекстный менеджер
            (через шаблонный метод — полиморфизм подтянет эту реализацию);
          - из BaseDecoder.on_handshake_init() при получении сигнала
            HANDSHAKE_INIT (начало работы с новым МК).
        """
        super()._clear()
        self.received_data.clear()
        self._saved_state = None
        self._device_decoder_logger.debug('Состояние DeviceDecoder очищено')

    def _get_decode_func(self, fmt: bytes) -> Optional[Callable[[list[bytes]], Coroutine[Any, Any, None]]]:
        """Возвращает функцию декодирования по байту формата пакета.

        Args:
            fmt (bytes): Байт формата из пакета.

        Returns:
            Callable или None если формат неизвестен.
        """
        # self._device_decoder_logger.debug(f'Получен байт формата посылки: fmt = {fmt}')
        if fmt in self._fmt_to_decode_func.keys():
            return self._fmt_to_decode_func[fmt]
        return None

    @abstractmethod
    def _bytes_to_protocol_data(self, byte_list: list[bytes]) -> T:
        """ Декодирование байтов в пакет данных, отправляемый МК """
        ...

    async def _bytes_to_data(self, byte_list: list[bytes]) -> None:
        """Декодирует список байтов в структуру T
        с сохранением в received_data и в _package_queue.

        Метод должен быть реализован в наследнике!

        Args:
            byte_list (list[bytes]): Список байтов всей посылки.
        """
        data: T = self._bytes_to_protocol_data(byte_list)
        self.received_data.append(data)
        await self._package_queue.put(data)

    async def _bytes_to_message(self, byte_list: list[bytes]) -> None:
        """Декодирует текстовое сообщение от МК и вызывает соответствующий обработчик.

        Args:
            byte_list (list[bytes]): Список байтов всей посылки.
        """
        # Данные начинаются с индекса 4 (2 байта заголовка + формат + длина)
        # и заканчиваются до последнего байта (контрольная сумма)
        message_bytes = b''.join(byte_list[4:-1])
        try:
            message = message_bytes.decode('ascii')
        except UnicodeDecodeError:
            self._device_decoder_logger.warning(f'Сообщение от МК содержит невалидные ASCII байты: {message_bytes!r}')
            return

        self._device_decoder_logger.debug(f'Получено сообщение {message}')

        if message in self._msg_to_handler.keys():
            coro_handler = self._msg_to_handler[message]
            await coro_handler()
        else:
            self._device_decoder_logger.warning(f'Неизвестное сообщение от МК: "{message}"')


    def _save_state(self, reason: str) -> None:
        """Сохраняет полное состояние конечного автомата и переводит его в WantHeader.

        Вызывается перед отправкой heartbeat / команды, чтобы декодер корректно
        принял короткий ACK-пакет, а после — восстановил разбор прерванной посылки
        (через _restore_state либо через обработчик таймаута).

        Args:
            reason (str): Причина сохранения для лога (например, 'heartbeat',
                'подтверждения команды'). Используется только в DEBUG-логе.
        """
        self._saved_state = (
            self._stage,
            self._received_bytes.copy(),
            self._data_bt_index,
            self._package_size,
            self._decode_func,
        )

        prev_stage = self._stage
        prev_buf_len = len(self._received_bytes)
        queue_size = self._byte_queue.qsize()

        self._stage = Stage.WantHeader
        self._received_bytes = []
        self._data_bt_index = 0
        self._package_size = 0
        self._device_decoder_logger.debug(
            f'Состояние декодера сохранено для {reason} '
            f'(stage={prev_stage.name}, буфер={prev_buf_len} байт, '
            f'очередь={queue_size} байт)'
        )

    def _restore_state(self) -> None:
        """Восстанавливает состояние конечного автомата из _saved_state.

        Используется после получения ACK heartbeat / подтверждения команды,
        а также после таймаута команды. Вызывающий код логирует причину
        восстановления сам.
        """
        if self._saved_state is None:
            self._device_decoder_logger.warning('Попытка восстановить состояние декодера без предварительного сохранения')
            return

        (self._stage,
         self._received_bytes,
         self._data_bt_index,
         self._package_size,
         self._decode_func) = self._saved_state

        self._saved_state = None
        self._device_decoder_logger.debug('Состояние декодера восстановлено')

    # =============================================================
    # ========= Методы для отработки полученных сообщений =========
    # =============================================================

    async def _handshake_ack_handler(self) -> None:
        await self._bus.handshake_done.emit()
        self._device_decoder_logger.info(f'ACK рукопожатия получен: "{self._handshake_ack}"')

    async def _heartbeat_ack_handler(self) -> None:
        self._restore_state()
        await self._bus.heartbeat_ack.emit()
        self._device_decoder_logger.debug(f'ACK heartbeat получен: "{self._heartbeat_ack}"')

    async def _command_ack_handler(self) -> None:
        self._restore_state()
        await self._bus.command_ack.emit()
        self._device_decoder_logger.debug(f'Подтверждение команды получено: "{self._command_ack}"')

    async def _command_rejected_msg_handler(self) -> None:
        self._restore_state()
        await self._bus.command_rejected.emit()
        self._device_decoder_logger.warning(f'МК отверг команду: "{self._command_rejected_msg}"')


