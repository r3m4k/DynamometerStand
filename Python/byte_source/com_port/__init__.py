"""
Пакет для работы с COM-портом
"""

__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from byte_source.com_port.utils import get_ComPorts
from byte_source.com_port.com_port import ComPort, ComPortSetting
from byte_source.com_port.com_port_error import ComPortReadError

# --------------------------------------------------------

__all__ = [
    'get_ComPorts',
    'ComPort',
    'ComPortSetting',
    'ComPortReadError'
]

# --------------------------------------------------------
