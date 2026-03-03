"""
Пакет для реализации источников данных
"""

__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from byte_source.bytes_source import BytesSource, ReadError
from byte_source.com_port import ComPortSetting
from byte_source.file_source import FileSourceSetting

# --------------------------------------------------------

__all__ = [
    'BytesSource',
    'ReadError',
    'ComPortSetting',
    'FileSourceSetting',
]

# --------------------------------------------------------
