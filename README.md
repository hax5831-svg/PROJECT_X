# ⚡ HyprFetch 2.0 — Cyberdeck System Monitor & GUI Companion

A next-generation cyberpunk live system monitor, Qt GUI cyberdeck, and diagnostic companion built for Linux and Hyprland setups.

Unlike static fetch tools, **HyprFetch 2.0** is powered by a unified modular telemetry core driving three synchronized interfaces: a **PyQt6 / PySide6 Cyberdeck GUI**, an animated **Terminal TUI with sparkline graphs**, and a **JSON Streaming Telemetry API** for Waybar and desktop widgets.

```
                 HYPRFETCH CORE
                       │
          ┌────────────┼────────────┐
          ↓            ↓            ↓
      Terminal        GUI        API
       TUI       PyQt6/PySide6   JSON
          │            │            │
          └────────────┴────────────┘
                       ↓
                  Linux system
```

---

## 🚀 Key Features

### 🖥️ 1. Cyberpunk GUI Cyberdeck
* **Real-Time Telemetry Cards**: Instant visual cards for GPU (RTX / AMD / Intel), CPU (utilization, temp, frequency, core count), RAM (allocation, free, swap), and Network (active interface, download / upload rates).
* **Hyprland Workspace Radar**: Live interactive workspace badges showing active workspace, window counts, and active window titles. Clicking any badge instantly switches to that workspace via IPC.
* **Now Playing MPRIS Media Bar**: Live track title, artist, status indicator, and interactive controls (Previous, Play/Pause, Next).

### 📊 2. Real-Time Hardware Graphs
* **60–120s Historical Memory**: Sliding-window time-series ring buffers tracking metrics over time.
* **Cyberpunk Neon Visuals**: Smooth cubic Bézier anti-aliased curves, multi-pass neon glow strokes, dynamic time grids (`-60s`, `-30s`, `NOW`), and gradient area fills.
* **Separate Dedicated Graphs**:
  * GPU Utilization (%)
  * CPU Utilization (%)
  * RAM Allocation (%)
  * Temperatures (°C) for both CPU and GPU
  * Network Traffic (↓ Download and ↑ Upload in KB/s & MB/s)
  * Power Consumption (Watts) and Battery Health

### 🎛️ 3. Interactive System Controls
* **Audio Volume & Mute**: Slider with live percentage and one-click toggle mute via PipeWire / WirePlumber (`wpctl` & `pactl`).
* **Audio Output Routing**: Instantly switch output sinks between Speakers, Headphones, HDMI / DisplayPort outputs.
* **Display Brightness**: Backlight intensity slider via `brightnessctl` or sysfs.
* **Wallpaper Cycler**: Instant Previous, Next, and Random wallpaper cycling integrated with `hyprpaper`, `swww`, or `feh` across `~/Pictures/Wallpapers`.
* **Hyprland Session Controls**: One-click Reload (`hyprctl reload`), Session Lock (`hyprlock` / `swaylock`), and Logout (`hyprctl dispatch exit`).

### 🧠 4. Automatic "What the hell is happening?" Diagnostics
* **Live Anomaly Detection**:
  * ⚠ High GPU VRAM allocation (>85%)
  * ⚠ GPU / CPU Thermal Throttling (>80°C / >85°C)
  * ⚠ Runaway CPU / Memory Hog processes
  * ⚠ Low Root Disk Space (<12% free)
  * ⚠ PipeWire / WirePlumber audio daemon degradation
* **Root Cause Explanation**: Translates cryptic Linux glitches into plain English.
* **Process Culprits**: Lists the exact PIDs and process names consuming resources.
* **Safe Mode Guidance**: Suggests safe, non-destructive shell remediation commands (e.g. `paccache -r`, `systemctl --user restart wireplumber`) with one-click copy to clipboard. **Never runs destructive commands automatically.**

### 🧪 5. "HYPRFETCH BENCH" Benchmark Suite
* **Real, Repeatable Performance Tests** (not cosmetic score generators):
  * **CPU**: Multi-*process* SHA-256 workload via `ProcessPoolExecutor` — avoids the GIL bottleneck of thread-based benchmarks and reports real elapsed time, worker count, and ops/sec.
  * **GPU**: A genuine timed CUDA matmul compute benchmark (warm-up + timed iterations + `cuda.synchronize()`) reported as **TFLOPS** and ops/sec — **never labeled FPS** unless an actual graphical rendering benchmark is implemented. Requires optional PyTorch + CUDA; if unavailable, the GPU component is clearly reported as **skipped** with the reason, and its score weight is redistributed rather than faked.
  * **RAM**: Real bulk memory write and copy bandwidth (GB/s) over a buffer sized relative to available system RAM (64–512MB), never large enough to cause memory pressure.
  * **Disk**: Sequential write and read bandwidth reported **separately**, using a temporary file in `~/.cache/hyprfetch/` that is always cleaned up, even on failure.
