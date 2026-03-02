"""
Пакет для построения графиков с более гибкими параметрами
функций их создания и настройки
"""

__version__ = '1.0.0'
__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from .canvas import Canvas
from .canvas_config import CanvasConfig
from .plotter import Plotter
from .color_scheme import color_scheme

# --------------------------------------------------------

__all__ = [
    'Canvas',
    'CanvasConfig',
    'Plotter',
    'color_scheme'
]

# --------------------------------------------------------
