"""MPRIS media controller and metadata provider via playerctl."""

import shutil
import subprocess


class MediaManager:
    """Interfaces with MPRIS media players for metadata and playback controls."""

    def __init__(self):
        self.has_playerctl = shutil.which("playerctl") is not None

    def get_info(self) -> dict:
        if not self.has_playerctl:
            return {
                "available": False,
                "status": "Stopped",
                "title": "playerctl not installed",
                "artist": "",
                "album": "",
                "player": "",
                "art_url": "",
                "display": "playerctl not installed",
            }

        try:
            # Check players
            players_res = subprocess.run(["playerctl", "-l"], capture_output=True, text=True, timeout=1.0)
            if players_res.returncode != 0 or not players_res.stdout.strip():
                return {
                    "available": True,
                    "status": "Stopped",
                    "title": "Nothing playing",
                    "artist": "",
                    "album": "",
                    "player": "",
                    "art_url": "",
                    "display": "Nothing playing",
                }

            player = players_res.stdout.strip().splitlines()[0]

            # Query status and metadata in one call using format
            fmt = "{{status}}\t{{title}}\t{{artist}}\t{{album}}\t{{mpris:artUrl}}"
            cmd = ["playerctl", "metadata", "--format", fmt]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=1.2)

            status = "Stopped"
            title = ""
            artist = ""
            album = ""
            art_url = ""

            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split("\t")
                status = parts[0] if len(parts) > 0 else "Stopped"
                title = parts[1] if len(parts) > 1 else ""
                artist = parts[2] if len(parts) > 2 else ""
                album = parts[3] if len(parts) > 3 else ""
                art_url = parts[4] if len(parts) > 4 else ""

            if not title and not artist:
                display = "Nothing playing"
            elif title and artist:
                display = f"{artist} — {title}"
            else:
                display = title or artist

            return {
                "available": True,
                "status": status,
                "title": title or "Unknown Track",
                "artist": artist or "Unknown Artist",
                "album": album,
                "player": player,
                "art_url": art_url,
                "display": display,
            }
        except Exception:
            return {
                "available": True,
                "status": "Stopped",
                "title": "Nothing playing",
                "artist": "",
                "album": "",
                "player": "",
                "art_url": "",
                "display": "Nothing playing",
            }

    def play_pause(self) -> bool:
        if not self.has_playerctl:
            return False
        try:
            subprocess.run(["playerctl", "play-pause"], check=False, timeout=1.0)
            return True
        except Exception:
            return False

    def next_track(self) -> bool:
        if not self.has_playerctl:
            return False
        try:
            subprocess.run(["playerctl", "next"], check=False, timeout=1.0)
            return True
        except Exception:
            return False

    def previous_track(self) -> bool:
        if not self.has_playerctl:
            return False
        try:
            subprocess.run(["playerctl", "previous"], check=False, timeout=1.0)
            return True
        except Exception:
            return False
