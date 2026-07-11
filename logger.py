import logging
import os
from PySide6.QtCore import QObject, Signal

class LogSignal(QObject):
    new_log = Signal(str, str)

class QtLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.emitter = LogSignal()

    def emit(self, record):
        msg = self.format(record)

        self.emitter.new_log.emit(record.levelname, msg)

LOG_FILE = os.path.join(os.getcwd(), "chatterbox.log")

app_logger = logging.getLogger("ChatterboxStudio")
app_logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)
app_logger.addHandler(file_handler)

qt_handler = QtLogHandler()
qt_handler.setFormatter(formatter)
qt_handler.setLevel(logging.INFO)
app_logger.addHandler(qt_handler)

def get_logger():

    return app_logger
