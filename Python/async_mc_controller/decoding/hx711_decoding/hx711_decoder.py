# -*- coding: utf-8 -*-
"""Модуль декодера протокола получения данных HX711.

Содержит константы форматов пакетов и конкретную реализацию декодера
для протокола HX711, унаследованную от BaseDecoder.

Классы:
    PackageFormat:  Константы форматов пакетов протокола HX711.
    HX711Decoder:   Декодер протокола HX711.
"""

# System imports
from collections.abc import Coroutine
from pathlib import Path
from typing import Any, Callable, Optional, TypeAlias

# External imports

# User imports
from async_mc_controller.logger import mc_logger
from async_mc_controller.signal_bus import bus
from async_mc_controller.decoding.base_decoder import BaseDecoder, Stage
from async_mc_controller.decoding.hx711_decoding.hx711_data_description import HX711Data, HX711DataIndexes, HX711Gain
from async_mc_controller.decoding.utils import *

#############################################

_logger = mc_logger.get_logger('MC.BaseDecoder.HX711Decoder')

# Тип сохранённого состояния автомата (см. HX711Decoder._save_state)
SavedState: TypeAlias = tuple[
    Stage,
    list[bytes],
    int,
    int,
    Callable[[list[bytes]], Coroutine[Any, Any, None]],
]

# ------------------------------------------

class PackageFormat:
    """Константы форматов пакетов протокола HX711."""
    ImuFormat:   bytes = b'\x01'    # Пакет с данными HX711
    MessageFormat: bytes = b'\xCD'  # Текстовое сообщение (ACK рукопожатия / heartbeat и тд)

# ------------------------------------------

