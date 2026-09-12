"""System and memory/disk monitoring core module."""

import os
import platform
import subprocess
import time
from collections import deque


class TimeSeriesBuffer:
    """Thread-safe time-series ring buffer maintaining metrics over a sliding window."""

    def __init__(self, max_points: int = 120, max_seconds: float = 120.0):
        self.max_points = max_points
        self.max_seconds = max_seconds
        self._data = deque(maxlen=max_points)

    def append(self, value: float, ts: float = None):
        ts = ts or time.time()
        self._data.append((ts, float(value)))
        self._trim(ts)

    def _trim(self, now: float):
        cutoff = now - self.max_seconds
        while len(self._data) > 1 and self._data[0][0] < cutoff:
            self._data.popleft()

    def values(self) -> list[float]:
        return [v for _, v in self._data]

    def points(self) -> list[tuple[float, float]]:
        return list(self._data)

    @property
    def latest(self) -> float:
        return self._data[-1][1] if self._data else 0.0

    @property
    def min(self) -> float:
        return min((v for _, v in self._data), default=0.0)

    @property
    def max(self) -> float:
        return max((v for _, v in self._data), default=0.0)

    @property
    def avg(self) -> float:
        if not self._data:
            return 0.0
        return sum(v for _, v in self._data) / len(self._data)

    def clear(self):
        self._data.clear()


class SystemMonitor:
    """Monitors host info, memory, swap, and disk metrics."""

    def __init__(self):
        self.ram_history = TimeSeriesBuffer(max_points=120, max_seconds=120.0)
        self.cached_info = self._get_static_info()

    def _get_static_info(self) -> dict:
        host = platform.node() or os.getenv("HOSTNAME", "localhost")
        user = os.getenv("USER") or os.getenv("LOGNAME") or "user"
        kernel = platform.release()

        # OS detection
        os_name = "Linux"
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            os_name = line.split("=", 1)[1].strip().strip('"')
                            break
            except Exception:
                pass

        shell = os.path.basename(os.getenv("SHELL", "bash"))

        # WM / Desktop
        wm = "Hyprland" if os.getenv("HYPRLAND_INSTANCE_SIGNATURE") else os.getenv("XDG_CURRENT_DESKTOP", "Wayland")

        return {
            "host": host,
            "user": user,
            "os": os_name,
            "kernel": kernel,
            "shell": shell,
            "wm": wm,
        }

    def get_uptime(self) -> tuple[str, float]:
        try:
            with open("/proc/uptime", "r", encoding="utf-8") as f:
                uptime_seconds = float(f.readline().split()[0])
            mins, _ = divmod(int(uptime_seconds), 60)
            hours, mins = divmod(mins, 60)
            days, hours = divmod(hours, 24)
            if days > 0:
                uptime_str = f"{days}d {hours}h {mins}m"
            elif hours > 0:
                uptime_str = f"{hours}h {mins}m"
            else:
                uptime_str = f"{mins}m"
            return uptime_str, uptime_seconds
        except Exception:
            return "N/A", 0.0

    def get_ram(self) -> dict:
        total = 0
        available = 0
        free = 0
        buffers = 0
        cached = 0
        swap_total = 0
        swap_free = 0

        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split()
                    key = parts[0].rstrip(":")
                    if key == "MemTotal":
                        total = int(parts[1]) * 1024
                    elif key == "MemAvailable":
                        available = int(parts[1]) * 1024
                    elif key == "MemFree":
                        free = int(parts[1]) * 1024
                    elif key == "Buffers":
                        buffers = int(parts[1]) * 1024
                    elif key == "Cached":
                        cached = int(parts[1]) * 1024
                    elif key == "SwapTotal":
                        swap_total = int(parts[1]) * 1024
                    elif key == "SwapFree":
                        swap_free = int(parts[1]) * 1024
        except Exception:
            pass

        if available > 0:
            used = total - available
        else:
            used = total - (free + buffers + cached)

        used = max(0, used)
        percent = (used / total * 100.0) if total > 0 else 0.0
        self.ram_history.append(percent)

        swap_used = max(0, swap_total - swap_free)
        swap_percent = (swap_used / swap_total * 100.0) if swap_total > 0 else 0.0

        return {
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "available_bytes": available,
            "percent": round(percent, 1),
            "total_gb": round(total / (1024**3), 1),
            "used_gb": round(used / (1024**3), 1),
            "swap_total_gb": round(swap_total / (1024**3), 1),
            "swap_used_gb": round(swap_used / (1024**3), 1),
            "swap_percent": round(swap_percent, 1),
            "display": f"{round(used / (1024**3), 1)} / {round(total / (1024**3), 1)} GB",
        }

    def get_disk(self, mount: str = "/") -> dict:
        try:
            st = os.statvfs(mount)
            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            used = total - free
            percent = (used / total * 100.0) if total > 0 else 0.0
            return {
                "mount": mount,
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "total_gb": round(total / (1024**3), 1),
                "used_gb": round(used / (1024**3), 1),
                "percent": round(percent, 1),
                "display": f"{round(used / (1024**3), 1)} / {round(total / (1024**3), 1)} GB ({round(percent)}%)",
            }
        except Exception:
            return {
                "mount": mount,
                "total_bytes": 0,
                "used_bytes": 0,
                "free_bytes": 0,
                "total_gb": 0.0,
                "used_gb": 0.0,
                "percent": 0.0,
                "display": "N/A",
            }

    def get_summary(self) -> dict:
        uptime_str, uptime_sec = self.get_uptime()
        return {
            **self.cached_info,
            "uptime": uptime_str,
            "uptime_seconds": uptime_sec,
            "ram": self.get_ram(),
            "disk": self.get_disk("/"),
        }
