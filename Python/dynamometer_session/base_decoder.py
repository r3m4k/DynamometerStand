# -*- coding: utf-8 -*-
"""Модуль базового декодера протокола обмена с МК.

Содержит конечный автомат разбора пакета и DeviceDecoder, который знает общие
форматы пакетов МК: данные, текстовые сообщения, ACK heartbeat и ACK команд.
"""

# System imports
import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Generic, Optional, TypeVar

# User imports
from dynamometer_session.mc_logger import McLogger
from dynamometer_session.signal_bus import McBus

##########################################################


T = TypeVar("T")


class Stage(Enum):
    """Состояния конечного автомата разбора пакета."""

    WANT_HEADER = 1
    WANT_FORMAT = 2
    WANT_LENGTH = 3
    WANT_DATA = 4
    WANT_CONTROL_SUM = 5


DecodeFunc = Callable[[list[bytes]], Awaitable[None]]
SavedState = tuple[Stage, list[bytes], int, int, DecodeFunc]

# ------------------------------------------


class BaseDecoder(ABC, Generic[T]):
    """Базовый асинхронный декодер потока байтов."""

    _header: list[bytes]

    def __init__(self, bus: McBus, mc_logger: McLogger):
        """Инициализирует очереди, состояние автомата и счётчики пакетов."""
        self._bus = bus
        self._logger = mc_logger.get_child_logger(self.__class__.__name__)

        self._byte_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._package_queue: asyncio.Queue[T] = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        self._package_emitting_task: Optional[asyncio.Task] = None

        self._decode_func: DecodeFunc = self._default_decode_func
        self._stage = Stage.WANT_HEADER
        self._received_bytes: list[bytes] = []
        self._data_bt_index = 0
        self._package_size = 0

        self._num_correct_packages = 0
        self._num_wrong_packages = 0
        self._num_unknown_packages = 0

    async def __aenter__(self) -> "BaseDecoder":
        """Подписывается на поток байтов и запускает фоновые задачи обработки."""
        self._reset()
        self._bus.new_byte.subscribe(self)
        self._processing_task = asyncio.create_task(self._processing_loop())
        self._package_emitting_task = asyncio.create_task(self._package_emitting_loop())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Отписывается от шины и отменяет фоновые задачи декодера."""
        self._bus.new_byte.unsubscribe(self)
        for task in (self._processing_task, self._package_emitting_task):
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        return False

    async def on_byte_received(self, bt: bytes) -> None:
        """Обработчик сигнала NEW_BYTE: кладёт новый байт во внутреннюю очередь."""
        await self._byte_queue.put(bt)

    @abstractmethod
    def _get_decode_func(self, fmt: bytes) -> Optional[DecodeFunc]:
        """Возвращает функцию декодирования по байту формата пакета."""
        ...

    def _reset(self) -> None:
        """Полностью сбрасывает состояние декодера и пересоздаёт очереди."""
        self._clear()
        self._byte_queue = asyncio.Queue()
        self._package_queue = asyncio.Queue()

    def _clear(self) -> None:
        """Очищает состояние конечного автомата и счётчики статистики."""
        self._stage = Stage.WANT_HEADER
        self._received_bytes = []
        self._data_bt_index = 0
        self._package_size = 0
        self._decode_func = self._default_decode_func
        self._num_correct_packages = 0
        self._num_wrong_packages = 0
        self._num_unknown_packages = 0

    async def _processing_loop(self) -> None:
        """Фоновая задача последовательной обработки входящих байтов."""
        try:
            while True:
                await self._byte_processing(await self._byte_queue.get())
        except asyncio.CancelledError:
            raise

    async def _package_emitting_loop(self) -> None:
        """Фоновая задача отправки декодированных пакетов в сигнальную шину."""
        try:
            while True:
                await self._bus.package_ready.emit(await self._package_queue.get())
        except asyncio.CancelledError:
            raise

    async def _byte_processing(self, bt: bytes) -> None:
        """Обрабатывает один байт в соответствии с текущим состоянием FSM."""
        self._received_bytes.append(bt)

        match self._stage:
            case Stage.WANT_HEADER:
                if self._received_bytes[-2:] == self._header:
                    self._stage = Stage.WANT_FORMAT
                    self._received_bytes = self._header.copy()
                    self._data_bt_index = 0

            case Stage.WANT_FORMAT:
                decode_func = self._get_decode_func(bt)
                if decode_func is None:
                    self._stage = Stage.WANT_HEADER
                    self._num_unknown_packages += 1
                    self._logger.warning("Unknown packet format: %r", bt)
                    return
                self._decode_func = decode_func
                self._stage = Stage.WANT_LENGTH

            case Stage.WANT_LENGTH:
                self._package_size = int.from_bytes(bt, "big")
                self._stage = Stage.WANT_DATA

            case Stage.WANT_DATA:
                if self._data_bt_index < self._package_size - 1:
                    self._data_bt_index += 1
                else:
                    self._stage = Stage.WANT_CONTROL_SUM

            case Stage.WANT_CONTROL_SUM:
                if bt == self._count_control_sum(self._received_bytes):
                    await self._decode_func(self._received_bytes)
                    self._num_correct_packages += 1
                else:
                    self._num_wrong_packages += 1
                    self._logger.warning("Wrong packet control sum")

                self._stage = Stage.WANT_HEADER
                self._received_bytes = []
                self._data_bt_index = 0

    @staticmethod
    def _count_control_sum(data_bytes: list[bytes]) -> bytes:
        """Считает контрольную сумму пакета как сумму байтов по модулю 256."""
        return bytes([sum(int.from_bytes(bt, "big") for bt in data_bytes[:-1]) & 0xFF])

    async def _default_decode_func(self, byte_list: list[bytes]) -> None:
        """Заглушка декодирования для пакета без выбранного формата."""
        self._logger.warning("Packet ignored: no decode function selected: %r", byte_list)

# ------------------------------------------


class DeviceDecoder(BaseDecoder[T], ABC):
    """Декодер пакетов МК без привязки к конкретной структуре данных."""

    # Константы форматов пакетов протокола.
    _data_format_bt = b"\x01"
    _message_format_bt = b"\xCD"

    # Получаемые текстовые сообщения от МК.
    _handshake_ack: str
    _heartbeat_ack: str
    _command_ack: str = "CONFIRM_RECEIVED_COMMAND"
    _command_rejected_msg: str = "UNKNOWN_COMMAND"

    def __init__(self, bus: McBus, mc_logger: McLogger):
        """Создаёт таблицу обработчиков текстовых сообщений МК."""
        super().__init__(bus, mc_logger)
        self.received_data: list[T] = []
        self._saved_state: Optional[SavedState] = None
        self._msg_to_handler: dict[str, Callable[[], Awaitable[None]]] = {
            self._handshake_ack: self._on_handshake_ack_msg,
            self._heartbeat_ack: self._on_heartbeat_ack_msg,
            self._command_ack: self._on_command_ack_msg,
            self._command_rejected_msg: self._on_command_rejected_msg,
        }

    async def __aenter__(self) -> "DeviceDecoder":
        """Подписывается на сигналы, влияющие на состояние декодера."""
        self._bus.handshake_init.subscribe(self)
        self._bus.heartbeat_sent.subscribe(self)
        self._bus.command_sent.subscribe(self)
        self._bus.command_ack_timeout.subscribe(self)
        return await super().__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Отписывается от сигналов управления состоянием декодера."""
        self._bus.handshake_init.unsubscribe(self)
        self._bus.heartbeat_sent.unsubscribe(self)
        self._bus.command_sent.unsubscribe(self)
        self._bus.command_ack_timeout.unsubscribe(self)
        return await super().__aexit__(exc_type, exc_val, exc_tb)

    async def on_handshake_init(self) -> None:
        """Очищает состояние перед новой процедурой рукопожатия."""
        self._clear()

    async def on_heartbeat_sent(self) -> None:
        """Сохраняет состояние автомата на время ожидания ACK heartbeat."""
        self._save_state()

    async def on_command_sent(self) -> None:
        """Сохраняет состояние автомата на время ожидания ACK команды."""
        self._save_state()

    async def on_command_ack_timeout(self) -> None:
        """Восстанавливает состояние, если ACK команды не пришёл вовремя."""
        self._restore_state()

    def _clear(self) -> None:
        """Очищает состояние DeviceDecoder вместе с накопленными данными."""
        super()._clear()
        self.received_data.clear()
        self._saved_state = None

    def _get_decode_func(self, fmt: bytes) -> Optional[DecodeFunc]:
        """Возвращает функцию декодирования для data/message пакета."""
        if fmt == self._data_format_bt:
            return self._bytes_to_data
        if fmt == self._message_format_bt:
            return self._bytes_to_message
        return None

    async def _bytes_to_data(self, byte_list: list[bytes]) -> None:
        """Декодирует data-пакет, сохраняет его и публикует в шину."""
        data = self._bytes_to_protocol_data(byte_list)
        self.received_data.append(data)
        await self._package_queue.put(data)

    async def _bytes_to_message(self, byte_list: list[bytes]) -> None:
        """Декодирует текстовое сообщение от МК и вызывает обработчик."""
        message_bytes = b"".join(byte_list[4:-1])
        try:
            message = message_bytes.decode("ascii")
        except UnicodeDecodeError:
            self._logger.warning("Non-ASCII message from device: %r", message_bytes)
            return

        handler = self._msg_to_handler.get(message)
        if handler is None:
            self._logger.warning("Unknown message from device: %s", message)
            return
        await handler()

    @abstractmethod
    def _bytes_to_protocol_data(self, byte_list: list[bytes]) -> T:
        """Декодирует байты data-пакета в доменную структуру данных."""
        ...

    def _save_state(self) -> None:
        """Сохраняет состояние FSM и переводит декодер в ожидание заголовка ACK."""
        self._saved_state = (
            self._stage,
            self._received_bytes.copy(),
            self._data_bt_index,
            self._package_size,
            self._decode_func,
        )
        self._stage = Stage.WANT_HEADER
        self._received_bytes = []
        self._data_bt_index = 0
        self._package_size = 0

    def _restore_state(self) -> None:
        """Восстанавливает состояние FSM после обработки ACK или таймаута."""
        if self._saved_state is None:
            return
        (
            self._stage,
            self._received_bytes,
            self._data_bt_index,
            self._package_size,
            self._decode_func,
        ) = self._saved_state
        self._saved_state = None

    async def _on_handshake_ack_msg(self) -> None:
        """Обрабатывает ACK рукопожатия."""
        await self._bus.handshake_done.emit()

    async def _on_heartbeat_ack_msg(self) -> None:
        """Обрабатывает ACK heartbeat и восстанавливает состояние декодера."""
        self._restore_state()
        await self._bus.heartbeat_ack.emit()

    async def _on_command_ack_msg(self) -> None:
        """Обрабатывает подтверждение команды от МК."""
        self._restore_state()
        await self._bus.command_ack.emit()

    async def _on_command_rejected_msg(self) -> None:
        """Обрабатывает отказ МК из-за неизвестной команды."""
        self._restore_state()
        await self._bus.command_rejected.emit()