* **Normalized System Score**: Weighted composite (CPU 30% / GPU 30% / RAM 20% / Disk 20%), capped per-component at 100 and reported with a full breakdown (`score_breakdown`) in JSON/history. A component that couldn't be measured (e.g. no CUDA-capable GPU) is excluded and clearly marked, with its weight redistributed across the components that were measured — it never scores as zero or full marks.
* **Historical Comparison**: Automatically logs benchmark runs to `~/.local/share/hyprfetch/benchmarks/` to compare performance *Today* vs *Last week* vs *After driver update*. Older benchmark result files remain loadable.

> **Benchmark interpretation**: HyprFetch's benchmark is a lightweight synthetic system/compute benchmark, not a gaming or graphics FPS test. GPU results reflect FP32 matrix-multiply compute throughput on your installed CUDA backend, not in-game frame rates.

### 🎨 6. Theme Engine
Shipped with 7 cyberpunk / neon themes, with customizable QSS stylesheets and ANSI terminal palettes:
* **Nova** — Classic HyprFetch magenta & electric cyan (`#ff007f` / `#00f0ff`)
* **Nebula** — Crimson red & cosmic purple on deep titanium
* **Cyberpunk** — High-voltage neon yellow, hot pink, and cyan
* **Matrix** — Terminal hacker green & obsidian dark
* **Arctic** — Glacial blue & frost cyan
* **AMOLED** — Pitch OLED black with hyper-contrast accents
* **Minimal** — Sleek slate gray & clean ice blue

Custom user overrides can be placed at `~/.config/hyprfetch/theme.json`:
```json
{
  "accent": "#ff00ff",
  "secondary": "#00ffff",
  "background": "#090909",
  "border_radius": 14,
  "animation_speed": 1.0
}
```

---

## 🧩 Modular Architecture

```
hyprfetch/
├── core/
│   ├── system.py       # RAM, Disk, Host, Uptime, Kernel, OS, Ring Buffers
│   ├── gpu_info.py     # Shared GPU detection layer: NVIDIA (nvidia-smi) & Intel/AMD sysfs, optional CUDA/PyTorch status
│   ├── gpu.py          # Live GPU telemetry polling + history (built on gpu_info.py)
│   ├── cpu.py          # Jiffies utilization, frequency, and thermal sensors
│   ├── battery.py      # Battery state, capacity, health, and power draw
│   └── network.py      # Interface detection, I/O counters, download/upload rates
│
├── modules/
│   ├── media.py        # MPRIS playerctl metadata and playback controls
│   ├── audio.py        # WirePlumber / PipeWire volume, mute, and sink selector
│   ├── brightness.py   # Display backlight control via brightnessctl
│   ├── hyprland.py     # hyprctl workspaces, active window, and IPC actions
│   ├── wallpaper.py    # hyprpaper / swww wallpaper cycler
│   └── weather.py      # Async non-blocking weather telemetry
│
├── themes/
│   ├── theme_engine.py # Dynamic QSS stylesheet and ANSI palette generator
│   ├── nova.json
│   ├── nebula.json
│   ├── cyberpunk.json
│   ├── matrix.json
│   ├── arctic.json
│   ├── amoled.json
│   └── minimal.json
│
├── diagnose/
│   └── engine.py       # Diagnostic rule engine, anomaly radar, safe commands
│   └── selftest.py     # --self-test dependency/subsystem checks (PASS/WARN/FAIL/SKIP)
│
├── bench/
│   ├── benchmark.py    # CPU/RAM/Disk benchmarks, scoring, and history logger
│   └── gpu_bench.py    # Real CUDA compute benchmark (optional PyTorch), honest fallback
│
├── ui/
│   ├── qt_compat.py    # Cross-toolkit PyQt6 / PySide6 abstraction layer (PyQt6 preferred)
│   ├── dashboard.py    # Main cyberdeck GUI window with multi-tab layout
│   ├── graphs.py       # RealtimeGraphWidget with glowing curves & time axis
│   ├── gauges.py       # Circular arc gauges and segmented LED cyber-bars
│   └── widgets.py      # Telemetry cards, workspace pills, and media player
│
├── tui/
│   └── terminal.py     # Animated terminal dashboard with ASCII logo & sparklines
│
├── main.py             # Unified CLI/GUI entrypoint
└── hyprfetch.sh        # Universal bash launcher / fallback runner
```

