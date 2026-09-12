"""Core system monitoring and telemetry hub for HyprFetch."""

import time
from hyprfetch.core.battery import BatteryMonitor
from hyprfetch.core.cpu import CPUMonitor
from hyprfetch.core.gpu import GPUMonitor
from hyprfetch.core.network import NetworkMonitor
from hyprfetch.core.system import SystemMonitor, TimeSeriesBuffer


class HyprFetchCore:
    """Unified telemetry hub orchestrating hardware monitors and historical data."""

    def __init__(self):
        self.system = SystemMonitor()
        self.gpu = GPUMonitor()
        self.cpu = CPUMonitor()
        self.battery = BatteryMonitor()
        self.network = NetworkMonitor()

    def snapshot(self) -> dict:
        """Capture a synchronized dictionary snapshot of all hardware telemetry."""
        return {
            "timestamp": time.time(),
            "system": self.system.get_summary(),
            "gpu": self.gpu.poll(),
            "cpu": self.cpu.poll(),
            "battery": self.battery.poll(),
            "network": self.network.poll(),
        }


__all__ = [
    "HyprFetchCore",
    "SystemMonitor",
    "GPUMonitor",
    "CPUMonitor",
    "BatteryMonitor",
    "NetworkMonitor",
    "TimeSeriesBuffer",
]
