# System imports
from sys import argv, exit

# External imports
from PyQt5.QtWidgets import QApplication

# User imports
from gui.main_window import MainWindow

#############################################

if __name__ == "__main__":
    app = QApplication(argv)
    window = MainWindow()
    window.show()
    exit(app.exec_())