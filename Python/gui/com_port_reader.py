# -*- coding: utf-8 -*-
from __future__ import annotations

from multiprocessing import get_context
from multiprocessing.queues import Queue
from pathlib import Path
from queue import Empty
from threading import Event, Thread
from typing import Any, Callable

from PyQt5.QtCore import QObject, pyqtSignal

from config.com_port_config import ComPortConfig
from config.logger_config import LoggerConfig
from decoding.hx711_decoding import HX711Data
from dynamometer_session.start_dynamometer_session import start_dynamometer_session


class ComPortReaderException(RuntimeError):
    pass


class NeedConfiguration(ComPortReaderException):
    pass


class SessionIsRunning(ComPortReaderException):
    pass


class SessionNotRunning(ComPortReaderException):
    pass


class MeasuringRunning(ComPortReaderException):
    pass


class MeasuringNotRunning(ComPortReaderException):
    pass


class _QueueReader(QObject):
    item_received = pyqtSignal(object)

    def __init__(self, queue: Queue) -> None:
        super().__init__()
        self._queue = queue
        self._stop_event = Event()

    def start(self) -> Thread:
        thread = Thread(target=self._read_loop, daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop_event.set()

    def _read_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.1)
            except Empty:
                continue
            except (EOFError, OSError):
                return

            self.item_received.emit(item)


class _ComPortReaderWorker(QObject):
    data_received = pyqtSignal(HX711Data)
    handshake_done = pyqtSignal()
    handshake_failed = pyqtSignal()
    connection_failed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    _STOP_COMMAND = "STOP_RUNNING"
    _HANDSHAKE_COMMAND = "HANDSHAKE_INIT"
    _START_COMMAND = "START_MEASURING"
    _STOP_MEASURING_COMMAND = "STOP_MEASURING"

    def __init__(self) -> None:
        super().__init__()
        self._ctx = get_context("spawn")
        self._command_queue: Queue | None = None
        self._response_queue: Queue | None = None
        self._data_queue: Queue | None = None
        self._process = None

        self._response_reader: _QueueReader | None = None
        self._data_reader: _QueueReader | None = None
        self._response_thread: Thread | None = None
        self._data_thread: Thread | None = None

        self._configured = False
        self._measuring = False

        self._response_handlers: dict[str, Callable[[str], None]] = {
            "HANDSHAKE_DONE": lambda _: self._on_handshake_done(),
            "HANDSHAKE_FAILED": lambda _: self._on_handshake_failed(),
            "CONNECTION_FAILED": self._on_connection_failed,
            "READ_ERROR": self._on_error,
            "DEVICE_LOST": self._on_error,
            "COMMAND_ACK_TIMEOUT": self._on_error,
            "COMMAND_REJECTED": self._on_error,
        }

    def configure(
        self,
        logger_config: LoggerConfig,
        com_port_name: str,
        baudrate: int,
        bin_file: Path | None = None,
    ) -> None:
        if self.is_running:
            raise SessionIsRunning("COM-port session is already running")

        com_port_config = ComPortConfig(name=com_port_name, baudrate=baudrate)
        self._command_queue = self._ctx.Queue()
        self._response_queue = self._ctx.Queue()
        self._data_queue = self._ctx.Queue()

        self._response_reader = _QueueReader(self._response_queue)
        self._data_reader = _QueueReader(self._data_queue)
        self._response_reader.item_received.connect(self._handle_response)
        self._data_reader.item_received.connect(self._handle_data)
        self._response_thread = self._response_reader.start()
        self._data_thread = self._data_reader.start()

        self._process = self._ctx.Process(
            target=start_dynamometer_session,
            args=(
                logger_config,
                com_port_config,
                bin_file,
                self._command_queue,
                self._response_queue,
                self._data_queue,
            ),
            daemon=True,
        )
        self._process.start()
        self._configured = True
        self._put_command(self._HANDSHAKE_COMMAND)

    def start_measuring(self) -> None:
        self._ensure_session()
        if self._measuring:
            raise MeasuringRunning("Measuring is already running")

        self._put_command(self._START_COMMAND)
        self._measuring = True

    def stop_measuring(self) -> None:
        self._ensure_session()
        if not self._measuring:
            raise MeasuringNotRunning("Measuring is not running")

        self._put_command(self._STOP_MEASURING_COMMAND)
        self._measuring = False

    def shutdown(self) -> None:
        self._measuring = False
        if self._command_queue is not None and self.is_running:
            self._put_command(self._STOP_COMMAND)

        if self._process is not None:
            self._process.join(timeout=3.0)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=1.0)

        self._stop_queue_readers()
        self._close_queues()
        self._process = None
        self._configured = False
        self.finished.emit()

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.is_alive()

    def _ensure_session(self) -> None:
        if not self._configured or self._command_queue is None:
            raise NeedConfiguration("COM-port session needs configuration")
        if not self.is_running:
            raise SessionNotRunning("COM-port session is not running")

    def _put_command(self, command: str) -> None:
        if self._command_queue is None:
            raise NeedConfiguration("COM-port session needs configuration")
        self._command_queue.put(command)

    def _handle_response(self, response: Any) -> None:
        response_text = str(response)
        message_type, _, payload = response_text.partition(":")
        handler = self._response_handlers.get(message_type)
        if handler is None:
            self._on_error(response_text)
            return

        handler(payload.strip() or response_text)

    def _handle_data(self, package: Any) -> None:
        if isinstance(package, HX711Data):
            self.data_received.emit(package)

    def _on_handshake_done(self) -> None:
        self.handshake_done.emit()

    def _on_handshake_failed(self) -> None:
        self._configured = False
        self._measuring = False
        self.handshake_failed.emit()

    def _on_connection_failed(self, message: str) -> None:
        self._configured = False
        self._measuring = False
        self.connection_failed.emit(message)

    def _on_error(self, message: str) -> None:
        self._measuring = False
        self.error_occurred.emit(message)

    def _stop_queue_readers(self) -> None:
        for reader in (self._response_reader, self._data_reader):
            if reader is not None:
                reader.stop()

        for thread in (self._response_thread, self._data_thread):
            if thread is not None:
                thread.join(timeout=0.5)

        self._response_reader = None
        self._data_reader = None
        self._response_thread = None
        self._data_thread = None

    def _close_queues(self) -> None:
        for queue in (self._command_queue, self._response_queue, self._data_queue):
            if queue is None:
                continue
            queue.close()
            queue.join_thread()

        self._command_queue = None
        self._response_queue = None
        self._data_queue = None


class ComPortReader(QObject):
    data_received = pyqtSignal(HX711Data)
    handshake_done = pyqtSignal()
    handshake_failed = pyqtSignal()
    connection_failed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._worker = _ComPortReaderWorker()
        self._worker.data_received.connect(self.data_received.emit)
        self._worker.handshake_done.connect(self.handshake_done.emit)
        self._worker.handshake_failed.connect(self.handshake_failed.emit)
        self._worker.connection_failed.connect(self.connection_failed.emit)
        self._worker.error_occurred.connect(self.error_occurred.emit)
        self._worker.finished.connect(self.finished.emit)

    def configure(
        self,
        logger_config: LoggerConfig,
        com_port_name: str,
        baudrate: int,
        bin_file: Path | None = None,
    ) -> None:
        self._worker.configure(logger_config, com_port_name, baudrate, bin_file)

    def start_measuring(self) -> None:
        self._worker.start_measuring()

    def stop_measuring(self) -> None:
        self._worker.stop_measuring()

    def shutdown(self) -> None:
        self._worker.shutdown()

    @property
    def is_running(self) -> bool:
        return self._worker.is_running
