# -*- coding: utf-8 -*-
"""Модуль настройки логгера для обмена с МК динамометрического стенда."""

# System imports
import logging
from pathlib import Path

# User imports
from config.logger_config import LoggerConfig

##########################################################


class McLogger:
    """Обёртка над logging.Logger для компонентов сессии МК."""

    def __init__(self, config: LoggerConfig):
        """Настраивает файловый обработчик логгера.

        Args:
            config: Конфигурация логирования приложения.
        """
        self._logger = logging.getLogger("DynamometerStand.MC")
        self._logger.setLevel(config.log_level)
        self._logger.propagate = False

        for handler in list(self._logger.handlers):
            self._logger.removeHandler(handler)
            handler.close()

        log_dir = Path(config.log_dir).resolve()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "dynamometer_mc.log"

        formatter = logging.Formatter(config.log_format, config.date_format)
        file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
        file_handler.setLevel(config.log_level)
        file_handler.setFormatter(formatter)
        self._logger.addHandler(file_handler)

    def get_child_logger(self, name: str) -> logging.Logger:
        """Возвращает дочерний логгер для конкретного компонента."""
        return logging.getLogger(f"{self._logger.name}.{name}")

    def debug(self, msg: str, *args, **kwargs) -> None:
        """Записывает DEBUG-сообщение."""
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        """Записывает INFO-сообщение."""
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        """Записывает WARNING-сообщение."""
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        """Записывает ERROR-сообщение."""
        self._logger.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs) -> None:
        """Записывает исключение с traceback."""
        self._logger.exception(msg, *args, **kwargs)
