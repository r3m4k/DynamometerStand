# System imports
import os
import io

# External imports

# User imports
from byte_source import BytesSource
from byte_source.file_source import FileReadError
from utils import get_cache, save_cache, confirm_from_console

#########################

# Класс для использования log файла в качестве источника данных
class FileSource(BytesSource):
    _bin_file: io.BufferedReader

    def __init__(self, file_name: str):
        self._filename: str = file_name

    def setup(self):
        self._bin_file = open(self._filename, 'rb')

    def cleanup(self):
        self._bin_file.close()

    def read_byte(self) -> bytes:
        try:
            data = self._bin_file.read(1)
            if not data:
                raise FileReadError("Достигнут конец файла")
            return data
        except OSError as e:
            raise FileReadError(f"Ошибка чтения файла: {e}", original_exception=e)


# Класс для настройки FileSource
class FileSourceSetting:
    _filename: str

    def __init__(self):
        self._cache_data = get_cache()

        try:
            _cache_filename = self._cache_data['FileSource']['filename']

            print(f'Использовать файл "{_cache_filename}" в качестве источника данных?')
            _user_confirmation = confirm_from_console()

            if _user_confirmation:
                if os.path.isfile(_cache_filename):
                    self._filename = os.path.normpath(_cache_filename)
                else:
                    print(f'Не удаётся найти файл {_cache_filename}!\n')
                    self._load_filename_from_console()
            else:
                self._load_filename_from_console()

        except KeyError:
            self._load_filename_from_console()

    def __del__(self):
        save_cache(self._cache_data)

    def get_bytes_source(self) -> BytesSource:
        if self._filename:
            return FileSource(self._filename)
        else:
            raise RuntimeError('Имя файла не задано!')

    def _load_filename_from_console(self):
        user_filename = input('Введите абсолютный путь log файла с записанными данными:\n')
        user_filename = os.path.normpath(user_filename.replace('"', ''))
        print()

        if os.path.isfile(user_filename):
            self._filename = user_filename
            self._cache_data['FileSource']['filename'] = user_filename
        else:
            print(f'Не удаётся найти файл "{user_filename}"!\n'
                  f'Проверьте корректность ввода.\n')
            exit(1)