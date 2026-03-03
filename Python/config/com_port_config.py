# System imports
from typing import Optional

# External imports
from pydantic import BaseModel, Field, field_validator

# User imports

#############################################

class ComPortConfig(BaseModel):
    """Настройки COM-порта."""
    name: Optional[str] = None
    desc: Optional[str] = None
    hwid: Optional[str] = None
    baudrate: Optional[int] = Field(
        None,
        description="Скорость передачи данных (допустимые значения: 9600, 57600, 115200, 230400, 460800, 921600)"
    )

    @field_validator('baudrate')
    @classmethod
    def _validate_baudrate(cls, v: int) -> int:
        allowed = [9600, 57600, 115200, 230400, 460800, 921600]
        if v not in allowed:
            raise ValueError(f'baudrate должен быть одним из {allowed}')
        return v
