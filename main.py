"""
JJK Domain Expansion — Desktop Application
Entry point: launches the PyQt5 app.

Usage:
    .\.venv\Scripts\python main.py

Controls:
    Esc   → Quit
    F     → Toggle fullscreen / windowed
"""

import sys
import os

# Suppress TensorFlow info logs (keep only warnings/errors)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtCore import Qt

from ui.main_window import MainWindow


def create_dark_palette() -> QPalette:
    """Create a system-wide dark color palette."""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(10, 10, 15))
    palette.setColor(QPalette.WindowText, QColor(200, 200, 220))
    palette.setColor(QPalette.Base, QColor(15, 15, 20))
    palette.setColor(QPalette.AlternateBase, QColor(20, 20, 28))
    palette.setColor(QPalette.Text, QColor(200, 200, 220))
    palette.setColor(QPalette.Button, QColor(25, 25, 35))
    palette.setColor(QPalette.ButtonText, QColor(200, 200, 220))
    palette.setColor(QPalette.Highlight, QColor(138, 43, 226))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    return palette


def main():
    app = QApplication(sys.argv)

    # ── Dark theme ──
    app.setStyle("Fusion")
    app.setPalette(create_dark_palette())
    app.setFont(QFont("Segoe UI", 10))

    # ── Launch ──
    window = MainWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
