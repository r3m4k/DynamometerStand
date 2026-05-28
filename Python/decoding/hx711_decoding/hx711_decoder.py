# -*- coding: utf-8 -*-
"""Модуль декодера протокола передачи данных АЦП HX711.

Содержит конечный автомат для разбора байтового потока, выделения пакетов,
проверки контрольной суммы и вызова соответствующих обработчиков для данных
или команд.

Классы:
    PackageFormat: Константы форматов пакетов.
    Stage: Перечисление состояний декодера.
    HX711Decoder: Основной класс декодера.
"""

# System imports
from enum import Enum
from typing import Callable
from pprint import pformat
from pathlib import Path

# External imports

# User imports
from decoding.command import Command
from decoding.hx711_decoding.hx711_data_description import HX711Data, HX711DataIndexes, HX711Gain
from decoding.utils import bytes_to_uint32, bytes_to_int32, bytes_to_uint8

#############################################

class PackageFormat:
    """Константы форматов пакетов протокола."""
    HX711Format = b'\x01'      # Байт, обозначающий пакет с данными HX711
    CommandFormat = b'\xAB'     # Байт, обозначающий командный пакет

# Стадии обработки данных из порта
class Stage(Enum):
    """Возможные состояния конечного автомата декодера."""
    WantHeader = 1          # Ожидание заголовка посылки
    WantFormat = 2          # Ожидание байта формата посылки
    WantLength = 3          # Ожидание байта длины данных
    WantData = 4            # Ожидание данных посылки
    WantControlSum = 5      # Ожидание контрольной суммы

# -------------------------------------------

