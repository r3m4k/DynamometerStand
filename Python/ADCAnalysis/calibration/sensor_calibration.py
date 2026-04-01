# -*- coding: utf-8 -*-
"""Модуль, определяющий интерфейс калибровки датчиков и его реализацию на основе кубического сплайна.

Содержит абстрактный базовый класс `SensorCalibration`, конкретную реализацию
`CubicSplineCalibration`, использующую сплайн-интерполяцию, и фабрику
`SensorCalibrationFactory` для создания объектов калибровки на основе настроек
из глобального конфига.
"""

# System imports

# External imports
from abc import ABC, abstractmethod
from scipy.interpolate import CubicSpline

# User imports
from config import config
from ADCAnalysis.calibration.values_loader import Loader, LoaderFactory

#############################################

class SensorCalibration(ABC):
    """Абстрактный базовый класс для калибровки датчика.

    Определяет интерфейс для расчёта крутящего момента по коду АЦП.
    При инициализации создаёт загрузчик данных с помощью `LoaderFactory`,
    используя идентификатор датчика. Конкретные классы-наследники должны
    реализовать метод `calc_from_adc_value`.

    Attributes:
        _loader (Loader): Загрузчик калибровочных данных для данного датчика.
    """

    def __init__(self, sensor_id: int) -> None:
        self._loader: Loader = LoaderFactory.get_loader(sensor_id)

    @abstractmethod
    def calc_from_adc_value(self, adc_value: int) -> float:
        """Вычисляет крутящий момент по коду АЦП.

        Args:
            adc_value (int): Значение АЦП, полученное от датчика.

        Returns:
            float: Рассчитанное значение крутящего момента.

        Raises:
            NotImplementedError: Если метод не переопределён в наследнике.
        """
        pass


class CubicSplineCalibration(SensorCalibration):
    """Калибровка датчика на основе кубического сплайна.

    Использует загрузчик для получения массивов калибровочных данных
    (коды АЦП и соответствующие им моменты), по которым строится
    кубический сплайн. При вычислении момента применяется интерполяция
    сплайном.

    Attributes:
        _spline (CubicSpline): Объект кубического сплайна из SciPy.
    """

    def __init__(self, sensor_id: int) -> None:
        """Инициализирует сплайн-калибровку.

        Загружает калибровочные данные через родительский класс и строит
        по ним кубический сплайн с естественными граничными условиями.

        Args:
            sensor_id (int): Идентификатор датчика.

        Raises:
            ValueError: Если загруженные массивы пусты или имеют разную длину.
            Exception: Любое исключение, возбуждённое `CubicSpline` при построении.
        """
        super().__init__(sensor_id)
        self._spline: CubicSpline = CubicSpline(self._loader.get_adc_values(),
                                                self._loader.get_torque_values())

    def calc_from_adc_value(self, adc_value: int) -> float:
        """Вычисляет момент интерполяцией по сплайну.

        Args:
            adc_value (int): Код АЦП.

        Returns:
            float: Интерполированное значение момента.

        Note:
            При выходе за пределы калибровочного диапазона поведение сплайна
            не определено (экстраполяция может давать непредсказуемые результаты).
            При необходимости можно добавить проверку границ.
        """
        return float(self._spline(adc_value))


class SensorCalibrationFactory:
    """Фабрика для создания объектов калибровки датчиков.

    Позволяет получить экземпляр калибровки нужного типа на основе
    строкового имени, заданного в глобальном конфиге
    (`config.calibration.calibration_type`).
    """

    @classmethod
    def get_calibration(cls, sensor_id: int) -> SensorCalibration:
        """Создаёт и возвращает объект калибровки для указанного датчика.

        Тип создаваемой калибровки определяется значением
        `config.calibration.calibration_type`. В текущей реализации
        поддерживается только `'CubicSplineCalibration'`.

        Args:
            sensor_id (int): Идентификатор датчика.

        Returns:
            SensorCalibration: Экземпляр класса, реализующего калибровку.

        Raises:
            RuntimeError: Если имя калибровки из конфига не поддерживается.
        """
        calibration_name: str = config.calibration.calibration_type
        match calibration_name:
            case 'CubicSplineCalibration':
                return CubicSplineCalibration(sensor_id)
            case _:
                raise RuntimeError(f'Unsupported calibration name {calibration_name}')