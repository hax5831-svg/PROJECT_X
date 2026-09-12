"""Screen backlight controller via brightnessctl or sysfs."""

import glob
import os
import shutil
import subprocess


class BrightnessManager:
    """Controls display backlight intensity."""

    def __init__(self):
        self.has_brightnessctl = shutil.which("brightnessctl") is not None

    def get_brightness(self) -> int:
        if self.has_brightnessctl:
            try:
                cur_res = subprocess.run(["brightnessctl", "get"], capture_output=True, text=True, timeout=1.0)
                max_res = subprocess.run(["brightnessctl", "max"], capture_output=True, text=True, timeout=1.0)
                if cur_res.returncode == 0 and max_res.returncode == 0:
                    cur = float(cur_res.stdout.strip())
                    max_b = float(max_res.stdout.strip())
                    if max_b > 0:
                        return int(round((cur / max_b) * 100))
            except Exception:
                pass

        # Fallback to /sys/class/backlight
        for dev in glob.glob("/sys/class/backlight/*"):
            try:
                with open(os.path.join(dev, "brightness"), "r") as f:
                    cur = float(f.read().strip())
                with open(os.path.join(dev, "max_brightness"), "r") as f:
                    max_b = float(f.read().strip())
                if max_b > 0:
                    return int(round((cur / max_b) * 100))
            except Exception:
                pass

        return 100

    def set_brightness(self, pct: int) -> bool:
        pct = max(1, min(100, pct))
        if self.has_brightnessctl:
            try:
                subprocess.run(["brightnessctl", "set", f"{pct}%"], check=False, timeout=1.0)
                return True
            except Exception:
                return False
        return False
