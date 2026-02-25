# System imports
from enum import Enum
from typing import Callable

# External imports
import numpy as np

# User imports
from utils import float_to_csv_format
from .data_description import HX711Data, HX711DataIndexes
from .command import Command
from .utils import bytes_to_float, bytes_to_uint32, bytes_to_triaxial

#############################################

class PackageFormat:
    HX711Format = b'\x01'
    CommandFormat = b'\xAB'

# Стадии обработки данных из порта
class Stage(Enum):
    WantHeader = 1          # Ожидание заголовка посылки
    WantFormat = 2          # Ожидание формата посылки
    WantLength = 3          # Ожидание длины данных
    WantData = 4            # Ожидание данных посылки
    WantControlSum = 5      # Ожидание контрольной суммы

# -------------------------------------------

# Декодер посылок формата Гиронавт
class HX711Decoder:
    _header = [b'\xfb', b'\x01']    # Заголовок посылки

    def __init__(self):
        self.received_data: dict[int, HX711Data] = {}    # Словарь с полученными данными, где ключ - номер датчика
        self.input_command: dict[int, Command] = {}      # Словарь с поступившими командами, где ключ - номер датчика

        # Метод для декодирования полученной посылки (по умолчанию - self._bytes_to_hx711_data)
        self._decode_func: Callable[[list[bytes]], ...] = self._bytes_to_hx711_data

        self._stage: Stage = Stage.WantHeader       # Текущая стадия декодера
        self._received_bytes: list[bytes] = []      # Список поступивших байтов

        self._data_bt_index = 0     # Индекс байта данных в посылке
        self._package_size = 0      # Количество байт данных в посылке

        self._num_correct_packages = 0      # Количество пакетов, полученных без ошибок
        self._num_wrong_packages = 0        # Количество пакетов, полученных с ошибками
        self._num_unknown_packages = 0      # Количество пакетов с неизвестным форматом

    @property
    def data_len(self) -> int:
        return self._num_correct_packages

    def __str__(self):
        pass

    def save_received_data(self, filename: str) -> None:
        pass

    def byte_processing(self, bt: bytes) -> None:
        """ Обработка поступившего байта """

        self._received_bytes.append(bt)
        # print(f'stage = {self._stage}       bt = {bt}')

        match self._stage:
            case Stage.WantHeader:
                if self._received_bytes[-2::] == self._header:
                    self._stage = Stage.WantFormat
                    # Отчистим self._received_bytes от возможных прошлых записанных байтов
                    self._received_bytes = self._header.copy()
                    self._data_bt_index = 0

            case Stage.WantFormat:
                if bt == PackageFormat.HX711Format:
                    self._decode_func = self._bytes_to_hx711_data
                elif bt == PackageFormat.CommandFormat:
                    self._decode_func = self._bytes_to_command
                else:
                    self._stage = Stage.WantHeader
                    self._num_unknown_packages += 1
                    return

                self._stage = Stage.WantLength

            case Stage.WantLength:
                self._package_size = int.from_bytes(bt, 'big')
                self._stage = Stage.WantData

            case Stage.WantData:
                # Добавим в self._received_bytes все байты данных
                if self._data_bt_index < self._package_size - 1:
                    self._data_bt_index += 1
                else:
                    self._stage = Stage.WantControlSum

            case Stage.WantControlSum:
                # Проверка контрольной суммы
                if bt == self._count_control_sum(self._received_bytes):
                    self._decode_func(self._received_bytes)
                    self._num_correct_packages += 1
                else:
                    self._num_wrong_packages += 1

                self._stage = Stage.WantHeader
                self._received_bytes = []

    @staticmethod
    def _count_control_sum(data_bytes: list[bytes]) -> bytes:
        """ Вычисление контрольной суммы согласно документации """
        total = 0
        for b in data_bytes[:-1]:          # исключаем последний элемент (контр. сумму)
            total += b[0]       # преобразуем bytes в int
        return bytes([total & 0xFF])

    @staticmethod
    def _bytes_to_hx711_data(byte_list: list[bytes]) -> HX711Data: ...

    @staticmethod
    def _bytes_to_command(byte_list: list[bytes]) -> Command: ...
