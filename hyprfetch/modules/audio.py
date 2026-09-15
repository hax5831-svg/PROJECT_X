"""PipeWire / WirePlumber audio controls and sink routing."""

import re
import shutil

from hyprfetch.core.shell import run_action, run_query, run_query_raw


class AudioManager:
    """Manages audio volume, muting, and sink selection via WirePlumber / PulseAudio."""

    def __init__(self):
        self.has_wpctl = shutil.which("wpctl") is not None
        self.has_pactl = shutil.which("pactl") is not None

    def get_status(self) -> dict:
        vol = 0
        muted = False

        if self.has_wpctl:
            out = run_query(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], timeout=1.0)
            if out is not None:
                muted = "[MUTED]" in out
                m = re.search(r"Volume:\s*([\d\.]+)", out)
                if m:
                    vol = int(round(float(m.group(1)) * 100))
        elif self.has_pactl:
            out = run_query(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], timeout=1.0)
            if out is not None:
                m = re.search(r"(\d+)%", out)
                if m:
                    vol = int(m.group(1))

        return {"volume": min(100, max(0, vol)), "muted": muted}

    def set_volume(self, pct: int) -> bool:
        pct = max(0, min(100, pct))
        if self.has_wpctl:
            return run_action(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{pct}%"], timeout=1.0)
        elif self.has_pactl:
            return run_action(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{pct}%"], timeout=1.0)
        return False

    def toggle_mute(self) -> bool:
        if self.has_wpctl:
            return run_action(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"], timeout=1.0)
        elif self.has_pactl:
            return run_action(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"], timeout=1.0)
        return False

    def get_sinks(self) -> list[dict]:
        sinks = []
        if not self.has_wpctl:
            return sinks

        res = run_query_raw(["wpctl", "status"], timeout=1.5)
        if res is None or res.returncode != 0:
            return sinks

        try:
            in_sinks = False
            for line in res.stdout.splitlines():
                if "Sinks:" in line:
                    in_sinks = True
                    continue
                if in_sinks:
                    if line.strip() == "" or "Sources:" in line or "Filters:" in line or "Streams:" in line:
                        break

                    # Example line:
                    # │  *   57. 700 Series Chipset Family HD Audio Speaker [vol: 0.75]
                    m = re.search(r"([*]?)\s*(\d+)\.\s+(.*?)(?:\s+\[vol:.*\])?$", line)
                    if m:
                        is_default = bool(m.group(1).strip())
                        sink_id = int(m.group(2))
                        desc = m.group(3).strip()

                        # Simplify description (e.g. Speaker, Headphones, HDMI)
                        short_desc = desc
                        for prefix in ("700 Series Chipset Family HD Audio ", "GA107 High Definition Audio Controller "):
                            short_desc = short_desc.replace(prefix, "")

                        # Deduplicate or group
                        sinks.append({
                            "id": sink_id,
                            "name": short_desc,
                            "full_name": desc,
                            "is_default": is_default,
                        })

            # Deduplicate by name, preferring the active/default sink
            seen_names = {}
            for s in sinks:
                name = s["name"]
                if name not in seen_names or s["is_default"]:
                    seen_names[name] = s
            sinks = list(seen_names.values())
        except Exception:
            pass

        return sinks

    def set_sink(self, sink_id: int) -> bool:
        if not self.has_wpctl:
            return False
        return run_action(["wpctl", "set-default", str(sink_id)], timeout=1.0)
