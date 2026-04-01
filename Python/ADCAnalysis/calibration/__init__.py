# -*- coding: utf-8 -*-
"""
Пакет для калибровки АЦП.

Содержит абстрактные интерфейсы и конкретные реализации для загрузки
калибровочных данных и расчёта крутящего момента по коду АЦП.
"""

__author__ = 'Roman Romanovskiy'

# --------------------------------------------------------

from ADCAnalysis.calibration.values_loader import Loader, LoaderFactory
from ADCAnalysis.calibration.sensor_calibration import SensorCalibration, SensorCalibrationFactory

# --------------------------------------------------------

__all__ = [
    'Loader',
    'LoaderFactory',
    'SensorCalibration',
    'SensorCalibrationFactory',
]

# --------------------------------------------------------
