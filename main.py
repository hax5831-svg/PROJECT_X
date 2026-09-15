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
from hyprfetch.core import gpu_info
from hyprfetch.diagnose.engine import DiagnosticEngine
from hyprfetch.diagnose.selftest import run_self_test
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
  hyprfetch --gpu-info      Show detailed GPU information and exit
  hyprfetch --self-test     Check HyprFetch's own dependencies/subsystems
  hyprfetch --diagnose      Run "What the hell is happening?" diagnostic scan
  hyprfetch --theme <name>  Select theme (nova, nebula, cyberpunk, matrix, arctic, amoled, minimal)
""",
    )

    parser.add_argument("--gui", action="store_true", help="Launch PyQt6/PySide6 Cyberdeck GUI")
    parser.add_argument("--tui", "--cli", action="store_true", help="Launch terminal TUI monitor")
    parser.add_argument("--json", "--api", action="store_true", help="Output machine telemetry as JSON")
    parser.add_argument("--bench", action="store_true", help="Run benchmark mode and exit")
    parser.add_argument("--gpu-info", action="store_true", help="Show detailed GPU information and exit")
    parser.add_argument("--self-test", action="store_true", help="Check HyprFetch's own dependencies/subsystems and exit")
    parser.add_argument("--diagnose", "--diag", action="store_true", help="Run diagnostic anomaly scan and exit")
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

    # GPU Info CLI Mode
    if getattr(args, "gpu_info", False):
        palette = theme_engine.active_theme.get_terminal_palette()
        print(f"{palette['bold']}{palette['accent']}=== GPU INFORMATION ==={palette['reset']}\n")
        gpus = gpu_info.list_gpus()
        if not gpus:
            print(f"{palette['warning']}No GPU detected on this system.{palette['reset']}")
        else:
            cuda = gpu_info.cuda_status()
            for g in gpus:
                print(f"{palette['bold']}GPU {g.index}{palette['reset']}")
                print(f"  Name: {g.name}")
                print(f"  Vendor: {g.vendor}")
                print(f"  Type: {g.type.capitalize()}")
                if g.detection_source == "nvidia-smi":
                    print(f"  VRAM: {round(g.vram_used_mb)} / {round(g.vram_total_mb)} MB")
                    print(f"  Utilization: {round(g.utilization_percent)}%")
                    print(f"  Temperature: {round(g.temperature_c)}\u00b0C")
                    print(f"  Power: {round(g.power_draw_w, 1)} W / {round(g.power_limit_w, 1)} W")
                    print(f"  Driver: {g.driver or 'Unknown'}")
                    print(f"  Compute Capability: {g.compute_capability or 'Unknown'}")
                    print(f"  CUDA (driver max): {gpu_info.nvidia_cuda_driver_version() or 'Unknown'}")
                    print(f"  CUDA (PyTorch): {'Available (' + cuda.cuda_version + ')' if cuda.cuda_available else 'Unavailable'}")
                else:
                    print(f"  Utilization: {round(g.utilization_percent)}%")
                    print(f"  Temperature: {round(g.temperature_c) if g.temperature_c else 'Unknown'}\u00b0C")
                    print("  (Detailed power/VRAM telemetry requires nvidia-smi; not applicable to this adapter)")
                print()
        sys.exit(0)

    # Self-Test CLI Mode
    if getattr(args, "self_test", False):
        palette = theme_engine.active_theme.get_terminal_palette()
        print(f"{palette['bold']}{palette['accent']}=== HYPRFETCH SELF-TEST ==={palette['reset']}\n")
        results = run_self_test()
        status_colors = {
            "PASS": palette.get("secondary", palette["accent"]),
            "WARN": palette["warning"],
            "FAIL": palette["critical"],
            "SKIP": palette["dim"],
        }
        fail_count = 0
        for r in results:
            color = status_colors.get(r.status, palette["reset"])
            line = f"{color}[{r.status:4s}]{palette['reset']} {r.name}"
            if r.detail:
                line += f" {palette['dim']}- {r.detail}{palette['reset']}"
            print(line)
            if r.status == "FAIL":
                fail_count += 1
        print()
        if fail_count:
            print(f"{palette['critical']}{fail_count} check(s) FAILED.{palette['reset']}")
            sys.exit(1)
        print(f"{palette['secondary']}All required checks passed.{palette['reset']}")
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
