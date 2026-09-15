"""Screen backlight controller via brightnessctl or sysfs."""

import glob
import os
import shutil

from hyprfetch.core.shell import run_action, run_query


class BrightnessManager:
    """Controls display backlight intensity."""

    def __init__(self):
        self.has_brightnessctl = shutil.which("brightnessctl") is not None

    def get_brightness(self) -> int:
        if self.has_brightnessctl:
            cur_out = run_query(["brightnessctl", "get"], timeout=1.0)
            max_out = run_query(["brightnessctl", "max"], timeout=1.0)
            if cur_out is not None and max_out is not None:
                try:
                    cur = float(cur_out)
                    max_b = float(max_out)
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
            return run_action(["brightnessctl", "set", f"{pct}%"], timeout=1.0)
        return False
