"""Network bandwidth, traffic rates, and active interface telemetry."""

import os
import subprocess
import time
from hyprfetch.core.system import TimeSeriesBuffer


class NetworkMonitor:
    """Monitors live network traffic (download/upload rates) and interface status."""

    def __init__(self):
        self.rx_history = TimeSeriesBuffer(max_points=120, max_seconds=120.0)
        self.tx_history = TimeSeriesBuffer(max_points=120, max_seconds=120.0)

        self.iface = self._detect_interface()
        self._prev_rx = 0
        self._prev_tx = 0
        self._prev_time = 0.0
        self._initialized = False

        self._init_counters()

    def _detect_interface(self) -> str:
        # Check /proc/net/route for default route
        try:
            with open("/proc/net/route", "r") as f:
                for line in f.readlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == "00000000":
                        return parts[0]
        except Exception:
            pass

        # Fallback to ip route
        try:
            res = subprocess.run(["ip", "route", "get", "1.1.1.1"], capture_output=True, text=True, timeout=1.0)
            if res.returncode == 0:
                words = res.stdout.split()
                if "dev" in words:
                    idx = words.index("dev")
                    if idx + 1 < len(words):
                        return words[idx + 1]
        except Exception:
            pass

        # Fallback to first non-loopback interface in /sys/class/net
        try:
            for iface in os.listdir("/sys/class/net"):
                if iface != "lo":
                    return iface
        except Exception:
            pass

        return "eth0"

    def _read_bytes(self) -> tuple[int, int]:
        rx_bytes = 0
        tx_bytes = 0
        rxf = f"/sys/class/net/{self.iface}/statistics/rx_bytes"
        txf = f"/sys/class/net/{self.iface}/statistics/tx_bytes"

        if os.path.exists(rxf) and os.path.exists(txf):
            try:
                with open(rxf, "r") as f:
                    rx_bytes = int(f.read().strip())
                with open(txf, "r") as f:
                    tx_bytes = int(f.read().strip())
                return rx_bytes, tx_bytes
            except Exception:
                pass

        try:
            with open("/proc/net/dev", "r") as f:
                for line in f.readlines()[2:]:
                    parts = line.split()
                    name = parts[0].rstrip(":")
                    if name == self.iface:
                        rx_bytes = int(parts[1])
                        tx_bytes = int(parts[9])
                        break
        except Exception:
            pass

        return rx_bytes, tx_bytes

    def _init_counters(self):
        self._prev_rx, self._prev_tx = self._read_bytes()
        self._prev_time = time.time()
        self._initialized = True

    def poll(self) -> dict:
        now = time.time()
        rx, tx = self._read_bytes()

        if not self._initialized or self._prev_time == 0:
            self._prev_rx = rx
            self._prev_tx = tx
            self._prev_time = now
            self._initialized = True
            return {
                "iface": self.iface,
                "rx_rate_kbs": 0.0,
                "tx_rate_kbs": 0.0,
                "rx_formatted": "0.0 KB/s",
                "tx_formatted": "0.0 KB/s",
                "display": "measuring…",
            }

        dt = max(0.1, now - self._prev_time)
        drx = max(0, rx - self._prev_rx)
        dtx = max(0, tx - self._prev_tx)

        self._prev_rx = rx
        self._prev_tx = tx
        self._prev_time = now

        rx_rate_kbs = round((drx / dt) / 1024.0, 1)
        tx_rate_kbs = round((dtx / dt) / 1024.0, 1)

        self.rx_history.append(rx_rate_kbs, now)
        self.tx_history.append(tx_rate_kbs, now)

        def format_speed(kbs: float) -> str:
            if kbs >= 1024:
                return f"{round(kbs / 1024.0, 1)} MB/s"
            return f"{kbs} KB/s"

        rx_fmt = format_speed(rx_rate_kbs)
        tx_fmt = format_speed(tx_rate_kbs)

        return {
            "iface": self.iface,
            "rx_rate_kbs": rx_rate_kbs,
            "tx_rate_kbs": tx_rate_kbs,
            "rx_formatted": rx_fmt,
            "tx_formatted": tx_fmt,
            "total_rx_mb": round(rx / (1024 * 1024), 1),
            "total_tx_mb": round(tx / (1024 * 1024), 1),
            "display": f"↓ {rx_fmt}  ↑ {tx_fmt} ({self.iface})",
        }
