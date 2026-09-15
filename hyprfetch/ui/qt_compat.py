"""Cross-toolkit Qt abstraction layer supporting both PyQt6 and PySide6 seamlessly.

PyQt6 is preferred when both are installed; PySide6 is used as a fallback.
If neither is available, this module raises ImportError (rather than calling
sys.exit) so callers -- namely main.py's GUI launch path -- can catch it and
fall back to the terminal TUI instead of killing the whole process.
"""

QT_API = None

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
except ImportError:
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
    except ImportError as err:
        raise ImportError(
            "Neither PyQt6 nor PySide6 is installed -- GUI mode is unavailable. "
            "Install one of them (e.g. `pip install PyQt6` or `pip install PySide6`) to use --gui. "
            "CLI/TUI/JSON modes do not require Qt and will still work."
        ) from err


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