# Декодер посылок данных АЦП HX711
class HX711Decoder:
    """Декодер потока байтов от микроконтроллера в структурированные данные.

    Реализует конечный автомат для разбора данных с АЦП:
    - Поиск заголовка (0xFB, 0x01).
    - Определение формата пакета (данные HX711 или команда).
    - Чтение длины, данных и контрольной суммы.
    - Проверка целостности и вызов соответствующей функции декодирования.

    Атрибуты:
        received_data (dict[int, list[HX711Data]]): Словарь, где ключ — идентификатор датчика,
            а значение — список принятых от него пакетов (история).
        input_command (list[Command]): Список принятых команд (объекты Command).
    """

    _header = [b'\xc8', b'\x8c']    # Заголовок посылки (2 байта)

    def __init__(self):
        """Инициализирует декодер, сбрасывая все внутренние состояния."""
        self.received_data: dict[int, list[HX711Data]] = {}     # Словарь с полученными данными, где ключ - номер датчика
        self.input_command: list[Command] = []                  # Список поступивших команд

        # Метод для декодирования полученной посылки (по умолчанию - self._bytes_to_hx711_data)
        self._decode_func: Callable[[list[bytes]], None] = self._bytes_to_hx711_data

        self._stage: Stage = Stage.WantHeader       # Текущая стадия декодера
        self._received_bytes: list[bytes] = []      # Список поступивших байтов

        self._data_bt_index = 0     # Индекс байта данных в посылке
        self._package_size = 0      # Количество байт данных в посылке

        self._num_correct_packages = 0      # Количество пакетов, полученных без ошибок
        self._num_wrong_packages = 0        # Количество пакетов, полученных с ошибками
        self._num_unknown_packages = 0      # Количество пакетов с неизвестным форматом

    @property
    def data_len(self) -> int:
        """Возвращает максимальное количество пакетов среди всех датчиков."""
        return max((len(v) for v in self.received_data.values()), default=0)

    def __str__(self) -> str:
        """Строковое представление состояния декодера.
        Returns:
            str: Многострочная строка с информацией о декодере.
        """
        return (
            f'🔍 Информация о {self.__class__.__name__}:\n'
            f'| Количество корректно принятых пакетов данных:     {self._num_correct_packages} из {self._num_correct_packages + self._num_wrong_packages + self._num_unknown_packages}\n'
            f'| Количество пакетов данных, полученных с ошибкой:  {self._num_wrong_packages} из {self._num_correct_packages + self._num_wrong_packages + self._num_unknown_packages}\n'
            f'| Количество пакетов с неизвестным форматом:        {self._num_unknown_packages} из {self._num_correct_packages + self._num_wrong_packages + self._num_unknown_packages}\n'
            f'| -----------------------------------------------\n'
            )

    def save_received_data(self, filepath: str | Path, sep: str = ',') -> None:
        """Сохраняет все накопленные данные декодера в файл.

        Args:
            filepath (str | Path): Путь к файлу сохранения.
            sep (str, optional): Разделитель полей в выходном файле. По умолчанию запятая.

        Формат файла:
            Первая строка — заголовок: SensorId{sep}Time{sep}ADCValue{sep}Gain
            Последующие строки: для каждого временного индекса (начиная с 0)
            последовательно выводятся данные всех датчиков в порядке возрастания
            их идентификаторов. Если у какого-то датчика на текущем индексе нет
            данных, строка для него пропускается.
        """
        if not self.received_data:
            raise ValueError("Нет данных для сохранения. Словарь received_data пуст.")

        # Преобразуем строку в объект Path
        file_path = Path(filepath)
        # Создаём родительскую директорию, если её нет
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Открываем файл на запись (используем явно путь как строку или объект Path)
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(f'SensorId{sep}Time{sep}ADCValue{sep}Gain\n')

            for index in range(self.data_len):
                for sensor_id in sorted(self.received_data.keys()):
                    try:
                        data = self.received_data[sensor_id][index]
                        file.write(f"{sensor_id}{sep}{data.time}{sep}{data.adc_value}{sep}{data.gain.to_string()}\n")
                    except IndexError:
                        pass

    def byte_processing(self, bt: bytes) -> None:
        """Обрабатывает один входящий байт, продвигая конечный автомат.

        Байт добавляется во внутренний буфер, затем анализируется текущая стадия.
        При завершении пакета вызывается соответствующая функция декодирования.

        Args:
            bt (bytes): Один байт для обработки.
        """
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
        """Вычисляет контрольную сумму пакета (XOR-сумма с исключением последнего байта).

        Args:
            data_bytes (list[bytes]): Список байтов всей посылки (включая CRC).

        Returns:
            bytes: Один байт — вычисленная контрольная сумма.
        """
        total = 0
        # Исключим последний байт (полученную контрольную сумму) из расчёта контрольной суммы
        for b in data_bytes[:-1]:
            total += int.from_bytes(b, 'big')
        return bytes([total & 0xFF])

    def _bytes_to_hx711_data(self, byte_list: list[bytes]) -> None:
        """Декодирует список байт в структуру HX711Data и сохраняет в received_data.

        Ожидается, что byte_list содержит полную посылку (заголовок, формат, длину,
        данные, CRC). Индексы полей берутся из HX711DataIndexes.

        Args:
            byte_list (list[bytes]): Список байтов всей посылки.
        """
        received_package = HX711Data(
            time=bytes_to_uint32(byte_list[HX711DataIndexes.time_index: HX711DataIndexes.time_index + 4]),
            id=bytes_to_uint8(byte_list[HX711DataIndexes.id_index: HX711DataIndexes.id_index + 1]),
            adc_value=bytes_to_int32(byte_list[HX711DataIndexes.adc_index: HX711DataIndexes.adc_index + 4]),
            gain=HX711Gain(bytes_to_uint8(byte_list[HX711DataIndexes.gain_index: HX711DataIndexes.gain_index + 1])),
        )
        # Добавляем пакет в историю для соответствующего ID
        if received_package.id not in self.received_data:
            self.received_data[received_package.id] = []
        self.received_data[received_package.id].append(received_package)

    def _bytes_to_command(self, byte_list: list[bytes]) -> None:
        """Декодирует список байт в объект Command и добавляет в список команд.

        Args:
            byte_list (list[bytes]): Список байтов всей посылки.
        """
        self.input_command.append(Command(byte_list))
