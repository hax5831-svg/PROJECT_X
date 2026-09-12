#!/usr/bin/env python3
"""
HyprFetch 2.0 - Next-generation live system monitor, cyberdeck dashboard, and telemetry core for Linux & Hyprland.
"""

import argparse
import json
import os
import sys

# Ensure package is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hyprfetch.bench.benchmark import BenchmarkEngine
from hyprfetch.core import HyprFetchCore
from hyprfetch.diagnose.engine import DiagnosticEngine
from hyprfetch.themes.theme_engine import ThemeEngine


def main():
    parser = argparse.ArgumentParser(
        description="HyprFetch 2.0 — Live Cyberpunk System Monitor, GUI Cyberdeck & Diagnostics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  hyprfetch                 Launch GUI Cyberdeck (or TUI if headless)
  hyprfetch --gui           Launch PyQt6/PySide6 Cyberdeck GUI
  hyprfetch --tui           Launch animated Neofetch-style terminal monitor
  hyprfetch --json          Print full JSON snapshot (for Waybar / scripts)
  hyprfetch --bench         Run CPU, GPU, RAM, Disk benchmark suite
  hyprfetch --diagnose      Run "What the hell is happening?" diagnostic scan
  hyprfetch --theme <name>  Select theme (nova, nebula, cyberpunk, matrix, arctic, amoled, minimal)
""",
    )

    parser.add_argument("--gui", action="store_true", help="Launch PyQt6/PySide6 Cyberdeck GUI")
    parser.add_argument("--tui", "--cli", action="store_true", help="Launch terminal TUI monitor")
    parser.add_argument("--json", "--api", action="store_true", help="Output machine telemetry as JSON")
    parser.add_argument("--bench", action="store_true", help="Run benchmark mode and exit")
    parser.add_argument("--diagnose", action="store_true", help="Run diagnostic anomaly scan and exit")
    parser.add_argument("--theme", type=str, default=None, help="Theme name (nova, nebula, cyberpunk, matrix, etc.)")
    parser.add_argument("-v", "--version", action="store_true", help="Show version")

    args = parser.parse_args()

    if args.version:
        from hyprfetch import __version__
        print(f"HyprFetch {__version__}")
        sys.exit(0)

    # Initialize theme engine
    theme_engine = ThemeEngine()
    if args.theme:
        theme_engine.set_theme(args.theme)

    # JSON Telemetry API Mode
    if args.json:
        core = HyprFetchCore()
        snap = core.snapshot()
        print(json.dumps(snap, indent=2))
        sys.exit(0)

    # Benchmark CLI Mode
    if args.bench:
        palette = theme_engine.active_theme.get_terminal_palette()
        print(f"{palette['bold']}{palette['accent']}=== HYPRFETCH BENCHMARK SUITE ==={palette['reset']}\n")
        engine = BenchmarkEngine()
        res = engine.run_all()
        print(f"{palette['bold']}CPU:{palette['reset']}   {res['cpu']['display']} ({res['cpu']['model']})")
        print(f"{palette['bold']}RAM:{palette['reset']}   {res['ram']['display']}")
        print(f"{palette['bold']}DISK:{palette['reset']}  {res['disk']['display']}")
        print(f"{palette['bold']}GPU:{palette['reset']}   {res['gpu']['display']} ({res['gpu']['model']})")
        print(f"\n{palette['bold']}{palette['accent']}SYSTEM SCORE: {res['system_score']} / 100{palette['reset']}")
        print(f"{palette['dim']}Saved to ~/.local/share/hyprfetch/benchmarks/{palette['reset']}")
        sys.exit(0)

    # Diagnostic CLI Mode
    if args.diagnose:
        palette = theme_engine.active_theme.get_terminal_palette()
        print(f"{palette['bold']}{palette['accent']}=== HYPRFETCH DIAGNOSTIC RADAR ==={palette['reset']}\n")
        core = HyprFetchCore()
        diag = DiagnosticEngine()
        reports = diag.run_diagnostics(core.snapshot())
        for r in reports:
            color = palette["critical"] if r.severity == "CRITICAL" else (palette["warning"] if r.severity == "WARNING" else palette["secondary"])
            print(f"{color}[{r.severity}] {r.title}{palette['reset']}")
            print(f"  Summary: {r.summary}")
            print(f"  Details: {r.details}")
            if r.culprits:
                print(f"  Top Culprit Processes:")
                for c in r.culprits:
                    print(f"    - PID {c['pid']} ({c['name']}): {c['usage']}")
            if r.suggested_commands:
                print(f"  Safe Suggested Commands:")
                for cmd in r.suggested_commands:
                    print(f"    $ {cmd}")
            print()
        sys.exit(0)

    # TUI vs GUI Decision
    has_display = bool(os.getenv("WAYLAND_DISPLAY") or os.getenv("DISPLAY"))
    launch_gui = args.gui or (has_display and not args.tui)

    if launch_gui:
        try:
            from hyprfetch.ui.qt_compat import QApplication
            from hyprfetch.ui.dashboard import HyprFetchDashboard

            app = QApplication(sys.argv)
            app.setApplicationName("HyprFetch")

            core = HyprFetchCore()
            dashboard = HyprFetchDashboard(core=core, theme_engine=theme_engine)
            dashboard.show()
            sys.exit(app.exec())
        except Exception as e:
            print(f"[HyprFetch] Could not launch GUI ({e}). Falling back to terminal TUI...", file=sys.stderr)

    # Terminal TUI Mode
    from hyprfetch.tui.terminal import TerminalApp
    core = HyprFetchCore()
    app = TerminalApp(core=core, theme_engine=theme_engine)
    app.run()


if __name__ == "__main__":
    main()
