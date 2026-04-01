# -*- coding: utf-8 -*-
"""Модуль для расчёта крутящего момента по данным АЦП.

Содержит класс `TorqueCalculation`, который управляет калибровками для нескольких
датчиков и предоставляет метод для вычисления момента по коду АЦП.
"""

# System imports

# External imports

# User imports
from config import config
from ADCAnalysis.calibration import SensorCalibration, SensorCalibrationFactory

#############################################

class TorqueCalculationError(Exception):
    """Исключение, возникающее при расчёте крутящего момента"""
    pass

class TorqueCalculation:
    """Вычисление крутящего момента для заданных датчиков в config.calibration.sensor_id_list"""

    def __init__(self) -> None:
        """Инициализирует объект `TorqueCalculation`.

        Загружает список ID датчиков из конфигурации и создаёт для каждого
        соответствующий объект калибровки.
        """
        sensor_id_list: list[int] = config.calibration.sensor_id_list
        self._sensor_calibration_dict: dict[int, SensorCalibration] = {
            sensor_id: SensorCalibrationFactory.get_calibration(sensor_id) for sensor_id in sensor_id_list
        }

    def calc_torque(self, sensor_id: int, adc_value: int) -> float:
        """Вычисление крутящего момента по коду АЦП для указанного датчика.

        Args:
            sensor_id (int): Идентификатор датчика (должен присутствовать в словаре).
            adc_value (int): Значение АЦП, полученное от датчика.

        Returns:
            float: Рассчитанное значение крутящего момента [H * m].
        """
        if sensor_id not in self._sensor_calibration_dict.keys():
            raise TorqueCalculationError(f'Переданный id датчика {sensor_id} не указан '
                                         f'в config.calibration.sensor_id_list: {config.calibration.sensor_id_list}!')
        return self._sensor_calibration_dict[sensor_id].calc_from_adc_value(adc_value)