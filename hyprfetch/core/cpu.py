"""CPU monitoring module measuring utilization, frequency, and thermal sensors."""

import glob
import os
import re
import shutil
import subprocess
from hyprfetch.core.system import TimeSeriesBuffer


class CPUMonitor:
    """Monitors CPU usage, per-core utilization, clock frequency, and temperatures."""

    def __init__(self):
        self.util_history = TimeSeriesBuffer(max_points=120, max_seconds=120.0)
        self.temp_history = TimeSeriesBuffer(max_points=120, max_seconds=120.0)

        self.name, self.short_name, self.core_count = self._get_cpu_info()
        self.has_sensors = shutil.which("sensors") is not None

        # Jiffies tracking for /proc/stat
        self._prev_total = 0
        self._prev_idle = 0
        self._prev_per_core = []
        self._init_stat()

    def _get_cpu_info(self) -> tuple[str, str, int]:
        name = "Unknown CPU"
        cores = os.cpu_count() or 1
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("model name"):
                        name = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass

        short_name = name
        short_name = re.sub(r"\(R\)|\(TM\)|Processor|CPU|13th Gen |12th Gen |14th Gen ", "", short_name)
        short_name = re.sub(r"\s+", " ", short_name).strip()

        return name, short_name, cores

    def _init_stat(self):
        try:
            with open("/proc/stat", "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines:
                parts = line.split()
                if parts[0] == "cpu":
                    vals = [int(x) for x in parts[1:]]
                    self._prev_idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
                    self._prev_total = sum(vals)
                elif parts[0].startswith("cpu") and parts[0][3:].isdigit():
                    vals = [int(x) for x in parts[1:]]
                    idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
                    self._prev_per_core.append((sum(vals), idle))
        except Exception:
            pass

    def get_utilization(self) -> tuple[float, list[float]]:
        total_util = 0.0
        per_core_utils = []

        try:
            with open("/proc/stat", "r", encoding="utf-8") as f:
                lines = f.readlines()

            curr_per_core = []
            for line in lines:
                parts = line.split()
                if parts[0] == "cpu":
                    vals = [int(x) for x in parts[1:]]
                    idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
                    total = sum(vals)

                    d_total = total - self._prev_total
                    d_idle = idle - self._prev_idle
                    self._prev_total = total
                    self._prev_idle = idle

                    if d_total > 0:
                        total_util = max(0.0, min(100.0, (d_total - d_idle) / d_total * 100.0))
                elif parts[0].startswith("cpu") and parts[0][3:].isdigit():
                    vals = [int(x) for x in parts[1:]]
                    idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
                    curr_per_core.append((sum(vals), idle))

            if self._prev_per_core and len(self._prev_per_core) == len(curr_per_core):
                for (prev_tot, prev_id), (cur_tot, cur_id) in zip(self._prev_per_core, curr_per_core):
                    dt = cur_tot - prev_tot
                    di = cur_id - prev_id
                    u = max(0.0, min(100.0, (dt - di) / dt * 100.0)) if dt > 0 else 0.0
                    per_core_utils.append(round(u, 1))

            self._prev_per_core = curr_per_core
        except Exception:
            pass

        self.util_history.append(total_util)
        return round(total_util, 1), per_core_utils

    def get_temperature(self) -> float:
        temp = 0.0

        if self.has_sensors:
            try:
                res = subprocess.run(["sensors"], capture_output=True, text=True, timeout=1.5)
                if res.returncode == 0:
                    # Look for Package id 0, Tctl, Tdie, Core 0, or dell_smm temp1
                    for line in res.stdout.splitlines():
                        m = re.search(r"(?:Package id 0|Tctl|Tdie|Core 0|temp1):\s*\+?([\d\.]+)°C", line)
                        if m:
                            temp = float(m.group(1))
                            break
            except Exception:
                pass

        if temp <= 0.0:
            # Fallback to sysfs thermal zones
            for path in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
                try:
                    with open(path, "r") as f:
                        val = float(f.read().strip())
                        if val > 1000:
                            val /= 1000.0
                        if 10.0 <= val <= 115.0:
                            temp = val
                            break
                except Exception:
                    pass

        self.temp_history.append(temp)
        return round(temp, 1)

    def get_frequency_ghz(self) -> float:
        try:
            freqs = []
            for path in glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq"):
                with open(path, "r") as f:
                    freqs.append(float(f.read().strip()) / 1_000_000.0)
            if freqs:
                return round(sum(freqs) / len(freqs), 2)
        except Exception:
            pass

        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "cpu MHz" in line:
                        mhz = float(line.split(":", 1)[1].strip())
                        return round(mhz / 1000.0, 2)
        except Exception:
            pass

        return 0.0

    def poll(self) -> dict:
        util, per_core = self.get_utilization()
        temp = self.get_temperature()
        freq = self.get_frequency_ghz()

        return {
            "name": self.name,
            "short_name": self.short_name,
            "cores": self.core_count,
            "utilization": util,
            "per_core": per_core,
            "temp": temp,
            "freq_ghz": freq,
            "display": f"{self.short_name}  {util}%  {temp}°C  {freq}GHz",
        }
