# System imports
from pathlib import Path
from typing import Optional

# External imports
from pydantic import BaseModel, Field

# User imports

#############################################

class FileSourceConfig(BaseModel):
    """Настройки файлового источника."""
    filename: Optional[Path] = Field(
        None,
        description="Путь к файлу с данными. Если None или отсутствует, источник не используется."
    )