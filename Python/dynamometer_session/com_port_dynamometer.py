# -*- coding: utf-8 -*-
"""Модуль асинхронного COM-порта для обмена с МК динамометрического стенда."""

# System imports
import asyncio
from typing import Optional

# External imports
import serial_asyncio
from serial import SerialException

# User imports
from byte_source.com_port.com_port_error import ComPortReadError
from dynamometer_session.mc_logger import McLogger
from dynamometer_session.packet_builders import (
    PacketBuilderDynamometerBytes,
    PacketBuilderDynamometerText,
)
from dynamometer_session.signal_bus import McBus

##########################################################

_SETUP_TIMEOUT = 5.0       # Таймаут открытия COM-порта
_RESPONSE_TIMEOUT = 2.0    # Таймаут ожидания ответов МК
_HEARTBEAT_PERIOD = 10.0   # Период проверки связи с МК

# ------------------------------------------

class ComPortDynamometer:
    """Источник байтов и отправитель команд для МК динамометрического стенда."""

    # Команды, отправляемые на МК.
    _handshake_req_command = PacketBuilderDynamometerText.build_text_command("HANDSHAKE_REQ")
    _heartbeat_req_command = PacketBuilderDynamometerText.build_text_command("HEARTBEAT_REQ")
    _set_foo_stage_command = PacketBuilderDynamometerBytes.build_byte_command(bytes([0xAA, 0x01]))
    _set_measure_stage_command = PacketBuilderDynamometerBytes.build_byte_command(bytes([0xAA, 0x02]))

    def __init__(self, port_name: str, baudrate: int, bus: McBus, mc_logger: McLogger):
        """Сохраняет настройки порта и общие объекты сессии."""
        self._port_name = port_name
        self._baudrate = baudrate
        self._bus = bus
        self._logger = mc_logger.get_child_logger("ComPort.Dynamometer")

        self._port_reader: Optional[asyncio.StreamReader] = None
        self._port_writer: Optional[asyncio.StreamWriter] = None
        self._reading_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        self._handshake_event = asyncio.Event()
        self._heartbeat_ack_event = asyncio.Event()
        self._command_ack_event = asyncio.Event()
        self._stop_flag = False

    async def __aenter__(self) -> "ComPortDynamometer":
        """Открывает порт и подписывается на управляющие сигналы шины."""
        await self.setup()
        self._bus.stop_executing.subscribe(self)
        self._bus.handshake_init.subscribe(self)
        self._bus.handshake_done.subscribe(self)
        self._bus.start_measuring.subscribe(self)
        self._bus.stop_measuring.subscribe(self)
        self._bus.interrupt_measuring.subscribe(self)
        self._bus.heartbeat_ack.subscribe(self)
        self._bus.command_ack.subscribe(self)
        self._bus.command_rejected.subscribe(self)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Отписывается от сигналов и закрывает COM-порт."""
        self._bus.stop_executing.unsubscribe(self)
        self._bus.handshake_init.unsubscribe(self)
        self._bus.handshake_done.unsubscribe(self)
        self._bus.start_measuring.unsubscribe(self)
        self._bus.stop_measuring.unsubscribe(self)
        self._bus.interrupt_measuring.unsubscribe(self)
        self._bus.heartbeat_ack.unsubscribe(self)
        self._bus.command_ack.unsubscribe(self)
        self._bus.command_rejected.unsubscribe(self)
        await self.cleanup()
        return False

    async def setup(self) -> None:
        """Открывает COM-порт и запускает задачу чтения входящих байтов."""
        self._stop_flag = False
        self._logger.info("Opening %s (%s baud)", self._port_name, self._baudrate)
        try:
            self._port_reader, self._port_writer = await asyncio.wait_for(
                serial_asyncio.open_serial_connection(url=self._port_name, baudrate=self._baudrate),
                timeout=_SETUP_TIMEOUT,
            )
        except asyncio.TimeoutError as err:
            raise ComPortReadError(f"COM port open timeout: {self._port_name}") from err
        except SerialException as err:
            raise ComPortReadError(f"Serial port error: {err}") from err

        self._reading_task = asyncio.create_task(self._reading_loop())

    async def cleanup(self) -> None:
        """Останавливает фоновые задачи и закрывает COM-порт."""
        await self._cancel_task(self._heartbeat_task)
        await self._cancel_task(self._reading_task)
        self._heartbeat_task = None
        self._reading_task = None

        if self._port_writer is not None:
            self._port_writer.close()
            await self._port_writer.wait_closed()
            self._port_writer = None

    async def on_stop_executing(self) -> None:
        """Обработчик STOP_EXECUTING: переводит МК в FooStage и закрывает порт."""
        if self._stop_flag:
            return
        self._stop_flag = True
        try:
            await self._send_command_with_ack(self._set_foo_stage_command)
        finally:
            await self.cleanup()

    async def on_handshake_init(self) -> None:
        """Запускает процедуру рукопожатия с МК."""
        self._handshake_event.clear()
        await self._send_command(self._handshake_req_command)
        try:
            await asyncio.wait_for(self._handshake_event.wait(), timeout=_RESPONSE_TIMEOUT)
        except asyncio.TimeoutError:
            await self._bus.handshake_failed.emit()

    async def on_handshake_done(self) -> None:
        """Фиксирует успешное рукопожатие и запускает heartbeat."""
        self._handshake_event.set()
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def on_start_measuring(self) -> None:
        """Отправляет команду перехода МК в MeasureStage."""
        await self._send_command_with_ack(self._set_measure_stage_command)

    async def on_stop_measuring(self) -> None:
        """Отправляет команду перехода МК в FooStage."""
        await self._send_command_with_ack(self._set_foo_stage_command)

    async def on_interrupt_measuring(self) -> None:
        """Аварийно завершает обмен без ожидания штатного STOP_EXECUTING."""
        if self._stop_flag:
            return
        self._stop_flag = True
        self._command_ack_event.set()
        await self.cleanup()

    async def on_heartbeat_ack(self) -> None:
        """Обработчик ACK heartbeat."""
        self._heartbeat_ack_event.set()

    async def on_command_ack(self) -> None:
        """Обработчик подтверждения команды."""
        self._command_ack_event.set()

    async def on_command_rejected(self) -> None:
        """Обработчик отказа МК из-за неизвестной команды."""
        self._command_ack_event.set()

    async def _reading_loop(self) -> None:
        """Фоновая задача чтения байтов из COM-порта и публикации NEW_BYTE."""
        try:
            while True:
                assert self._port_reader is not None
                data = await self._port_reader.read(1)
                if not data:
                    raise ComPortReadError("Serial connection closed")
                await self._bus.new_byte.emit(data)
        except asyncio.CancelledError:
            raise
        except ComPortReadError as err:
            await self._bus.read_error.emit(err)
        except SerialException as err:
            await self._bus.read_error.emit(ComPortReadError(f"Serial read error: {err}"))

    async def _heartbeat_loop(self) -> None:
        """Фоновая задача периодической проверки связи с МК."""
        try:
            while True:
                await asyncio.sleep(_HEARTBEAT_PERIOD)
                self._heartbeat_ack_event.clear()
                await self._bus.heartbeat_sent.emit()
                await self._send_command(self._heartbeat_req_command)
                try:
                    await asyncio.wait_for(self._heartbeat_ack_event.wait(), timeout=_RESPONSE_TIMEOUT)
                except asyncio.TimeoutError:
                    await self._bus.device_lost.emit()
                    return
        except asyncio.CancelledError:
            raise

    async def _send_command(self, command: bytes) -> None:
        """Отправляет подготовленный пакет команды в COM-порт."""
        if self._port_writer is None:
            raise ComPortReadError("Serial port is not open")
        self._port_writer.write(command)
        await self._port_writer.drain()

    async def _send_command_with_ack(self, command: bytes) -> None:
        """Отправляет команду и ожидает подтверждение от МК."""
        self._command_ack_event.clear()
        await self._bus.command_sent.emit()
        await self._send_command(command)
        try:
            await asyncio.wait_for(self._command_ack_event.wait(), timeout=_RESPONSE_TIMEOUT)
        except asyncio.TimeoutError:
            await self._bus.command_ack_timeout.emit()

    @staticmethod
    async def _cancel_task(task: Optional[asyncio.Task]) -> None:
        """Отменяет asyncio.Task и дожидается её завершения."""
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
