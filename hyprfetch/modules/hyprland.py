"""Hyprland compositor controller and workspace state tracker."""

import json
import os
import shutil
import subprocess


class HyprlandManager:
    """Interacts with Hyprland IPC via hyprctl."""

    def __init__(self):
        self.is_running = self._check_running()

    def _check_running(self) -> bool:
        if os.getenv("HYPRLAND_INSTANCE_SIGNATURE"):
            return True
        return shutil.which("hyprctl") is not None

    def get_workspaces(self) -> list[dict]:
        if not self.is_running:
            return []

        try:
            res = subprocess.run(["hyprctl", "workspaces", "-j"], capture_output=True, text=True, timeout=1.2)
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout.strip())
                # Sort by workspace ID
                return sorted(data, key=lambda w: w.get("id", 0))
        except Exception:
            pass

        return []

    def get_active_workspace(self) -> int:
        if not self.is_running:
            return 1
        try:
            res = subprocess.run(["hyprctl", "activeworkspace", "-j"], capture_output=True, text=True, timeout=1.0)
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout.strip())
                return int(data.get("id", 1))
        except Exception:
            pass
        return 1

    def get_active_window(self) -> dict:
        if not self.is_running:
            return {"title": "Desktop", "class": "", "workspace": 1}
        try:
            res = subprocess.run(["hyprctl", "activewindow", "-j"], capture_output=True, text=True, timeout=1.0)
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout.strip())
                return {
                    "title": data.get("title", ""),
                    "class": data.get("class", ""),
                    "workspace": data.get("workspace", {}).get("id", 1),
                }
        except Exception:
            pass
        return {"title": "", "class": "", "workspace": 1}

    def switch_workspace(self, ws_id: int) -> bool:
        try:
            subprocess.run(["hyprctl", "dispatch", "workspace", str(ws_id)], check=False, timeout=1.0)
            return True
        except Exception:
            return False

    def reload(self) -> bool:
        try:
            subprocess.run(["hyprctl", "reload"], check=False, timeout=1.5)
            return True
        except Exception:
            return False

    def lock(self) -> bool:
        # Try hyprlock, swaylock, or loginctl
        for lock_cmd in ("hyprlock", "swaylock"):
            if shutil.which(lock_cmd):
                try:
                    subprocess.Popen([lock_cmd])
                    return True
                except Exception:
                    pass

        try:
            subprocess.run(["loginctl", "lock-session"], check=False, timeout=1.0)
            return True
        except Exception:
            return False

    def logout(self) -> bool:
        try:
            subprocess.run(["hyprctl", "dispatch", "exit"], check=False, timeout=1.5)
            return True
        except Exception:
            return False
