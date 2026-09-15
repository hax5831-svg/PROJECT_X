"""Minimal opt-in debug logging.

HyprFetch intentionally stays silent about *expected* failures -- a missing
optional CLI tool (playerctl, brightnessctl, sensors, ...) is normal, not a
bug, and this is a desktop fetch/monitor tool that shouldn't spam stdout or
stderr during ordinary use.

But "silent by default" is not the same as "impossible to debug". Setting
HYPRFETCH_DEBUG=1 writes those otherwise-swallowed failures to
~/.cache/hyprfetch/debug.log, so a "why isn't my GPU/audio/media detected"
investigation has something concrete to look at instead of nothing.
"""

import os
import time
from pathlib import Path

_ENABLED = os.environ.get("HYPRFETCH_DEBUG", "") not in ("", "0", "false", "False")
_LOG_PATH = Path(os.path.expanduser("~/.cache/hyprfetch/debug.log"))


def log_debug(message: str) -> None:
    """Append a debug line if HYPRFETCH_DEBUG is set; otherwise a no-op.

    Never raises -- a logging failure must not take down the caller.
    """
    if not _ENABLED:
        return
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass
