# -*- coding: utf-8 -*-
"""Модуль для настройки и использования файлового логгера с ротацией.

Содержит класс `AppLogger`, который инкапсулирует настройку логгера
и предоставляет удобные методы для записи сообщений различных уровней.
Конфигурация загружается из глобального объекта `config.logger_config`.

В модуле также определён глобальный экземпляр `app_logger`, который можно
импортировать и использовать во всём приложении.
"""

# System imports
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

# External imports

# User imports
from config import config

#############################################

class AppLogger:
    """Класс для управления логгером приложения."""

    def __init__(self):
        self._file_handler: Optional[logging.Handler] = None

        # Создаём корневой логгер
        self._logger = logging.getLogger()
        self._logger.setLevel(config.logger_config.log_level)

        # Настраиваем файловый обработчик по умолчанию
        self._setup_file_logging(config.logger_config.log_dir)

    def _setup_file_logging(self, log_dir: Path) -> None:
        """Создаёт или заменяет файловый обработчик логгера.

        Args:
            log_dir (Path): Путь к директории, в которой будет сохранён файл лога.
        """

        log_dir = Path(log_dir).resolve()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / config.logger_config.log_filename

        log_format = logging.Formatter(
            config.logger_config.log_format,
            config.logger_config.date_format
        )

        # Удаляем старый обработчик
        if self._file_handler is not None:
            self._logger.removeHandler(self._file_handler)
            self._file_handler.close()

        # Создаём новый
        self._file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=config.logger_config.max_bytes,
            backupCount=config.logger_config.backup_count,
            encoding='utf-8'
        )
        self._file_handler.setLevel(config.logger_config.log_level)
        self._file_handler.setFormatter(log_format)
        self._logger.addHandler(self._file_handler)

    def set_log_dir(self, log_dir: Path) -> None:
        """Изменение директории для хранения логов с помощью создания
        пересозданию файлового обработчика в указанной директории.
        Старый файл остаётся на диске.

        Args:
            log_dir (Path): Новая директория для хранения логов.
        """
        self._setup_file_logging(log_dir)

    # =============================================================
    # ================ Методы для записи сообщений ================
    # =============================================================

    def debug(self, msg: str, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        self._logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        self._logger.exception(msg, *args, **kwargs)

# -------------------------------------------

# Глобальный экземпляр логгера для использования во всём приложении
app_logger = AppLogger()

# -------------------------------------------
