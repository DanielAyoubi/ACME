import os
import sys

from PyQt6.QtWidgets import QApplication

from src.gui.main_window import MainWindow


def main():
    # Relative paths in setup files (like the log folder) are relative to the app folder.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.setWindowTitle("ACME")
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
