"""MPRIS media controller and metadata provider via playerctl."""

import shutil

from hyprfetch.core.shell import run_action, run_query_raw

_NOTHING_PLAYING = {
    "available": True,
    "status": "Stopped",
    "title": "Nothing playing",
    "artist": "",
    "album": "",
    "player": "",
    "art_url": "",
    "display": "Nothing playing",
}


class MediaManager:
    """Interfaces with MPRIS media players for metadata and playback controls."""

    def __init__(self):
        self.has_playerctl = shutil.which("playerctl") is not None

    def get_info(self) -> dict:
        if not self.has_playerctl:
            return {
                **_NOTHING_PLAYING,
                "available": False,
                "title": "playerctl not installed",
                "display": "playerctl not installed",
            }

        players_res = run_query_raw(["playerctl", "-l"], timeout=1.0)
        if players_res is None or players_res.returncode != 0 or not players_res.stdout.strip():
            return dict(_NOTHING_PLAYING)

        player = players_res.stdout.strip().splitlines()[0]

        # Query status and metadata in one call using format
        fmt = "{{status}}\t{{title}}\t{{artist}}\t{{album}}\t{{mpris:artUrl}}"
        res = run_query_raw(["playerctl", "metadata", "--format", fmt], timeout=1.2)

        status = "Stopped"
        title = ""
        artist = ""
        album = ""
        art_url = ""

        if res is not None and res.returncode == 0 and res.stdout.strip():
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

    def play_pause(self) -> bool:
        if not self.has_playerctl:
            return False
        return run_action(["playerctl", "play-pause"], timeout=1.0)

    def next_track(self) -> bool:
        if not self.has_playerctl:
            return False
        return run_action(["playerctl", "next"], timeout=1.0)

    def previous_track(self) -> bool:
        if not self.has_playerctl:
            return False
        return run_action(["playerctl", "previous"], timeout=1.0)
