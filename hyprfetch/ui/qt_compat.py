"""Cross-toolkit Qt abstraction layer supporting both PySide6 and PyQt6 seamlessly."""

import sys

QT_API = None

try:
    import PySide6
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtCore import Property, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal, Slot
    from PySide6.QtGui import (
        QAction,
        QBrush,
        QColor,
        QFont,
        QFontMetrics,
        QLinearGradient,
        QPainter,
        QPainterPath,
        QPen,
        QPolygonF,
    )
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSlider,
        QSplitter,
        QStackedWidget,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
    QT_API = "PySide6"
except ImportError:
    try:
        import PyQt6
        from PyQt6 import QtCore, QtGui, QtWidgets
        from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer
        from PyQt6.QtCore import pyqtProperty as Property
        from PyQt6.QtCore import pyqtSignal as Signal
        from PyQt6.QtCore import pyqtSlot as Slot
        from PyQt6.QtGui import (
            QAction,
            QBrush,
            QColor,
            QFont,
            QFontMetrics,
            QLinearGradient,
            QPainter,
            QPainterPath,
            QPen,
            QPolygonF,
        )
        from PyQt6.QtWidgets import (
            QApplication,
            QComboBox,
            QFrame,
            QGridLayout,
            QGroupBox,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QProgressBar,
            QPushButton,
            QScrollArea,
            QSlider,
            QSplitter,
            QStackedWidget,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
        QT_API = "PyQt6"
    except ImportError as err:
        print(f"Error: Neither PySide6 nor PyQt6 could be found on the system. {err}", file=sys.stderr)
        sys.exit(1)


__all__ = [
    "QT_API",
    "QtCore",
    "QtGui",
    "QtWidgets",
    "Signal",
    "Slot",
    "Property",
    "Qt",
    "QTimer",
    "QPoint",
    "QPointF",
    "QRect",
    "QRectF",
    "QSize",
    "QColor",
    "QFont",
    "QFontMetrics",
    "QPen",
    "QBrush",
    "QPainter",
    "QPainterPath",
    "QLinearGradient",
    "QPolygonF",
    "QAction",
    "QApplication",
    "QMainWindow",
    "QWidget",
    "QFrame",
    "QLabel",
    "QPushButton",
    "QSlider",
    "QComboBox",
    "QProgressBar",
    "QScrollArea",
    "QStackedWidget",
    "QTableWidget",
    "QTableWidgetItem",
    "QHeaderView",
    "QGroupBox",
    "QSplitter",
    "QLineEdit",
    "QMessageBox",
    "QVBoxLayout",
    "QHBoxLayout",
    "QGridLayout",
]
