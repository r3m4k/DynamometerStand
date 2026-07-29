# -*- coding: utf-8 -*-
"""Модуль запуска сессии обмена с МК в отдельном процессе."""

# System imports
import asyncio
from multiprocessing import Queue
from pathlib import Path

# User imports
from config.com_port_config import ComPortConfig
from config.logger_config import LoggerConfig
from dynamometer_session.com_port_dynamometer import ComPortDynamometer
from dynamometer_session.controller_dynamometer import ControllerDynamometer
from dynamometer_session.decoder_dynamometer import DynamometerDecoder
from dynamometer_session.mc_logger import McLogger
from dynamometer_session.mc_session import McSession
from dynamometer_session.signal_bus import McBus

##########################################################


async def _send_response_msg(response_queue: Queue, msg: str) -> None:
    """Безопасно отправляет сообщение в очередь ответов GUI."""
    try:
        await asyncio.to_thread(response_queue.put, msg)
    except Exception:
        pass

# ------------------------------------------


async def _run_dynamometer_session(logger_config: LoggerConfig,
                                   com_port_config: ComPortConfig,
                                   bin_file: Path | None,
                                   command_queue: Queue,
                                   response_queue: Queue,
                                   data_queue: Queue) -> None:
    """Создаёт компоненты сессии и запускает их в async-контексте."""
    mc_logger = McLogger(logger_config)
    bus = McBus()

    if com_port_config.name is None or com_port_config.baudrate is None:
        await _send_response_msg(response_queue, "CONNECTION_FAILED: COM port is not configured")
        return

    com_port = ComPortDynamometer(com_port_config.name, com_port_config.baudrate, bus, mc_logger)
    decoder = DynamometerDecoder(bus, mc_logger)
    decoder.setup_bin_file(bin_file)
    controller = ControllerDynamometer(bus, mc_logger, command_queue, response_queue, data_queue)

    try:
        async with McSession(decoder, com_port, controller):
            await controller.running()
    except Exception as err:
        mc_logger.exception("Dynamometer session failed")
        await _send_response_msg(response_queue, f"CONNECTION_FAILED: {err}")

    await asyncio.sleep(0.2)

# ------------------------------------------


def start_dynamometer_session(logger_config: LoggerConfig,
                              com_port_config: ComPortConfig,
                              bin_file: Path | None,
                              command_queue: Queue,
                              response_queue: Queue,
                              data_queue: Queue) -> None:
    """Точка входа дочернего процесса сессии МК."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            _run_dynamometer_session(
                logger_config,
                com_port_config,
                bin_file,
                command_queue,
                response_queue,
                data_queue,
            )
        )
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()
