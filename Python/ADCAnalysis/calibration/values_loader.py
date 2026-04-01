# System imports
from abc import ABC, abstractmethod

# External imports
import numpy as np

# User imports
from config import config

#############################################


class Loader(ABC):

    @abstractmethod
    def get_adc_values(self) -> np.typing.NDArray[float]: ...

    @abstractmethod
    def get_torque_values(self) -> np.typing.NDArray[float]: ...


class FooLinearLoader(Loader):
    """Загрузчик данных без реальной калибровки.
    Используется исключительно для отладки проекта"""
    def __init__(self, sensor_id: int):
        ADC_MAX_VALUE = 16777215
        if sensor_id == 1:
            self._adc_values = np.linspace(-ADC_MAX_VALUE, ADC_MAX_VALUE, 100)
            self._torque_values = np.linspace(-ADC_MAX_VALUE, ADC_MAX_VALUE, 100)
        elif sensor_id == 2:
            self._adc_values = np.linspace(-ADC_MAX_VALUE, ADC_MAX_VALUE, 100)
            self._torque_values = -np.linspace(-ADC_MAX_VALUE, ADC_MAX_VALUE, 100)
        else:
            raise RuntimeError('Неподдерживаемый ID датчика')

    def get_adc_values(self) -> np.typing.NDArray[float]:
        return self._adc_values

    def get_torque_values(self) -> np.typing.NDArray[float]:
        return self._torque_values


class CalibrationDataLoader(Loader):
    """Загрузчик данных калибровки."""
    def __init__(self, sensor_id: int):
        ...

    def get_adc_values(self) -> np.typing.NDArray[float]:
        ...

    def get_torque_values(self) -> np.typing.NDArray[float]:
        ...


class LoaderFactory:
    @classmethod
    def get_loader(cls, sensor_id: int) -> Loader:
        loader_name: str = config.calibration.loader_type
        match loader_name:
            case 'FooLinearLoader':
                return FooLinearLoader(sensor_id)
            case 'CalibrationDataLoader':
                return CalibrationDataLoader(sensor_id)
            case _:
                raise RuntimeError(f'Unsupported loader name {loader_name}')
