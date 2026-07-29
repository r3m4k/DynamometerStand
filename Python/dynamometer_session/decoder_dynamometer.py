# -*- coding: utf-8 -*-
"""Модуль декодера данных HX711 для динамометрического стенда."""

# System imports
from pathlib import Path
from typing import BinaryIO, Optional

# User imports
from decoding.hx711_decoding import HX711Data, HX711DataIndexes, HX711Gain
from decoding.utils import bytes_to_int32, bytes_to_uint8, bytes_to_uint32
from dynamometer_session.base_decoder import DeviceDecoder
from dynamometer_session.mc_logger import McLogger
from dynamometer_session.signal_bus import McBus

##########################################################


class DynamometerDecoder(DeviceDecoder[HX711Data]):
    """Декодер протокола МК, передающего пакеты HX711Data."""

    # Заголовок и текстовые ACK заданы в embedded-коде текущего проекта.
    _header = [b"\xC8", b"\x8C"]

    _handshake_ack = "HX711_STM32_ACK"
    _heartbeat_ack = "HX711_STM32_ALIVE"

    def __init__(self, bus: McBus, mc_logger: McLogger):
        """Инициализирует декодер и опциональный бинарный файл сырого потока."""
        super().__init__(bus, mc_logger)
        self._bin_file: Optional[BinaryIO] = None

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Закрывает бинарный файл при завершении сессии."""
        self._close_bin_file()
        return await super().__aexit__(exc_type, exc_val, exc_tb)

    async def on_byte_received(self, bt: bytes) -> None:
        """Сохраняет сырой байт в bin-файл и передаёт его базовому декодеру."""
        if self._bin_file is not None:
            self._bin_file.write(bt)
        await super().on_byte_received(bt)

    def setup_bin_file(self, bin_file_path: Optional[Path]) -> None:
        """Открывает файл для сохранения сырого входящего потока байтов."""
        if bin_file_path is None:
            return
        bin_file_path.parent.mkdir(parents=True, exist_ok=True)
        self._close_bin_file()
        self._bin_file = open(bin_file_path, "wb")

    def _close_bin_file(self) -> None:
        """Закрывает файл сырого потока, если он был открыт."""
        if self._bin_file is not None:
            self._bin_file.close()
            self._bin_file = None

    def _bytes_to_protocol_data(self, byte_list: list[bytes]) -> HX711Data:
        """Преобразует байты data-пакета в структуру HX711Data."""
        return HX711Data(
            time=bytes_to_uint32(byte_list[HX711DataIndexes.time_index: HX711DataIndexes.time_index + 4]),
            id=bytes_to_uint8(byte_list[HX711DataIndexes.id_index: HX711DataIndexes.id_index + 1]),
            adc_value=bytes_to_int32(byte_list[HX711DataIndexes.adc_index: HX711DataIndexes.adc_index + 4]),
            gain=HX711Gain(bytes_to_uint8(byte_list[HX711DataIndexes.gain_index: HX711DataIndexes.gain_index + 1])),
        )
