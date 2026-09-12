"""HyprFetch UI package."""

from hyprfetch.ui.dashboard import HyprFetchDashboard
from hyprfetch.ui.graphs import RealtimeGraphWidget
from hyprfetch.ui.qt_compat import QApplication, QMainWindow

__all__ = ["HyprFetchDashboard", "RealtimeGraphWidget", "QApplication", "QMainWindow"]
