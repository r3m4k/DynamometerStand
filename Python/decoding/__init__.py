# -*- coding: utf-8 -*-
"""Пакет для декодирования данных с АЦП.

Пакет предоставляет набор классов для приёма байтового потока, выделения пакетов,
проверки контрольной суммы и преобразования сырых данных в структурированные объекты
(данные тензодатчиков HX711 или команды).

Доступные модули и классы:
    - decoder_protocol.DecoderProtocol: Описание формата пакетов (константы, длины полей).
    - hx711_decoder.HX711Decoder: Основной класс-декодер с конечным автоматом.
    - data_description.HX711Data: Класс для хранения распакованных данных датчика.

Attributes:
    __version__ (str): Версия пакета.
    __author__ (str): Автор пакета.
"""

__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from decoding.decoder_protocol import DecoderProtocol
from decoding.command import Command
from decoding.hx711_decoding import HX711Decoder, HX711Data

# --------------------------------------------------------

__all__ = [
    'DecoderProtocol',
    'Command',
    'HX711Decoder',
    'HX711Data'
]

# --------------------------------------------------------