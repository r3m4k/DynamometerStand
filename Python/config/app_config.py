# -*- coding: utf-8 -*-
"""Модуль управления конфигурацией приложения.

Предоставляет модель `AppConfig` на основе Pydantic для загрузки, валидации
и сохранения настроек в JSON-файл. Структура конфигурации включает секции
для COM-порта и файлового источника, а также общие параметры.
"""

# System imports
import json
from pathlib import Path

# External imports
from pydantic import BaseModel, ConfigDict, Field

# User imports
from config.com_port_config import ComPortConfig
from config.file_source_config import FileSourceConfig

#############################################

class AppConfig(BaseModel):
    """Основная конфигурация приложения.

    Содержит настройки источников данных и общие параметры.
    Неизвестные поля в JSON-файле запрещены.

    Attributes:
        com_port (ComPortConfig): Настройки COM-порта.
            По умолчанию создаётся экземпляр ComPortConfig со значениями по умолчанию.
        file_source (FileSourceConfig): Настройки файлового источника.
            По умолчанию создаётся экземпляр FileSourceConfig со значениями по умолчанию.
        save_dir (Path): Директория для сохранения результатов.
            По умолчанию './results'.
    """

    model_config = ConfigDict(extra='forbid')

    com_port: ComPortConfig = Field(
        default_factory=ComPortConfig,
        description="Настройки COM-порта"
    )
    file_source: FileSourceConfig = Field(
        default_factory=FileSourceConfig,
        description="Настройки файлового источника"
    )
    save_dir: Path = Field(
        default_factory=lambda: Path("./results"),
        description="Директория для сохранения результатов"
    )

    @classmethod
    def load(cls, config_path: Path) -> 'AppConfig':
        """Загружает конфигурацию из JSON-файла.

        Если файл не существует, создаёт экземпляр со значениями по умолчанию,
        сохраняет его по указанному пути и возвращает этот экземпляр.

        Args:
            config_path (Path): Путь к JSON-файлу конфигурации.

        Returns:
            AppConfig: Экземпляр конфигурации, загруженный из файла
            или созданный по умолчанию.

        Raises:
            json.JSONDecodeError: Если файл содержит некорректный JSON.
            ValidationError: Если данные в файле не соответствуют модели.
        """
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls(**data)
        instance = cls()
        instance.save(config_path)
        return instance

    def save(self, config_path: Path) -> None:
        """Сохраняет текущую конфигурацию в JSON-файл.

        Перед записью создаёт родительскую директорию, если она не существует.
        Использует отступы (indent=4) для читаемости.

        Args:
            config_path (Path): Путь для сохранения файла конфигурации.
        """
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            # model_dump(mode='json') преобразует Path в строку и т.д.
            json.dump(self.model_dump(mode='json'), f, indent=4, ensure_ascii=False)
