"""Battery health, charging state, and discharge telemetry."""

import glob
import os
import re
import shutil
import subprocess
from hyprfetch.core.system import TimeSeriesBuffer


class BatteryMonitor:
    """Queries power supplies for battery percentage, health, and power consumption."""

    def __init__(self):
        self.history = TimeSeriesBuffer(max_points=120, max_seconds=120.0)
        self.power_history = TimeSeriesBuffer(max_points=120, max_seconds=120.0)
        self.has_upower = shutil.which("upower") is not None
        self._bat_sysfs = self._find_bat_sysfs()

    def _find_bat_sysfs(self) -> str | None:
        bats = glob.glob("/sys/class/power_supply/BAT*")
        return bats[0] if bats else None

    def poll(self) -> dict:
        if self._bat_sysfs and os.path.exists(self._bat_sysfs):
            data = self._read_sysfs(self._bat_sysfs)
            if data["present"]:
                self.history.append(data["percent"])
                self.power_history.append(data["power_w"])
                return data

        if self.has_upower:
            data = self._read_upower()
            if data["present"]:
                self.history.append(data["percent"])
                self.power_history.append(data["power_w"])
                return data

        return {
            "present": False,
            "percent": 0.0,
            "state": "No battery",
            "health": 0.0,
            "power_w": 0.0,
            "time_remaining": "N/A",
            "display": "No battery (AC / Desktop)",
        }

    def _read_sysfs(self, path: str) -> dict:
        def read_val(filename, default=""):
            fpath = os.path.join(path, filename)
            if os.path.exists(fpath):
                try:
                    with open(fpath, "r") as f:
                        return f.read().strip()
                except Exception:
                    pass
            return default

        capacity = float(read_val("capacity", "0") or "0")
        status = read_val("status", "Unknown")

        # Health calculation
        energy_full = float(read_val("energy_full", "0") or "0")
        energy_design = float(read_val("energy_full_design", "0") or "0")
        if energy_design <= 0:
            energy_full = float(read_val("charge_full", "0") or "0")
            energy_design = float(read_val("charge_full_design", "0") or "0")

        health = (energy_full / energy_design * 100.0) if energy_design > 0 else 100.0

        # Power draw
        power_u = float(read_val("power_now", "0") or "0")
        if power_u <= 0:
            voltage = float(read_val("voltage_now", "0") or "0")
            current = float(read_val("current_now", "0") or "0")
            power_u = (voltage * current) / 1_000_000.0
        power_w = round(power_u / 1_000_000.0, 1)

        return {
            "present": True,
            "percent": capacity,
            "state": status,
            "health": round(health, 1),
            "power_w": power_w,
            "time_remaining": "",
            "display": f"{round(capacity)}% ({status}) — health {round(health, 1)}%",
        }

    def _read_upower(self) -> dict:
        try:
            res = subprocess.run(["upower", "-e"], capture_output=True, text=True, timeout=1.5)
            bat_dev = None
            for line in res.stdout.splitlines():
                if "BAT" in line:
                    bat_dev = line.strip()
                    break

            if not bat_dev:
                return {"present": False, "percent": 0.0, "state": "No battery", "health": 0.0, "power_w": 0.0, "display": "No battery"}

            info = subprocess.run(["upower", "-i", bat_dev], capture_output=True, text=True, timeout=1.5).stdout

            pct = 0.0
            state = "Unknown"
            energy_full = 0.0
            energy_design = 0.0
            energy_rate = 0.0

            for line in info.splitlines():
                parts = [p.strip() for p in line.split(":", 1)]
                if len(parts) == 2:
                    k, v = parts[0], parts[1]
                    if k == "percentage":
                        pct = float(v.replace("%", "").strip())
                    elif k == "state":
                        state = v.capitalize()
                    elif k == "energy-full":
                        energy_full = float(v.split()[0])
                    elif k == "energy-full-design":
                        energy_design = float(v.split()[0])
                    elif k == "energy-rate":
                        energy_rate = float(v.split()[0])

            health = (energy_full / energy_design * 100.0) if energy_design > 0 else 100.0

            return {
                "present": True,
                "percent": pct,
                "state": state,
                "health": round(health, 1),
                "power_w": round(energy_rate, 1),
                "time_remaining": "",
                "display": f"{round(pct)}% ({state}) — health {round(health, 1)}%",
            }
        except Exception:
            return {"present": False, "percent": 0.0, "state": "Error", "health": 0.0, "power_w": 0.0, "display": "N/A"}
