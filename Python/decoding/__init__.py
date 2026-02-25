"""
Пакет для работы с декодером данных в формате "Гиронавт"
"""

__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from .decoder_protocol import DecoderProtocol
from .data_description import GyronavtData, TriaxialData
from .gyronavt_decoder import GyronavtDecoder

# --------------------------------------------------------

__all__ = [
    'DecoderProtocol',
    'GyronavtDecoder',
    'GyronavtData',
    'TriaxialData'
]

# --------------------------------------------------------
