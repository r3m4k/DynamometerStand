# System imports
import sys
import traceback

# External imports
from PyQt5.QtWidgets import QApplication

# User imports
from gui.main_window import MainWindow
from app_logger import app_logger

#############################################

def global_exception_handler(exc_type, exc_value, exc_tb):
    """Обработчик необработанных исключений."""
    app_logger.critical("Необработанное исключение:")
    app_logger.critical(''.join(traceback.format_exception(exc_type, exc_value, exc_tb)))
    sys.exit(1)

# -------------------------------------------

sys.excepthook = global_exception_handler

# -------------------------------------------

class MyApplication(QApplication):
    def notify(self, receiver, event):
        try:
            return super().notify(receiver, event)
        except Exception:
            app_logger.exception("Исключение при обработке события")
            return False

# -------------------------------------------

if __name__ == "__main__":
    try:
        app = MyApplication(sys.argv)
        app_logger.debug('Инициализация main_window')
        window = MainWindow()
        app.setQuitOnLastWindowClosed(False)
        app_logger.debug('Запуск main window')
        window.show()
        sys.exit(app.exec_())

    except Exception:
        app_logger.critical("Критическая ошибка при запуске приложения")
        sys.exit(1)
