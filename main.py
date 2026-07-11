import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

if getattr(sys, "frozen", False):

    BASE_DIR = os.path.dirname(sys.executable)
else:

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CACHE_DIR = os.path.join(BASE_DIR, "system_models_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

os.environ["HF_HOME"] = CACHE_DIR
os.environ["HUGGINGFACE_HUB_CACHE"] = CACHE_DIR
os.environ["TRANSFORMERS_CACHE"] = CACHE_DIR

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt

def main():
    app = QApplication(sys.argv)

    icon_path = os.path.join(BASE_DIR, "icon.ico")
    app.setWindowIcon(QIcon(icon_path))

    splash_path = os.path.join(BASE_DIR, "splash.png")
    splash_pixmap = QPixmap(splash_path)

    splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
    splash.show()

    app.processEvents()

    from ui.main_window import MainWindow

    window = MainWindow()
    window.show()

    splash.finish(window)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
