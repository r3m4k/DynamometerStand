"""
Пакет для работы с файлом в качестве источника байтовых данных
"""

__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from byte_source.file_source.file_source import FileSource, FileSourceSetting
from byte_source.file_source.file_source_error import FileReadError

# --------------------------------------------------------

__all__ = [
    'FileSource',
    'FileSourceSetting',
    'FileReadError'
]

# --------------------------------------------------------
