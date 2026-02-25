# System imports
import os
import serial

# External imports
if os.name == 'nt':  # sys.platform == 'win32':
    from serial.tools.list_ports_windows import comports
elif os.name == 'posix':
    from serial.tools.list_ports_posix import comports

# User imports



##########################################################

def get_ComPorts() -> dict[str, ...]:
    """
    Функция для получения информации о всех подключённых com-портах.
    Возвращает словарь данной структуры:
        {'номер COM-порта': {
                'desc': дескриптор выбранного порта,
                'hwid': hwid порта
            }
        }
    """
    iterator = comports(include_links=False)
    res = {}
    for n, (_port, desc, hwid) in enumerate(iterator, 1):
        res[_port] = {"desc": desc, "hwid": hwid}

    return res
