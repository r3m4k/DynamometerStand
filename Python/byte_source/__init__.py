"""
Пакет для реализации источников данных
"""

__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from .bytes_source import BytesSource
from .com_port import ComPortSetting
from .file_source import FileSourceSetting

# --------------------------------------------------------

__all__ = [
    'BytesSource',
    'ComPortSetting',
    'FileSourceSetting',
]

# --------------------------------------------------------
