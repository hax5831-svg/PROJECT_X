"""Interactive terminal companion (TUI) powered by the unified HyprFetch core."""

import os
import select
import sys
import termios
import time
import tty
from hyprfetch.bench.benchmark import BenchmarkEngine
from hyprfetch.core import HyprFetchCore
from hyprfetch.diagnose.engine import DiagnosticEngine
from hyprfetch.modules import HyprlandManager, MediaManager
from hyprfetch.themes.theme_engine import ThemeEngine

LOGO_FRAMES = [
    "    ▄▄▄▄▄▄▄▄▄▄▄▄    ",
    "  ▄██▀▀▀▀▀▀▀▀▀▀██▄  ",
    " ██▀   ██    ██   ▀██ ",
    " ██    ██    ██    ██ ",
    " ██    ██████████    ██ ",
    " ██    ██    ██    ██ ",
    " ▀██▄            ▄██▀ ",
    "    ▀▀▀▀▀▀▀▀▀▀▀▀    ",
]

SPARK_CHARS = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]


def make_sparkline(values: list[float], max_val: float = 100.0, width: int = 12) -> str:
    if not values:
        return " " * width
    recent = values[-width:]
    chars = []
    for v in recent:
        ratio = max(0.0, min(1.0, v / max_val))
        idx = int(ratio * (len(SPARK_CHARS) - 1))
        chars.append(SPARK_CHARS[idx])
    return "".join(chars).ljust(width)