class HX711Decoder(BaseDecoder[HX711Data]):
    """Декодер протокола передачи данных АЦП HX711.

    Расширяет BaseDecoder логикой HX711-протокола: добавляет заголовок,
    форматы пакетов, методы декодирования данных / команд / текстовых
    сообщений (ACK рукопожатия, heartbeat, подтверждения команды),
    а также механизм сохранения и восстановления состояния автомата
    на время обработки короткого ACK-пакета.

    Дополнительное взаимодействие с шиной (поверх базового NEW_BYTE / PACKAGE_READY):
        - подписка: HANDSHAKE_INIT (начало работы с новым МК → _clear()
                    очищает FSM и счётчики, очереди и задачи не трогает);
        - подписка: HEARTBEAT_SENT, COMMAND_SENT (сохранить состояние);
        - подписка: COMMAND_ACK_TIMEOUT (откатить состояние при таймауте);
        - эмиссия:  HANDSHAKE_DONE, HEARTBEAT_ACK, COMMAND_ACK,
                    COMMAND_REJECTED (напрямую из _bytes_to_message).

    Attributes:
        received_data (list[ImuData]): Плоский список принятых пакетов
            данных HX711 в порядке поступления.

    Пример использования:
        decoder = HX711Decoder()
        async with decoder:
            await controller.start()
            await controller.stop()
    """

    _header: list[bytes] = [b'\xc8', b'\x8c']       # Заголовок посылки (2 байта)

    _handshake_ack: str = 'HX711_STM32_ACK'         # Ожидаемое сообщение рукопожатия
    _heartbeat_ack: str = 'HX711_STM32_ALIVE'       # Ожидаемое сообщение heartbeat
    _command_ack: str = 'CONFIRM_RECEIVED_COMMAND'  # Ожидаемое подтверждение команды
    _command_rejected_msg: str = 'UNKNOWN_COMMAND'  # Отказ МК: команда не распознана

    def __init__(self):
        super().__init__()

        # Словарь с полученными данными, где ключ - номер датчика
        self.received_data: dict[int, list[HX711Data]] = {}

        # Сохранённое состояние автомата на время обработки heartbeat / команды
        self._saved_state: Optional[SavedState] = None

        # Самостоятельная подписка на HX711-специфичные сигналы шины
        bus.handshake_init.subscribe(self)
        bus.heartbeat_sent.subscribe(self)
        bus.command_sent.subscribe(self)
        bus.command_ack_timeout.subscribe(self)

    # =============================================================
    # =================== Обработчики сигналов ====================
    # =============================================================

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
            _logger.warning('COMMAND_ACK_TIMEOUT без предварительно сохранённого состояния')
            return
        self._restore_state()
        _logger.warning('Состояние декодера восстановлено после таймаута команды')

    # =============================================================
    # =================== Публичные методы ========================
    # =============================================================

    @property
    def data_len(self) -> int:
        """Возвращает максимальное количество пакетов среди всех датчиков."""
        return max((len(v) for v in self.received_data.values()), default=0)

    def __str__(self) -> str:
        total = self._num_correct_packages + self._num_wrong_packages + self._num_unknown_packages
        return (
            f'🔍 Информация о {self.__class__.__name__}:\n'
            f'| Количество корректно принятых пакетов данных:     {self._num_correct_packages} из {total}\n'
            f'| Количество пакетов данных, полученных с ошибкой:  {self._num_wrong_packages} из {total}\n'
            f'| Количество пакетов с неизвестным форматом:        {self._num_unknown_packages} из {total}\n'
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
                        file.write(f"{sensor_id}{sep}{data.package_num}{sep}{data.adc_value}{sep}{data.gain.to_string()}\n")
                    except IndexError:
                        pass

    # =============================================================
    # ================= Внутренняя логика =========================
    # =============================================================

    def _clear(self) -> None:
        """Очищает состояние HX711Decoder.

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
        _logger.debug('Состояние HX711Decoder очищено')

    def _get_decode_func(self, fmt: bytes) -> Optional[Callable[[list[bytes]], Coroutine[Any, Any, None]]]:
        """Возвращает функцию декодирования по байту формата пакета.

        Args:
            fmt (bytes): Байт формата из пакета.

        Returns:
            Callable или None если формат неизвестен.
        """
        if fmt == PackageFormat.ImuFormat:
            return self._bytes_to_imu_data
        elif fmt == PackageFormat.MessageFormat:
            return self._bytes_to_message
        return None

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

        prev_stage   = self._stage
        prev_buf_len = len(self._received_bytes)
        queue_size   = self._byte_queue.qsize()

        self._stage = Stage.WantHeader
        self._received_bytes = []
        self._data_bt_index = 0
        self._package_size = 0
        _logger.debug(
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
            _logger.warning('Попытка восстановить состояние декодера без предварительного сохранения')
            return

        (self._stage,
         self._received_bytes,
         self._data_bt_index,
         self._package_size,
         self._decode_func) = self._saved_state

        self._saved_state = None
        _logger.debug('Состояние декодера восстановлено')

    async def _bytes_to_imu_data(self, byte_list: list[bytes]) -> None:
        """Декодирует список байтов в структуру HX711Data.

        Сохраняет пакет в received_data и кладёт в _package_queue.

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

        await self._package_queue.put(received_package)

    async def _bytes_to_message(self, byte_list: list[bytes]) -> None:
        """Декодирует текстовое сообщение от МК.

        Различает четыре известных сообщения:
          - 'HX711_STM32_ACK'           — ACK рукопожатия → HANDSHAKE_DONE;
          - 'HX711_STM32_ALIVE'         — ACK heartbeat → HEARTBEAT_ACK;
          - 'CONFIRM_RECEIVED_COMMAND' — подтверждение команды → COMMAND_ACK;
          - 'UNKNOWN_COMMAND'         — МК не понял команду → COMMAND_REJECTED.

        Во всех случаях кроме рукопожатия восстанавливает сохранённое состояние
        автомата (heartbeat / command_ack / command_rejected — все приходят
        в момент, когда декодер находится в режиме «ждём ответ на команду»
        с сохранённым в _saved_state контекстом разбора прерванной посылки).

        Args:
            byte_list (list[bytes]): Список байтов всей посылки.
        """
        # Данные начинаются с индекса 4 (2 байта заголовка + формат + длина)
        # и заканчиваются до последнего байта (контрольная сумма)
        message_bytes = b''.join(byte_list[4:-1])
        try:
            message = message_bytes.decode('ascii')
        except UnicodeDecodeError:
            _logger.warning(f'Сообщение от МК содержит невалидные ASCII байты: {message_bytes!r}')
            return

        if message == self._handshake_ack:
            await bus.handshake_done.emit()
            _logger.info(f'ACK рукопожатия получен: "{message}"')

        elif message == self._heartbeat_ack:
            self._restore_state()
            await bus.heartbeat_ack.emit()
            _logger.debug(f'ACK heartbeat получен: "{message}"')

        elif message == self._command_ack:
            self._restore_state()
            await bus.command_ack.emit()
            _logger.debug(f'Подтверждение команды получено: "{message}"')

        elif message == self._command_rejected_msg:
            self._restore_state()
            await bus.command_rejected.emit()
            _logger.warning(f'МК отверг команду: "{message}"')

        else:
            _logger.warning(f'Неизвестное сообщение от МК: "{message}"')