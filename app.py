import sys

from PyQt6.QtWidgets import QApplication

from app import setup_launcher
from app.main_window import MainWindow


def main():
    setup_launcher()
    app = QApplication(sys.argv)
    app.setApplicationName("LettMine")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
