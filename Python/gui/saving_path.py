# System imports
from pathlib import Path
from typing import TypedDict

# External imports
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QRadioButton, QLineEdit, QToolButton

# User imports

##########################################################

class SavingPathSetting(QObject):
    def __init__(self, saving_path_edit: QLineEdit, choose_saving_path_button: QToolButton):
        super().__init__()

    def get_saving_path(self) -> Path: ...

    def _load_from_config(self) -> None: ...

    def _select_path(self) -> None: ...
