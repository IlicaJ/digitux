"""Entry point for the DigiTux app."""
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap

from .main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DigiTux")

    # splash
    splash = None
    splash_path = Path(__file__).parents[1] / "assets" / "img" / "splash" / "digitux_splash.png"
    if splash_path.exists():
        pm = QPixmap(str(splash_path))
        if not pm.isNull():
            splash = QSplashScreen(pm.scaled(600, 450, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            splash.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
            splash.show()
            app.processEvents()

    w = MainWindow()

    def show_main():
        w.show()
        if splash:
            splash.finish(w)

    if splash:
        QTimer.singleShot(900, show_main)
    else:
        w.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()