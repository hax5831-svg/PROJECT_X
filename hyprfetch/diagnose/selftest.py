"""Self-test: verifies HyprFetch's own components and optional subsystems.

Every check reports one of PASS / WARN / FAIL / SKIP. A missing *optional*
dependency is reported as SKIP or WARN, never FAIL -- only a genuinely
required, broken piece of HyprFetch itself should FAIL.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    status: str  # "PASS" | "WARN" | "FAIL" | "SKIP"
    detail: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "status": self.status, "detail": self.detail}


def _module_available(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:
        return False


def _binary_available(binary: str) -> bool:
    return shutil.which(binary) is not None


def run_self_test() -> list[CheckResult]:
    checks: list[CheckResult] = []

    # --- Python runtime ---------------------------------------------------
    py_ver = sys.version_info
    if py_ver >= (3, 10):
        checks.append(CheckResult("Python version", "PASS", f"{platform_version()}"))
    else:
        checks.append(CheckResult("Python version", "FAIL", f"{platform_version()} (need >= 3.10)"))

    # --- Required modules (stdlib-only core should always pass) -----------
    for mod in ("json", "subprocess", "concurrent.futures", "hashlib", "argparse"):
        checks.append(
            CheckResult(f"Required module: {mod}", "PASS" if _module_available(mod) else "FAIL")
        )

    # --- Optional Qt backend ------------------------------------------------
    has_pyqt6 = _module_available("PyQt6")
    has_pyside6 = _module_available("PySide6")
    if has_pyqt6:
        checks.append(CheckResult("Qt backend", "PASS", "PyQt6 available (preferred)"))
    elif has_pyside6:
        checks.append(CheckResult("Qt backend", "PASS", "PySide6 available (fallback)"))
    else:
        checks.append(
            CheckResult("Qt backend", "WARN", "Neither PyQt6 nor PySide6 installed -- GUI mode unavailable, CLI/TUI/JSON still work")
        )

    # --- Display server -----------------------------------------------------
    if os.getenv("WAYLAND_DISPLAY"):
        checks.append(CheckResult("Display server", "PASS", f"Wayland ({os.getenv('WAYLAND_DISPLAY')})"))
    elif os.getenv("DISPLAY"):
        checks.append(CheckResult("Display server", "PASS", f"X11 ({os.getenv('DISPLAY')})"))
    else:
        checks.append(CheckResult("Display server", "WARN", "No WAYLAND_DISPLAY or DISPLAY set -- headless/TTY session"))

    # --- Hyprland -------------------------------------------------------
    if os.getenv("HYPRLAND_INSTANCE_SIGNATURE"):
        checks.append(CheckResult("Hyprland", "PASS", "Running under Hyprland"))
    elif _binary_available("hyprctl"):
        checks.append(CheckResult("Hyprland", "WARN", "hyprctl found but not currently running under Hyprland"))
    else:
        checks.append(CheckResult("Hyprland", "SKIP", "hyprctl not found -- Hyprland-specific features unavailable"))

    # --- GPU / CUDA ----------------------------------------------------
    from hyprfetch.core import gpu_info

    if gpu_info.has_nvidia_smi():
        gpus = gpu_info.detect_nvidia_gpus()
        if gpus:
            checks.append(CheckResult("nvidia-smi", "PASS", f"{len(gpus)} NVIDIA GPU(s) detected"))
        else:
            checks.append(CheckResult("nvidia-smi", "WARN", "nvidia-smi present but returned no GPUs"))
    else:
        checks.append(CheckResult("nvidia-smi", "SKIP", "Not installed -- NVIDIA telemetry unavailable"))

    cuda = gpu_info.cuda_status()
    if not cuda.torch_installed:
        checks.append(CheckResult("PyTorch / CUDA benchmark", "SKIP", "PyTorch not installed -- GPU compute benchmark unavailable"))
    elif cuda.cuda_available:
        checks.append(CheckResult("PyTorch / CUDA benchmark", "PASS", f"torch {cuda.torch_version}, CUDA {cuda.cuda_version}"))
    else:
        checks.append(CheckResult("PyTorch / CUDA benchmark", "WARN", "PyTorch installed but CUDA unavailable to it"))

    # --- Audio -----------------------------------------------------------
    if _binary_available("wpctl") or _binary_available("pactl"):
        checks.append(CheckResult("PipeWire/PulseAudio", "PASS"))
    else:
        checks.append(CheckResult("PipeWire/PulseAudio", "SKIP", "wpctl/pactl not found -- audio telemetry unavailable"))

    # --- Misc optional CLI tools -----------------------------------------
    optional_tools = {
        "brightnessctl": "brightness telemetry/control",
        "playerctl": "media controls",
        "upower": "battery telemetry (falls back to sysfs)",
        "sensors": "CPU/GPU thermal sensors (lm-sensors)",
    }
    for tool, feature in optional_tools.items():
        if _binary_available(tool):
            checks.append(CheckResult(tool, "PASS"))
        else:
            checks.append(CheckResult(tool, "SKIP", f"Not found -- {feature} unavailable"))

    # --- Filesystem permissions -------------------------------------------
    checks.append(_check_dir_writable("Benchmark directory", Path(os.path.expanduser("~/.local/share/hyprfetch/benchmarks"))))
    checks.append(_check_dir_writable("Cache directory", Path(os.path.expanduser("~/.cache/hyprfetch"))))

    return checks


def _check_dir_writable(label: str, path: Path) -> CheckResult:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".hyprfetch_selftest_probe"
        probe.write_text("ok")
        probe.unlink()
        return CheckResult(label, "PASS", str(path))
    except Exception as e:
        return CheckResult(label, "FAIL", f"{path}: {e}")


def platform_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
