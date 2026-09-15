"""Wallpaper cycler and controller supporting hyprpaper, swww, and swaybg."""

import glob
import os
import random
import shutil

from hyprfetch.core.shell import run_action, run_query_raw


class WallpaperManager:
    """Manages wallpaper cycling (previous, next, random) on Hyprland."""

    IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")

    def __init__(self):
        self.wallpapers = self._find_wallpapers()
        self.current_idx = 0
        self.has_hyprpaper = shutil.which("hyprpaper") is not None
        self.has_swww = shutil.which("swww") is not None

    def _find_wallpapers(self) -> list[str]:
        dirs_to_search = [
            os.path.expanduser("~/Pictures/Wallpapers"),
            os.path.expanduser("~/Pictures/wallpapers"),
            os.path.expanduser("~/Pictures"),
            os.path.expanduser("~/.config/hypr"),
            os.path.expanduser("~/.config/backgrounds"),
            "/usr/share/backgrounds",
        ]

        found = []
        for d in dirs_to_search:
            if os.path.exists(d):
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.lower().endswith(self.IMAGE_EXTS):
                            found.append(os.path.join(root, f))
        return sorted(list(set(found)))

    def apply_wallpaper(self, path: str) -> bool:
        if not path or not os.path.exists(path):
            return False

        # Try hyprctl hyprpaper
        res = run_query_raw(["hyprctl", "hyprpaper", "listloaded"], timeout=1.0)
        if res is not None and res.returncode == 0:
            run_action(["hyprctl", "hyprpaper", "preload", path], timeout=1.5)
            run_action(["hyprctl", "hyprpaper", "wallpaper", f",{path}"], timeout=1.5)
            return True

        # Try swww
        if self.has_swww and run_action(["swww", "img", path, "--transition-type", "wipe"], timeout=1.5):
            return True

        # Try feh fallback
        if shutil.which("feh") and run_action(["feh", "--bg-fill", path], timeout=1.5):
            return True

        return False

    def next_wallpaper(self) -> str | None:
        if not self.wallpapers:
            return None
        self.current_idx = (self.current_idx + 1) % len(self.wallpapers)
        chosen = self.wallpapers[self.current_idx]
        self.apply_wallpaper(chosen)
        return chosen

    def previous_wallpaper(self) -> str | None:
        if not self.wallpapers:
            return None
        self.current_idx = (self.current_idx - 1) % len(self.wallpapers)
        chosen = self.wallpapers[self.current_idx]
        self.apply_wallpaper(chosen)
        return chosen

    def random_wallpaper(self) -> str | None:
        if not self.wallpapers:
            return None
        self.current_idx = random.randint(0, len(self.wallpapers) - 1)
        chosen = self.wallpapers[self.current_idx]
        self.apply_wallpaper(chosen)
        return chosen
