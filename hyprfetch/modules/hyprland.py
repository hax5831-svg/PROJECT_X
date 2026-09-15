"""Hyprland compositor controller and workspace state tracker."""

import json
import os
import shutil

from hyprfetch.core.debug_log import log_debug
from hyprfetch.core.shell import run_action, run_detached, run_query


class HyprlandManager:
    """Interacts with Hyprland IPC via hyprctl."""

    def __init__(self):
        self.is_running = self._check_running()

    def _check_running(self) -> bool:
        if os.getenv("HYPRLAND_INSTANCE_SIGNATURE"):
            return True
        return shutil.which("hyprctl") is not None

    def _query_json(self, cmd: list[str], timeout: float):
        """Run a `hyprctl ... -j` command and parse its JSON output.
        Returns None on any failure (missing binary, timeout, bad JSON).
        """
        out = run_query(cmd, timeout=timeout)
        if not out:
            return None
        try:
            return json.loads(out)
        except Exception as e:
            log_debug(f"hyprctl JSON parse failed for {cmd}: {e}")
            return None

    def get_workspaces(self) -> list[dict]:
        if not self.is_running:
            return []
        data = self._query_json(["hyprctl", "workspaces", "-j"], timeout=1.2)
        if data is None:
            return []
        return sorted(data, key=lambda w: w.get("id", 0))

    def get_active_workspace(self) -> int:
        if not self.is_running:
            return 1
        data = self._query_json(["hyprctl", "activeworkspace", "-j"], timeout=1.0)
        if data is None:
            return 1
        return int(data.get("id", 1))

    def get_active_window(self) -> dict:
        if not self.is_running:
            return {"title": "Desktop", "class": "", "workspace": 1}
        data = self._query_json(["hyprctl", "activewindow", "-j"], timeout=1.0)
        if data is None:
            return {"title": "", "class": "", "workspace": 1}
        return {
            "title": data.get("title", ""),
            "class": data.get("class", ""),
            "workspace": data.get("workspace", {}).get("id", 1),
        }

    def switch_workspace(self, ws_id: int) -> bool:
        return run_action(["hyprctl", "dispatch", "workspace", str(ws_id)], timeout=1.0)

    def reload(self) -> bool:
        return run_action(["hyprctl", "reload"], timeout=1.5)

    def lock(self) -> bool:
        # Try hyprlock, swaylock, or loginctl
        for lock_cmd in ("hyprlock", "swaylock"):
            if shutil.which(lock_cmd) and run_detached([lock_cmd]):
                return True
        return run_action(["loginctl", "lock-session"], timeout=1.0)

    def logout(self) -> bool:
        return run_action(["hyprctl", "dispatch", "exit"], timeout=1.5)
