# System imports
import os
import json
from pathlib import Path

# External imports

# User imports

#############################################


cache_filename = Path(__file__).resolve().parent / 'cache.json'


def float_to_csv_format(value):
    """
    Перевод числа с плавающей точкой в строку для csv файла.
    """
    return str(round(value, 8)).replace(".", ",")


def get_cache() -> dict[str, ...]:
    loaded_data = {
        'ComPort': {
            # 'port': {
            #     'name': '',
            #     'desc': '',
            #     'hwid': '',
            #     'baudrate': 0,
            # }
        },
        'FileSource': {
            # 'filename': ''
        }
    }

    try:
        if os.path.exists(cache_filename):
            with open(cache_filename, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
    except Exception as err:
        print(err)

    return loaded_data


def save_cache(cache: dict[str, ...]):
    with open(cache_filename, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)


def confirm_from_console() -> bool:
    chose = input(f'Введите 1 для подтверждения, 0 для отказа:\t')
    print()
    if chose in ['1']:
        return True
    elif chose in ['0']:
        return False
    else:
        print('Ошибка ввода!')
        return confirm_from_console()