---

## 📦 Requirements

| Subsystem | Arch / EndeavourOS Package | Purpose |
|---|---|---|
| **Python** | `python` (>= 3.10) | Backend core engine (stdlib only) |
| **Qt Toolkit** | `python-pyqt6` (preferred) or `python-pyside6` | Cyberdeck GUI application — optional, CLI/TUI/JSON work without it |
| **GPU telemetry** | `nvidia-utils` (`nvidia-smi`) | NVIDIA GPU detection, VRAM/temp/power telemetry |
| **GPU compute benchmark** | `python-pytorch-cuda` (PyPI: `torch`, optional) | Real CUDA compute benchmark (TFLOPS). Without it, the GPU benchmark component is skipped, not faked |
| **Audio** | `wireplumber` or `pipewire-pulse` | Volume & sink routing |
| **Brightness**| `brightnessctl` | Screen brightness control |
| **Media** | `playerctl` | MPRIS media metadata & controls |
| **Battery** | `upower` or sysfs | Battery state & health |
| **Sensors** | `lm_sensors` (optional) | CPU thermal monitoring |

Run `./hyprfetch.sh --self-test` any time to see exactly which of these are detected on your system.

---

## 🚀 Usage

### 1. Launch GUI Cyberdeck
```bash
./hyprfetch.sh
# or explicitly:
./hyprfetch.sh --gui
```

### 2. Launch Terminal TUI Companion
Features live animated scanline ASCII logo, real-time metrics, and terminal sparkline graphs:
```bash
./hyprfetch.sh --tui
```
*Keyboard Shortcuts in TUI:*
* `q` or `Ctrl+C`: Quit
* `t`: Cycle color themes in real-time
* `d`: Run instant diagnostic check
* `b`: Run hardware benchmark suite
* `Space`: Play / Pause currently playing media
* `n` / `p`: Next / Previous media track

### 3. Run Anomaly Diagnostics ("What the hell is happening?")
```bash
./hyprfetch.sh --diag
```

### 4. Run Hardware Benchmarks
```bash
./hyprfetch.sh --bench
```

### 5. Inspect GPU Details
```bash
./hyprfetch.sh --gpu-info
```
Prints detailed per-GPU telemetry (name, VRAM, utilization, temperature, power, driver, CUDA status) without running the full benchmark. Works correctly with zero, one, or multiple GPUs, and never crashes if `nvidia-smi` is missing.

### 6. Verify HyprFetch's Own Dependencies
```bash
./hyprfetch.sh --self-test
```
Checks Python version, required/optional Python modules, Qt backend, Wayland/X11, Hyprland, `nvidia-smi`, CUDA/PyTorch, audio, brightness, media, sensors, and filesystem permissions. Reports PASS/WARN/FAIL/SKIP — missing optional tools are never reported as failures.

### 7. Stream JSON Telemetry
Integrate live hardware telemetry into Waybar, Eww, or scripts:
```bash
./hyprfetch.sh --json
```

### 8. Pure Lightweight Bash Mode
```bash
./hyprfetch.sh --bash
```

### 9. Short Subcommands (optional)
If typing `./hyprfetch.sh --flag` every time is annoying, install the shorthand commands once:
```bash
./install-shortcuts.sh
```
This symlinks `hyprgui`, `hyprtui`, `hyprbench`, `hyprgpu`, `hyprself`, `hyprdiag`, and `hyprjson` into `~/.local/bin` (add it to `PATH` if the script warns it isn't there yet). After that you can just run e.g. `hyprgui` or `hyprbench` from anywhere. Uninstall with `./install-shortcuts.sh --uninstall`.

---

## ⌨️ Hyprland Integration

Add bindings to your `~/.config/hypr/hyprland.conf`:

```ini
# Open HyprFetch Cyberdeck GUI
bind = $mainMod, F1, exec, ~/Projects/"project x"/hyprfetch.sh --gui

# Open HyprFetch Terminal Monitor in a floating Kitty window
bind = $mainMod, F2, exec, kitty --title hyprfetch -e ~/Projects/"project x"/hyprfetch.sh --tui

# Windowrule to float and center the GUI
windowrulev2 = float, title:^(HyprFetch 2.0 — Cyberdeck)$
windowrulev2 = size 1100 780, title:^(HyprFetch 2.0 — Cyberdeck)$
windowrulev2 = center, title:^(HyprFetch 2.0 — Cyberdeck)$
```

---

## 📜 License
MIT
