# -*- coding: utf-8 -*-
"""Модуль потокового сохранения данных HX711, полученных от МК динамометрического стенда."""

# System imports
from pathlib import Path
from typing import Optional, TextIO

# User imports
from decoding.hx711_decoding import HX711Data

##########################################################


class DataStorage:
    """Потоковое сохранение пакетов HX711Data в CSV-файл."""

    def __init__(self) -> None:
        """Инициализирует хранилище без открытого файла."""
        self.file_path: Optional[Path] = None
        self._file: Optional[TextIO] = None
        self._sep: str = ","
        self._count: int = 0

    @property
    def is_open(self) -> bool:
        """Возвращает True, если файл сохранения открыт."""
        return self._file is not None and not self._file.closed

    @property
    def count(self) -> int:
        """Возвращает количество записанных пакетов в текущий файл."""
        return self._count

    def set_file(self, file_path: Path, sep: str = ",") -> None:
        """Задаёт новый CSV-файл для потокового сохранения данных.

        Args:
            file_path: Путь к CSV-файлу.
            sep: Разделитель полей. По умолчанию запятая, как в текущем HX711Decoder.

        Raises:
            TypeError: Если file_path не является экземпляром Path.
        """
        if not isinstance(file_path, Path):
            raise TypeError(f"Ожидается file_path: Path, получен {type(file_path)}")
        if self.file_path == file_path and self.is_open:
            return

        self.close()
        self.file_path = file_path
        self._sep = sep
        self._count = 0

        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self.file_path, "w", encoding="utf-8", newline="")
            self._write_header()
        except Exception:
            self.close()
            raise

    def add_package(self, package: HX711Data) -> None:
        """Записывает новый пакет HX711Data в текущий CSV-файл.

        Args:
            package: Пакет данных, полученный от МК.

        Raises:
            TypeError: Если package не является экземпляром HX711Data.
        """
        if not isinstance(package, HX711Data):
            raise TypeError(f"Ожидается package: HX711Data, получен {type(package)}")
        file = self._file
        if file is None or file.closed:
            return

        # Формат строки сохранён таким же, как в HX711Decoder.save_received_data().
        file.write(
            f"{package.id}{self._sep}{package.time}{self._sep}"
            f"{package.adc_value}{self._sep}{package.gain.to_string()}\n"
        )
        self._count += 1

    def close(self) -> None:
        """Закрывает текущий файл сохранения."""
        if self._file is None:
            return

        self._file.close()
        self._file = None

    def _write_header(self) -> None:
        """Записывает заголовок CSV-файла."""
        file = self._file
        if file is None or file.closed:
            return

        file.write(f"SensorId{self._sep}Time{self._sep}ADCValue{self._sep}Gain\n")
