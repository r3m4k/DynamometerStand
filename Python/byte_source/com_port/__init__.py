"""
Пакет для работы с COM-портом
"""

__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from .utils import get_ComPorts
from .com_port import ComPort, ComPortSetting

# --------------------------------------------------------

__all__ = [
    'get_ComPorts',
    'ComPort',
    'ComPortSetting'
]

# --------------------------------------------------------
