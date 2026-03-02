# -*- coding: utf-8 -*-
"""Модуль управления конфигурацией приложения.

Содержит модель `AppConfig` на базе Pydantic для загрузки, валидации
и сохранения настроек в JSON-файл.
"""

# System imports
import json
from pathlib import Path
from typing import Optional

# External imports
from pydantic import BaseModel, ConfigDict, Field

# User imports

#############################################

class AppConfig(BaseModel):
    """Модель конфигурации приложения.

    Все поля имеют значения по умолчанию, загрузка и сохранение производятся
    в формате JSON. Неизвестные поля в файле настроек запрещены (extra='forbid').

    Attributes:
        host (str): Адрес сервера или хоста. По умолчанию 'localhost'.
        port (int): Порт сервера. Допустимые значения от 1 до 65535.
            По умолчанию 8080.
        debug (bool): Флаг отладки. Включает подробное логирование и т.п.
            По умолчанию False.
        database_url (str): Строка подключения к базе данных.
            По умолчанию 'sqlite:///app.db'.
        api_key (Optional[str]): Ключ API для доступа к внешним сервисам.
            Может отсутствовать. По умолчанию None.
    """

    # Настройки Pydantic: запретить неизвестные поля в JSON
    model_config = ConfigDict(extra='forbid')

    # Поля конфигурации с типизацией и значениями по умолчанию
    host: str = "localhost"
    port: int = Field(8080, ge=1, le=65535)          # порт должен быть в диапазоне
    debug: bool = False
    database_url: str = "sqlite:///app.db"
    api_key: Optional[str] = None                    # необязательное поле

    @classmethod
    def load(cls, config_path: Path) -> 'AppConfig':
        """Загружает конфигурацию из JSON-файла.

        Если файл не существует, создаёт экземпляр со значениями по умолчанию
        и сохраняет его в указанный путь.

        Args:
            config_path (Path): Путь к JSON-файлу конфигурации.

        Returns:
            AppConfig: Экземпляр конфигурации, загруженный из файла
            или созданный по умолчанию.

        Raises:
            json.JSONDecodeError: Если файл содержит некорректный JSON.
            pydantic.ValidationError: Если данные не соответствуют типам полей.
        """
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls(**data)  # Pydantic проверит типы и поля
        # Файла нет – создаём с умолчаниями и сохраняем
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
        # Создаём директорию, если она не существует
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            # model_dump() превращает модель в словарь
            json.dump(self.model_dump(), f, indent=4, ensure_ascii=False)

    def reload(self, config_path: Path) -> None:
        """Перезагружает конфигурацию из файла, обновляя текущий экземпляр.

        Полезно, если файл был изменён вручную во время работы приложения.
        Обновляет только существующие поля (неизвестные игнорируются).

        Args:
            config_path (Path): Путь к файлу конфигурации.

        Raises:
            json.JSONDecodeError: Если файл содержит некорректный JSON.
        """
        if not config_path.exists():
            return  # или можно выбросить исключение, но по умолчанию ничего не делаем
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Обновляем только существующие поля (игнорируем неизвестные)
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
