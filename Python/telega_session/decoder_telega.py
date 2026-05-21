# System imports
import asyncio
from typing import NamedTuple, Optional, BinaryIO
import logging
from pathlib import Path

# External imports

# User imports
from async_mc_controller.signal_bus import McBus
from async_mc_controller.logger import McLogger
from async_mc_controller.decoding import DeviceDecoder, TriaxialData
from async_mc_controller.decoding.utils import *

#########################

class TelegaData(NamedTuple):
    package_num: int
    acc: TriaxialData
    gyro: TriaxialData
    temp: float
    dpp_code: int

    def __str__(self):
        return (f'PackageNum: {self.package_num}\n\n'

                f'Acc:  {self.acc.x_coord}\n'
                f'      {self.acc.y_coord}\n'
                f'      {self.acc.z_coord}\n\n'

                f'Gyro: {self.gyro.x_coord}\n'
                f'      {self.gyro.y_coord}\n'
                f'      {self.gyro.z_coord}\n\n'
                
                f'Temp:    {self.temp}\n'
                f'DppCode: {self.dpp_code}'
        )

# ------------------------------------------

# Описание начала индексов данных внутри посылки
class TelegaDataIndexes:
    """Смещения начала полей данных внутри бинарного пакета.
    Индексы отсчитываются от начала всей посылки, включая заголовок.
    """
    package_num = 4
    acc_index = 8
    gyro_index = 20
    temp_index = 32
    dpp_code_index = 36

# ------------------------------------------

class DecoderTelega(DeviceDecoder[TelegaData]):
    # Зададим заголовок посылки
    _header = [b'\x7e', b'\xe7']

    # Получаемые текстовые сообщения от МК
    _handshake_ack: str = "TELEGA_STM32_ACK"            # Ожидаемое сообщение рукопожатия
    _heartbeat_ack: str = "TELEGA_STM32_ALIVE"          # Ожидаемое сообщение heartbeat
    _command_ack: str = "CONFIRM_RECEIVED_COMMAND"      # Ожидаемое подтверждение команды
    _command_rejected_msg: str = "UNKNOWN_COMMAND"      # Отказ МК: команда не распознана

    _end_of_calibration_msg: str = "END_OF_CALIBRATION"     # Сообщение о завершение калибровки
    _end_of_static_init_msg: str = "END_OF_STATIC_INIT"     # Сообщение о завершение набора статического буфера

    # Константы форматов пакетов протокола
    _DataFormatBt: bytes = b'\xC8'       # Пакет с данными
    _MessageFormatBt: bytes = b'\xCD'    # Текстовое сообщение

    def __init__(self, signal_bus: McBus, mc_logger: McLogger):
        super().__init__(signal_bus, mc_logger)
        self._telega_decoder_logger: logging.Logger = mc_logger.get_child_logger("BaseDecoder.DeviceDecoder.TelegaDecoder")

        # Сохраним обработчики _end_of_calibration_msg и _end_of_static_init_msg
        self._msg_to_handler[self._end_of_calibration_msg] = self._end_of_calibration
        self._msg_to_handler[self._end_of_static_init_msg] = self._end_of_static_init

        # Сохраним переданный путь к бинарному файлу
        self._bin_file: Optional[BinaryIO] = None

    # =============================================================
    # ======= Методы для работы в контекстном менеджере ===========
    # =============================================================

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """ Закроем бинарный файл и вызовем родительский __aexit__ """
        self._close_bin_file()
        return await super().__aexit__(exc_type, exc_val, exc_tb)

    # =============================================================
    # =================== Обработчики сигналов ====================
    # =============================================================

    async def on_byte_received(self, bt: bytes) -> None:
        """ При получении нового байта сохраним его в self._bin_file """
        if self._bin_file:
            self._bin_file.write(bt)
        await super().on_byte_received(bt)

    # =============================================================
    # =================== Публичные методы ========================
    # =============================================================

    def save_received_data(self, filepath: Path, sep: str = ' ') -> None:
        """Сохраняет все накопленные данные декодера в CSV-файл.

        Формат: PackageNum, AccX, AccY, AccZ, GyroX, GyroY, GyroZ.
        Числа с плавающей точкой записываются с точкой как десятичным
        разделителем — поэтому разделитель полей по умолчанию пробел.

        Args:
            filepath (Path): Путь к файлу сохранения.
            sep (str):       Разделитель полей. По умолчанию пробел.

        Raises:
            ValueError: Если нет данных для сохранения.
        """
        if not self.received_data:
            raise ValueError('Нет данных для сохранения. Список received_data пуст.')

        file_path = Path(filepath)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(
                f'PackageNum{sep}DppCode{sep}'
                f'AccX{sep}AccY{sep}AccZ{sep}'
                f'GyroX{sep}GyroY{sep}GyroZ\n'
            )
            for data in self.received_data:
                file.write(
                    f'{data.package_num}{sep}'
                    f'{data.dpp_code}{sep}'
                    f'{data.acc.x_coord}{sep}{data.acc.y_coord}{sep}{data.acc.z_coord}{sep}'
                    f'{data.gyro.x_coord}{sep}{data.gyro.y_coord}{sep}{data.gyro.z_coord}\n'
                )

    # =============================================================
    # ================= Внутренняя логика =========================
    # =============================================================

    def setup_bin_file(self, bin_file_path: Path) -> None:
        """ Конфигурация бинарного файла для сохранения полученных байтов """
        if bin_file_path.exists():
            self._telega_decoder_logger.warning(f"Переданный файл {bin_file_path} уже существует! "
                                                f"Его данные будут перезаписаны")

        # Создадим новый бинарный файл с новым bin_file_path
        bin_file_path.parent.mkdir(parents=True, exist_ok=True)
        self._close_bin_file()
        self._bin_file = open(bin_file_path, "wb")

    def _close_bin_file(self) -> None:
        """ Закрытие self._bin_file """
        if self._bin_file:
            self._telega_decoder_logger.debug(f"Закрытие файла {self._bin_file.name}")
            self._bin_file.close()

    def _bytes_to_protocol_data(self, byte_list: list[bytes]) -> TelegaData:
        """ Декодирование байтов в пакет данных TelegaData """
        return TelegaData(
            package_num=    bytes_to_uint32(byte_list[TelegaDataIndexes.package_num: TelegaDataIndexes.package_num + 4]),
            acc=            bytes_to_triaxial(byte_list[TelegaDataIndexes.acc_index: TelegaDataIndexes.acc_index + 12]),
            gyro=           bytes_to_triaxial(byte_list[TelegaDataIndexes.gyro_index: TelegaDataIndexes.gyro_index + 12]),
            temp=           bytes_to_float(byte_list[TelegaDataIndexes.temp_index: TelegaDataIndexes.temp_index + 4]),
            dpp_code=       bytes_to_int32(byte_list[TelegaDataIndexes.dpp_code_index: TelegaDataIndexes.dpp_code_index + 4])
        )

    async def _end_of_calibration(self) -> None:
        """ Процедура завершения калибровки """
        await self._bus.stop_calibration.emit()

    async def _end_of_static_init(self) -> None:
        """ Процедура завершения набора статического буфера перед проездом """
        await self._bus.stop_static_init.emit()
