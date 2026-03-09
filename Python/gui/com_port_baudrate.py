# System imports
from pathlib import Path
from typing import TypedDict

# External imports
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QRadioButton

# User imports

##########################################################

class RadioButtonsDict(TypedDict):
    rb_921600: QRadioButton | int
    rb_460800: QRadioButton | int
    rb_230400: QRadioButton | int
    rb_115200: QRadioButton | int
    rb_57600: QRadioButton | int
    rb_9600: QRadioButton | int

    # def key_from_int(self, baudrate: int) -> 'RadioButtonsDict': ...


# --------------------------------------------------------

class ComPortBaudrate(QObject):
    baudrate_dict = RadioButtonsDict(
        rb_921600 = 921600,
        rb_460800 = 460800,
        rb_230400 = 230400,
        rb_115200 = 115200,
        rb_57600 = 57600,
        rb_9600 = 9600
    )

    def __init__(self, radio_buttons: RadioButtonsDict):
        super().__init__()
        self._radio_buttons: RadioButtonsDict = radio_buttons
        self._current_radio_button: QRadioButton | None = None

    def get_baudrate(self) -> int: ...

    def _load_from_config(self) -> None: ...

    def _set_radio_button(self) -> None: ...

    def _radio_button_clicked(self) -> None: ...


