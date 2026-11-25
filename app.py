import ctypes
import os
import sys

from PyQt6.QtWidgets import QApplication

from app import setup_launcher
from app.main_window import MainWindow, _windows
from app.ui import theme as th
from app.ui.widgets import logo_icon


def main():
    if os.name == "nt":
        # Своя группа на панели задач: иначе Windows покажет иконку Python, а не LettMine
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LettCup.LettMine")
        except Exception:
            pass
    setup_launcher()
    app = QApplication(sys.argv)
    app.setApplicationName("LettMine")
    th.load_fonts()
    app.setWindowIcon(logo_icon())
    window = MainWindow()
    _windows.append(window)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
