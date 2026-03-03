# System imports

# External imports

# User imports
from byte_source.bytes_source import ReadError

#########################


class ComPortReadError(ReadError):
    """Ошибка чтения из COM-порта."""
    pass