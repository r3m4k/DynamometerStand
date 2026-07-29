# -*- coding: utf-8 -*-
"""Модуль сигнальной шины для взаимодействия компонентов сессии МК.

Содержит перечисление сигналов, простую асинхронную шину и фасад McBus,
который предоставляет именованные endpoint-ы в стиле проекта Telega.
"""

# System imports
import inspect
from collections import defaultdict
from enum import Enum
from typing import Any, Awaitable, Callable

##########################################################


class Signals(Enum):
    """Список событий, которыми обмениваются компоненты сессии."""

    NEW_BYTE = "NewByte"
    PACKAGE_READY = "PackageReady"

    STOP_EXECUTING = "StopExecuting"
    HANDSHAKE_INIT = "HandshakeInit"
    HANDSHAKE_DONE = "HandshakeDone"
    HANDSHAKE_FAILED = "HandshakeFailed"

    START_MEASURING = "StartMeasuring"
    STOP_MEASURING = "StopMeasuring"
    INTERRUPT_MEASURING = "InterruptMeasuring"

    READ_ERROR = "ReadError"
    HEARTBEAT_SENT = "HeartbeatSent"
    HEARTBEAT_ACK = "HeartbeatAck"
    DEVICE_LOST = "DeviceLost"

    COMMAND_SENT = "CommandSent"
    COMMAND_ACK = "CommandAck"
    COMMAND_ACK_TIMEOUT = "CommandAckTimeout"
    COMMAND_REJECTED = "CommandRejected"


Subscriber = Callable[..., Awaitable[None] | None]

# ------------------------------------------


class SignalBus:
    """Низкоуровневая асинхронная шина сигналов."""

    def __init__(self) -> None:
        """Инициализирует пустой словарь подписчиков."""
        self._subscribers: dict[Signals, list[Subscriber]] = defaultdict(list)

    def subscribe(self, signal: Signals, handler: Subscriber) -> None:
        """Подписывает обработчик на указанный сигнал."""
        if handler not in self._subscribers[signal]:
            self._subscribers[signal].append(handler)

    def unsubscribe(self, signal: Signals, handler: Subscriber) -> None:
        """Отписывает обработчик от указанного сигнала."""
        if handler in self._subscribers[signal]:
            self._subscribers[signal].remove(handler)

    async def emit(self, signal: Signals, *args: Any, **kwargs: Any) -> None:
        """Вызывает все обработчики сигнала и ожидает coroutine-результаты."""
        for handler in list(self._subscribers[signal]):
            result = handler(*args, **kwargs)
            if inspect.isawaitable(result):
                await result

# ------------------------------------------


class _Endpoint:
    """Именованный endpoint шины, привязанный к методу подписчика."""

    def __init__(self, signal_bus: SignalBus, signal: Signals, handler_name: str):
        self._signal_bus = signal_bus
        self._signal = signal
        self._handler_name = handler_name

    def subscribe(self, subscriber: object) -> None:
        """Подписывает объект по имени метода-обработчика."""
        self._signal_bus.subscribe(self._signal, getattr(subscriber, self._handler_name))

    def unsubscribe(self, subscriber: object) -> None:
        """Отписывает объект по имени метода-обработчика."""
        self._signal_bus.unsubscribe(self._signal, getattr(subscriber, self._handler_name))

    async def emit(self, *args: Any, **kwargs: Any) -> None:
        """Публикует событие endpoint-а."""
        await self._signal_bus.emit(self._signal, *args, **kwargs)

# ------------------------------------------


class McBus:
    """Фасад сигнальной шины с endpoint-ами протокола динамометрического стенда."""

    def __init__(self) -> None:
        """Создаёт endpoint-ы для всех событий сессии МК."""
        self._signal_bus = SignalBus()

        self.new_byte = _Endpoint(self._signal_bus, Signals.NEW_BYTE, "on_byte_received")
        self.package_ready = _Endpoint(self._signal_bus, Signals.PACKAGE_READY, "on_package_ready")

        self.stop_executing = _Endpoint(self._signal_bus, Signals.STOP_EXECUTING, "on_stop_executing")
        self.handshake_init = _Endpoint(self._signal_bus, Signals.HANDSHAKE_INIT, "on_handshake_init")
        self.handshake_done = _Endpoint(self._signal_bus, Signals.HANDSHAKE_DONE, "on_handshake_done")
        self.handshake_failed = _Endpoint(self._signal_bus, Signals.HANDSHAKE_FAILED, "on_handshake_failed")

        self.start_measuring = _Endpoint(self._signal_bus, Signals.START_MEASURING, "on_start_measuring")
        self.stop_measuring = _Endpoint(self._signal_bus, Signals.STOP_MEASURING, "on_stop_measuring")
        self.interrupt_measuring = _Endpoint(
            self._signal_bus, Signals.INTERRUPT_MEASURING, "on_interrupt_measuring"
        )

        self.read_error = _Endpoint(self._signal_bus, Signals.READ_ERROR, "on_read_error")
        self.heartbeat_sent = _Endpoint(self._signal_bus, Signals.HEARTBEAT_SENT, "on_heartbeat_sent")
        self.heartbeat_ack = _Endpoint(self._signal_bus, Signals.HEARTBEAT_ACK, "on_heartbeat_ack")
        self.device_lost = _Endpoint(self._signal_bus, Signals.DEVICE_LOST, "on_device_lost")

        self.command_sent = _Endpoint(self._signal_bus, Signals.COMMAND_SENT, "on_command_sent")
        self.command_ack = _Endpoint(self._signal_bus, Signals.COMMAND_ACK, "on_command_ack")
        self.command_ack_timeout = _Endpoint(
            self._signal_bus, Signals.COMMAND_ACK_TIMEOUT, "on_command_ack_timeout"
        )
        self.command_rejected = _Endpoint(
            self._signal_bus, Signals.COMMAND_REJECTED, "on_command_rejected"
        )
