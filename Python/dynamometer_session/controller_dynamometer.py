# -*- coding: utf-8 -*-
"""Модуль контроллера сессии МК для связи GUI-процесса и async-компонентов."""

# System imports
import asyncio
from multiprocessing import Queue
from queue import Empty
from typing import Awaitable, Callable, Optional

# User imports
from byte_source.read_error import ReadError
from decoding.hx711_decoding import HX711Data
from dynamometer_session.mc_logger import McLogger
from dynamometer_session.signal_bus import McBus

##########################################################


class ControllerDynamometer:
    """Контроллер команд GUI, событий МК и межпроцессорных очередей."""

    def __init__(self, bus: McBus, mc_logger: McLogger,
                 command_queue: Queue, response_queue: Queue, data_queue: Queue):
        """Сохраняет очереди и создаёт таблицу обработчиков команд GUI."""
        self._bus = bus
        self._logger = mc_logger.get_child_logger("Controller.Dynamometer")
        self._command_queue = command_queue
        self._response_queue = response_queue
        self._data_queue = data_queue
        self._stop_event = asyncio.Event()
        self._reading_cmd_queue_task: Optional[asyncio.Task] = None
        self._status = "SUCCESS"

        self._command_to_handler: dict[str, Callable[[], Awaitable[None]]] = {
            "STOP_RUNNING": self._stop_running,
            "HANDSHAKE_INIT": self._handshake_init,
            "START_MEASURING": self._start_measuring,
            "STOP_MEASURING": self._stop_measuring,
        }

    # =============================================================
    # ======= Методы для работы в контекстном менеджере ===========
    # =============================================================

    async def __aenter__(self) -> "ControllerDynamometer":
        """Подписывается на события шины и запускает чтение команд GUI."""
        self._bus.package_ready.subscribe(self)
        self._bus.handshake_done.subscribe(self)
        self._bus.handshake_failed.subscribe(self)
        self._bus.read_error.subscribe(self)
        self._bus.device_lost.subscribe(self)
        self._bus.command_ack_timeout.subscribe(self)
        self._bus.command_rejected.subscribe(self)
        self._reading_cmd_queue_task = asyncio.create_task(self._reading_command_queue())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Отписывается от событий и инициирует штатное или аварийное завершение."""
        self._bus.package_ready.unsubscribe(self)
        self._bus.handshake_done.unsubscribe(self)
        self._bus.handshake_failed.unsubscribe(self)
        self._bus.read_error.unsubscribe(self)
        self._bus.device_lost.unsubscribe(self)
        self._bus.command_ack_timeout.unsubscribe(self)
        self._bus.command_rejected.unsubscribe(self)
        await self._cancel_task(self._reading_cmd_queue_task)

        if self._status == "SUCCESS":
            await self._bus.stop_executing.emit()
        else:
            await self._bus.interrupt_measuring.emit()
        return False

    # =============================================================
    # ===================== Публичные методы ======================
    # =============================================================

    async def running(self) -> None:
        """Ожидает сигнала завершения работы контроллера."""
        self._stop_event.clear()
        await self._stop_event.wait()

    # =============================================================
    # =================== Обработчики сигналов ====================
    # =============================================================

    async def on_package_ready(self, data_package: HX711Data) -> None:
        """Отправляет декодированный пакет данных в data_queue."""
        await asyncio.to_thread(self._data_queue.put, data_package)

    async def on_handshake_done(self) -> None:
        """Отправляет GUI сообщение об успешном рукопожатии."""
        await self._send_info_msg("HANDSHAKE_DONE")

    async def on_handshake_failed(self) -> None:
        """Фиксирует ошибку рукопожатия и завершает сессию."""
        self._status = "HANDSHAKE_FAILED"
        await self._send_info_msg("HANDSHAKE_FAILED")
        self._stop_event.set()

    async def on_read_error(self, err: ReadError) -> None:
        """Фиксирует ошибку чтения из источника байтов."""
        self._status = "READ_ERROR"
        await self._send_info_msg("READ_ERROR")
        self._stop_event.set()

    async def on_device_lost(self) -> None:
        """Фиксирует потерю связи по heartbeat."""
        self._status = "DEVICE_LOST"
        await self._send_info_msg("DEVICE_LOST")
        self._stop_event.set()

    async def on_command_ack_timeout(self) -> None:
        """Фиксирует таймаут подтверждения команды."""
        self._status = "COMMAND_ACK_TIMEOUT"
        await self._send_info_msg("COMMAND_ACK_TIMEOUT")
        self._stop_event.set()

    async def on_command_rejected(self) -> None:
        """Фиксирует отказ МК из-за неизвестной команды."""
        self._status = "COMMAND_REJECTED"
        await self._send_info_msg("COMMAND_REJECTED")
        self._stop_event.set()

    # =============================================================
    # =================== Внутренняя логика =======================
    # =============================================================

    async def _stop_running(self) -> None:
        """Завершает работу контроллера по команде GUI."""
        self._stop_event.set()

    async def _handshake_init(self) -> None:
        """Инициирует процедуру рукопожатия."""
        await self._bus.handshake_init.emit()

    async def _start_measuring(self) -> None:
        """Публикует сигнал запуска измерения."""
        await self._bus.start_measuring.emit()

    async def _stop_measuring(self) -> None:
        """Публикует сигнал остановки измерения."""
        await self._bus.stop_measuring.emit()

    async def _reading_command_queue(self) -> None:
        """Неблокирующее чтение команд из command_queue."""
        def get_input_command(command_queue: Queue) -> Optional[str]:
            """Ожидает команду ограниченное время, чтобы task можно было отменить."""
            try:
                return command_queue.get(timeout=0.1)
            except Empty:
                return None

        try:
            while True:
                cmd = await asyncio.to_thread(get_input_command, self._command_queue)
                if cmd is None:
                    continue
                handler = self._command_to_handler.get(cmd)
                if handler is None:
                    self._logger.warning("Unknown GUI command: %s", cmd)
                    continue
                await handler()
        except asyncio.CancelledError:
            raise

    async def _send_info_msg(self, msg: str) -> None:
        """Отправляет информационное сообщение в response_queue."""
        await asyncio.to_thread(self._response_queue.put, msg)

    @staticmethod
    async def _cancel_task(task: Optional[asyncio.Task]) -> None:
        """Отменяет asyncio.Task и дожидается её завершения."""
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
