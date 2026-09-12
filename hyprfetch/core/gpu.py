"""GPU monitoring module supporting NVIDIA (nvidia-smi) and AMD/Intel sysfs fallbacks."""

import os
import shutil
import subprocess
from hyprfetch.core.system import TimeSeriesBuffer


class GPUMonitor:
    """Queries GPU metrics and stores historical trends."""

    def __init__(self):
        self.has_nvidia_smi = shutil.which("nvidia-smi") is not None
        self.util_history = TimeSeriesBuffer(max_points=120, max_seconds=120.0)
        self.temp_history = TimeSeriesBuffer(max_points=120, max_seconds=120.0)
        self.power_history = TimeSeriesBuffer(max_points=120, max_seconds=120.0)
        self.vram_history = TimeSeriesBuffer(max_points=120, max_seconds=120.0)

        # Cache static card info
        self.cached_name = None

    def poll(self) -> dict:
        if self.has_nvidia_smi:
            stats = self._query_nvidia()
            if stats["available"]:
                self._record(stats)
                return stats

        # Fallback to sysfs for Intel / AMD
        stats = self._query_sysfs()
        self._record(stats)
        return stats

    def _record(self, stats: dict):
        if stats["available"]:
            self.util_history.append(stats.get("utilization", 0.0))
            self.temp_history.append(stats.get("temp", 0.0))
            self.power_history.append(stats.get("power_w", 0.0))
            self.vram_history.append(stats.get("vram_pct", 0.0))

    def _query_nvidia(self) -> dict:
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total,power.draw,fan.speed",
            "--format=csv,noheader,nounits",
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
            if res.returncode == 0 and res.stdout.strip():
                line = res.stdout.strip().splitlines()[0]
                parts = [p.strip() for p in line.split(",")]
                name = parts[0] if len(parts) > 0 else "NVIDIA GPU"
                self.cached_name = name

                def to_float(val, default=0.0):
                    try:
                        clean = "".join(c for c in val if (c.isdigit() or c == "." or c == "-"))
                        return float(clean) if clean else default
                    except Exception:
                        return default

                util = to_float(parts[1]) if len(parts) > 1 else 0.0
                temp = to_float(parts[2]) if len(parts) > 2 else 0.0
                mem_used = to_float(parts[3]) if len(parts) > 3 else 0.0
                mem_total = to_float(parts[4]) if len(parts) > 4 else 0.0
                power_w = to_float(parts[5]) if len(parts) > 5 else 0.0
                if power_w > 350.0:
                    power_w = power_w / 1000.0 if power_w < 350000 else 0.0
                fan_pct = to_float(parts[6]) if len(parts) > 6 else 0.0

                vram_pct = (mem_used / mem_total * 100.0) if mem_total > 0 else 0.0

                # Short display name (e.g. RTX 3050)
                short_name = name
                for prefix in ("NVIDIA GeForce ", "NVIDIA ", "Laptop GPU", "Graphics"):
                    short_name = short_name.replace(prefix, "").strip()

                return {
                    "available": True,
                    "type": "nvidia",
                    "name": name,
                    "short_name": short_name,
                    "utilization": util,
                    "temp": temp,
                    "vram_used_mb": mem_used,
                    "vram_total_mb": mem_total,
                    "vram_pct": round(vram_pct, 1),
                    "power_w": power_w,
                    "fan_pct": fan_pct,
                    "display": f"{round(util)}%  {round(temp)}°C  {round(mem_used)}/{round(mem_total)}MiB  {round(power_w, 1)}W",
                }
        except Exception:
            pass

        return {"available": False, "name": "N/A", "short_name": "N/A", "utilization": 0.0, "temp": 0.0, "display": "N/A"}

    def _query_sysfs(self) -> dict:
        # Check AMD / Intel DRM sysfs
        for card in ("card1", "card0"):
            base = f"/sys/class/drm/{card}/device"
            if not os.path.exists(base):
                continue

            util = 0.0
            temp = 0.0
            busy_file = os.path.join(base, "gpu_busy_percent")
            if os.path.exists(busy_file):
                try:
                    with open(busy_file, "r") as f:
                        util = float(f.read().strip())
                except Exception:
                    pass

            hwmon_dir = os.path.join(base, "hwmon")
            if os.path.exists(hwmon_dir):
                for sub in os.listdir(hwmon_dir):
                    t_file = os.path.join(hwmon_dir, sub, "temp1_input")
                    if os.path.exists(t_file):
                        try:
                            with open(t_file, "r") as f:
                                temp = float(f.read().strip()) / 1000.0
                                break
                        except Exception:
                            pass

            return {
                "available": True,
                "type": "sysfs",
                "name": "Integrated / AMD GPU",
                "short_name": "GPU",
                "utilization": util,
                "temp": temp,
                "vram_used_mb": 0.0,
                "vram_total_mb": 0.0,
                "vram_pct": 0.0,
                "power_w": 0.0,
                "fan_pct": 0.0,
                "display": f"{round(util)}%  {round(temp)}°C",
            }

        return {
            "available": False,
            "type": "none",
            "name": "No GPU detected",
            "short_name": "N/A",
            "utilization": 0.0,
            "temp": 0.0,
            "vram_used_mb": 0.0,
            "vram_total_mb": 0.0,
            "vram_pct": 0.0,
            "power_w": 0.0,
            "fan_pct": 0.0,
            "display": "N/A",
        }