class TerminalApp:
    """Animated Neofetch-style live terminal dashboard."""

    def __init__(self, core: HyprFetchCore = None, theme_engine: ThemeEngine = None):
        self.core = core or HyprFetchCore()
        self.theme_engine = theme_engine or ThemeEngine()
        self.hyprland = HyprlandManager()
        self.media = MediaManager()
        self.diag = DiagnosticEngine()
        self.bench = BenchmarkEngine()
        self.theme_keys = list(self.theme_engine.available_themes.keys())
        self.cur_theme_idx = 0

    def run(self):
        old_settings = None
        if sys.stdin.isatty():
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())

        # Hide cursor and clear
        sys.stdout.write("\033[?25l\033[2J")
        sys.stdout.flush()

        frame = 0
        tick = 0
        stat_interval = 5  # Every 5 ticks (1 second if tick is 0.2s)
        snap = self.core.snapshot()
        media_info = self.media.get_info()

        try:
            while True:
                if tick % stat_interval == 0:
                    snap = self.core.snapshot()
                    media_info = self.media.get_info()

                self._render(frame, snap, media_info)
                frame = (frame + 1) % len(LOGO_FRAMES)
                tick += 1

                # Check non-blocking input
                if sys.stdin.isatty():
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.2)
                    if rlist:
                        ch = sys.stdin.read(1)
                        if ch == "q" or ch == "\x03":  # q or Ctrl+C
                            break
                        elif ch == "t":  # cycle themes
                            self.cur_theme_idx = (self.cur_theme_idx + 1) % len(self.theme_keys)
                            self.theme_engine.set_theme(self.theme_keys[self.cur_theme_idx])
                        elif ch == " ":  # play/pause
                            self.media.play_pause()
                        elif ch == "n":  # next
                            self.media.next_track()
                        elif ch == "p":  # prev
                            self.media.previous_track()
                        elif ch == "d":  # diagnose
                            self._render_diag(snap)
                        elif ch == "b":  # bench
                            self._render_bench()
                else:
                    time.sleep(0.2)
        finally:
            # Restore cursor and terminal
            sys.stdout.write("\033[?25h\033[0m\n")
            sys.stdout.flush()
            if old_settings and sys.stdin.isatty():
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    def _render(self, active_frame: int, snap: dict, media_info: dict):
        p = self.theme_engine.active_theme.get_terminal_palette()
        accent = p["accent"]
        accent2 = p["secondary"]
        bold = p["bold"]
        dim = p["dim"]
        reset = p["reset"]
        warn = p["warning"]

        sys_data = snap["system"]
        gpu = snap["gpu"]
        cpu = snap["cpu"]
        bat = snap["battery"]
        net = snap["network"]

        cpu_spark = make_sparkline(self.core.cpu.util_history.values(), 100.0, 10)
        gpu_spark = make_sparkline(self.core.gpu.util_history.values(), 100.0, 10)

        # Workspace pills
        ws_list = self.hyprland.get_workspaces()
        active_ws = self.hyprland.get_active_workspace()
        ws_str = " ".join(
            f"{bold}{accent}[{w['id']}]{reset}" if w["id"] == active_ws else f"{dim}{w['id']}{reset}"
            for w in ws_list[:6]
        ) or "None"

        # Media status
        media_disp = media_info.get("display", "Nothing playing")
        if len(media_disp) > 36:
            media_disp = media_disp[:33] + "..."

        sep = "―" * 38
        info_lines = [
            f"{bold}{accent}{sys_data['user']}{reset}{dim}@{reset}{bold}{accent}{sys_data['host']}{reset}  {dim}[{self.theme_engine.active_theme.name}]{reset}",
            f"{dim}{sep}{reset}",
            f"{bold}{accent2}GPU{reset}       {gpu['display']} {dim}[{gpu_spark}]{reset}",
            f"{bold}{accent2}CPU{reset}       {cpu['display']} {dim}[{cpu_spark}]{reset}",
            f"{bold}{accent2}RAM{reset}       {sys_data['ram']['display']} ({sys_data['ram']['percent']}%)",
            f"{bold}{accent2}Battery{reset}   {bat['display']}",
            f"{bold}{accent2}Disk{reset}      {sys_data['disk']['display']}",
            f"{bold}{accent2}Net{reset}       {net['display']}",
            f"{bold}{accent2}Hyprland{reset}  WS: {ws_str}",
            f"{bold}{accent2}Media{reset}     {media_disp}",
            f"{dim}{sep}{reset}",
            f"{dim}Controls: [q]uit  [t]heme  [d]iagnose  [b]ench  [space]pause{reset}",
        ]

        # Home cursor and redraw
        output = ["\033[H"]
        total_rows = max(len(LOGO_FRAMES), len(info_lines))

        for i in range(total_rows):
            logo_part = ""
            if i < len(LOGO_FRAMES):
                if i == active_frame:
                    logo_part = f"{bold}{accent}{LOGO_FRAMES[i]}{reset}"
                else:
                    logo_part = f"{dim}{LOGO_FRAMES[i]}{reset}"
            else:
                logo_part = " " * 22

            info_part = info_lines[i] if i < len(info_lines) else ""
            output.append(f"{logo_part}  {info_part}\033[K\n")

        output.append("\033[J")
        sys.stdout.write("".join(output))
        sys.stdout.flush()

    def _render_diag(self, snap: dict):
        sys.stdout.write("\033[2J\033[H")
        p = self.theme_engine.active_theme.get_terminal_palette()
        print(f"{p['bold']}{p['accent']}=== HYPRFETCH AUTOMATIC DIAGNOSTICS ==={p['reset']}\n")

        reports = self.diag.run_diagnostics(snap)
        for r in reports:
            color = p["critical"] if r.severity == "CRITICAL" else (p["warning"] if r.severity == "WARNING" else p["secondary"])
            print(f"{color}[{r.severity}] {r.title}{p['reset']}")
            print(f"  Summary: {r.summary}")
            print(f"  Details: {r.details}")
            if r.culprits:
                print(f"  Top Culprits:")
                for c in r.culprits:
                    print(f"    - PID {c['pid']} ({c['name']}): {c['usage']}")
            if r.suggested_commands:
                print(f"  Safe Suggested Commands:")
                for cmd in r.suggested_commands:
                    print(f"    $ {cmd}")
            print()

        print(f"{p['dim']}Press any key to resume monitoring...{p['reset']}")
        sys.stdout.flush()
        if sys.stdin.isatty():
            _ = sys.stdin.read(1)
        sys.stdout.write("\033[2J")

    def _render_bench(self):
        sys.stdout.write("\033[2J\033[H")
        p = self.theme_engine.active_theme.get_terminal_palette()
        print(f"{p['bold']}{p['accent']}=== HYPRFETCH BENCHMARK MODE ==={p['reset']}\n")
        print("Running tests (CPU, RAM, Disk, GPU)...")
        sys.stdout.flush()

        res = self.bench.run_all()
        print(f"\n{p['bold']}CPU:{p['reset']}   {res['cpu']['display']}")
        print(f"{p['bold']}RAM:{p['reset']}   {res['ram']['display']}")
        print(f"{p['bold']}DISK:{p['reset']}  {res['disk']['display']}")
        print(f"{p['bold']}GPU:{p['reset']}   {res['gpu']['display']}")
        print(f"\n{p['bold']}{p['accent']}SYSTEM SCORE: {res['system_score']} / 100{p['reset']}\n")

        print(f"{p['dim']}Saved to ~/.local/share/hyprfetch/benchmarks/. Press any key to return...{p['reset']}")
        sys.stdout.flush()
        if sys.stdin.isatty():
            _ = sys.stdin.read(1)
        sys.stdout.write("\033[2J")
