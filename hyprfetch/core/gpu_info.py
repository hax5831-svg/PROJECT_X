"""Shared GPU detection and CUDA/PyTorch capability layer.

This module is the single source of truth for GPU hardware detection in
HyprFetch. It is imported by:
  - hyprfetch.core.gpu   (live telemetry / dashboard polling)
  - hyprfetch.bench.gpu_bench (compute benchmark)
  - main.py --gpu-info   (standalone CLI inspection)

No component of HyprFetch should call `nvidia-smi` or read GPU sysfs nodes
directly outside of this module — this keeps hardware detection logic in
one place instead of duplicated per-interface.

Everything here degrades gracefully: if `nvidia-smi` is missing, if PyTorch
is not installed, or if no GPU is present at all, functions return
structured "unavailable" results instead of raising or fabricating values.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from typing import Optional

from hyprfetch.core.shell import run_query, run_query_raw

_NVIDIA_SMI_TIMEOUT = 2.5

# Fields requested from `nvidia-smi --query-gpu=...`, in order. Keep this
# list and _parse_nvidia_line() in sync.
_NVIDIA_QUERY_FIELDS = [
    "index",
    "name",
    "memory.total",
    "memory.used",
    "memory.free",
    "utilization.gpu",
    "temperature.gpu",
    "power.draw",
    "power.limit",
    "driver_version",
    "compute_cap",
    "clocks.current.graphics",
]


@dataclass
class GPUInfo:
    """Normalized information about a single GPU."""

    index: int
    name: str
    vendor: str  # "NVIDIA", "Intel", "AMD", "Unknown"
    type: str  # "discrete", "integrated", "unknown"
    available: bool = True
    vram_total_mb: float = 0.0
    vram_used_mb: float = 0.0
    vram_free_mb: float = 0.0
    utilization_percent: float = 0.0
    temperature_c: float = 0.0
    power_draw_w: float = 0.0
    power_limit_w: float = 0.0
    driver: Optional[str] = None
    compute_capability: Optional[str] = None
    clock_mhz: float = 0.0
    detection_source: str = "none"  # "nvidia-smi", "sysfs", "none"

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "name": self.name,
            "vendor": self.vendor,
            "type": self.type,
            "available": self.available,
            "vram_total_mb": self.vram_total_mb,
            "vram_used_mb": self.vram_used_mb,
            "vram_free_mb": self.vram_free_mb,
            "utilization_percent": self.utilization_percent,
            "temperature_c": self.temperature_c,
            "power_draw_w": self.power_draw_w,
            "power_limit_w": self.power_limit_w,
            "driver": self.driver,
            "compute_capability": self.compute_capability,
            "clock_mhz": self.clock_mhz,
            "detection_source": self.detection_source,
        }


def _to_float(val: str, default: float = 0.0) -> float:
    try:
        val = val.strip()
        if val in ("", "[N/A]", "N/A"):
            return default
        clean = "".join(c for c in val if (c.isdigit() or c in ".-"))
        return float(clean) if clean else default
    except Exception:
        return default


def has_nvidia_smi() -> bool:
    return shutil.which("nvidia-smi") is not None


def _run_nvidia_smi(args: list[str], timeout: float = _NVIDIA_SMI_TIMEOUT) -> Optional[str]:
    return run_query(["nvidia-smi", *args], timeout=timeout)


def _parse_nvidia_line(line: str) -> Optional[GPUInfo]:
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < len(_NVIDIA_QUERY_FIELDS):
        # Pad missing trailing fields (older driver/nvidia-smi versions may
        # not support every query key) rather than discarding the GPU.
        parts += [""] * (len(_NVIDIA_QUERY_FIELDS) - len(parts))

    try:
        index = int(_to_float(parts[0], 0))
    except Exception:
        index = 0

    name = parts[1] or "NVIDIA GPU"
    driver = parts[9] or None
    compute_cap = parts[10] or None

    return GPUInfo(
        index=index,
        name=name,
        vendor="NVIDIA",
        type="discrete",
        available=True,
        vram_total_mb=_to_float(parts[2]),
        vram_used_mb=_to_float(parts[3]),
        vram_free_mb=_to_float(parts[4]),
        utilization_percent=_to_float(parts[5]),
        temperature_c=_to_float(parts[6]),
        power_draw_w=_to_float(parts[7]),
        power_limit_w=_to_float(parts[8]),
        driver=driver,
        compute_capability=compute_cap,
        clock_mhz=_to_float(parts[11]),
        detection_source="nvidia-smi",
    )


def detect_nvidia_gpus() -> list[GPUInfo]:
    """Enumerate all NVIDIA GPUs via nvidia-smi. Returns [] if unavailable."""
    if not has_nvidia_smi():
        return []

    query = ",".join(_NVIDIA_QUERY_FIELDS)
    out = _run_nvidia_smi([f"--query-gpu={query}", "--format=csv,noheader,nounits"])
    if not out:
        return []

    gpus = []
    for line in out.strip().splitlines():
        if not line.strip():
            continue
        gpu = _parse_nvidia_line(line)
        if gpu:
            gpus.append(gpu)
    return gpus


def nvidia_cuda_driver_version() -> Optional[str]:
    """Parse the max CUDA toolkit version supported by the installed driver
    from the banner of plain `nvidia-smi` output (not exposed via --query-gpu).
    This is the driver's CUDA capability ceiling, not necessarily the CUDA
    version PyTorch was built against.
    """
    if not has_nvidia_smi():
        return None
    out = _run_nvidia_smi([])
    if not out:
        return None
    m = re.search(r"CUDA Version:\s*([\d.]+)", out)
    return m.group(1) if m else None


_SYSFS_VENDOR_MAP = {
    "0x8086": ("Intel", "integrated"),
    "0x1002": ("AMD", "unknown"),  # AMD covers both APUs and discrete cards
    "0x10de": ("NVIDIA", "discrete"),  # already covered via nvidia-smi normally
}


def detect_sysfs_gpus(exclude_vendor: str = "NVIDIA") -> list[GPUInfo]:
    """Enumerate non-NVIDIA GPUs (typically Intel iGPU, sometimes AMD) via
    DRM sysfs. Used as a fallback / supplement when nvidia-smi is absent or
    to surface the iGPU alongside a detected NVIDIA dGPU.
    """
    import os

    gpus = []
    drm_root = "/sys/class/drm"
    if not os.path.isdir(drm_root):
        return gpus

    seen_devices = set()
    idx = 0
    for card in sorted(os.listdir(drm_root)):
        if not re.match(r"^card\d+$", card):
            continue
        base = os.path.join(drm_root, card, "device")
        if not os.path.isdir(base) or base in seen_devices:
            continue
        seen_devices.add(base)

        vendor_id = None
        vendor_file = os.path.join(base, "vendor")
        if os.path.exists(vendor_file):
            try:
                with open(vendor_file, "r") as f:
                    vendor_id = f.read().strip().lower()
            except Exception:
                pass

        vendor_name, gpu_type = _SYSFS_VENDOR_MAP.get(vendor_id, ("Unknown", "unknown"))
        if vendor_name == exclude_vendor:
            continue
        if vendor_id is None:
            continue

        util = 0.0
        busy_file = os.path.join(base, "gpu_busy_percent")
        if os.path.exists(busy_file):
            try:
                with open(busy_file, "r") as f:
                    util = float(f.read().strip())
            except Exception:
                pass

        temp = 0.0
        hwmon_dir = os.path.join(base, "hwmon")
        if os.path.isdir(hwmon_dir):
            for sub in os.listdir(hwmon_dir):
                t_file = os.path.join(hwmon_dir, sub, "temp1_input")
                if os.path.exists(t_file):
                    try:
                        with open(t_file, "r") as f:
                            temp = float(f.read().strip()) / 1000.0
                        break
                    except Exception:
                        pass

        name = f"{vendor_name} Graphics"
        # Best-effort friendly name via lspci, if available. Never fatal.
        if shutil.which("lspci"):
            try:
                res = run_query_raw(["lspci", "-mm"], timeout=1.5)
                if res is not None and res.returncode == 0:
                    for pline in res.stdout.splitlines():
                        if "VGA" in pline or "3D controller" in pline:
                            fields = [f.strip('"') for f in re.findall(r'"[^"]*"|\S+', pline)]
                            if len(fields) >= 4:
                                name = f"{vendor_name} {fields[-1]}"
                            break
            except Exception:
                pass

        gpus.append(
            GPUInfo(
                index=idx,
                name=name,
                vendor=vendor_name,
                type=gpu_type,
                available=True,
                utilization_percent=util,
                temperature_c=temp,
                detection_source="sysfs",
            )
        )
        idx += 1

    return gpus


def list_gpus() -> list[GPUInfo]:
    """Return every detected GPU: NVIDIA discrete card(s) first (if any),
    then any Intel/AMD integrated or secondary GPUs found via sysfs.
    Never fabricates a GPU that isn't actually present.
    """
    gpus = detect_nvidia_gpus()
    next_idx = len(gpus)
    for extra in detect_sysfs_gpus(exclude_vendor="NVIDIA"):
        extra.index = next_idx
        gpus.append(extra)
        next_idx += 1
    return gpus


def primary_gpu() -> Optional[GPUInfo]:
    """Preferred GPU for telemetry display and benchmarking: the first
    discrete GPU if one exists, else the first GPU found, else None.
    """
    gpus = list_gpus()
    if not gpus:
        return None
    for g in gpus:
        if g.type == "discrete":
            return g
    return gpus[0]


@dataclass
class CudaStatus:
    torch_installed: bool = False
    torch_version: Optional[str] = None
    cuda_available: bool = False
    cuda_version: Optional[str] = None  # CUDA version torch was built against
    device_name: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "torch_installed": self.torch_installed,
            "torch_version": self.torch_version,
            "cuda_available": self.cuda_available,
            "cuda_version": self.cuda_version,
            "device_name": self.device_name,
            "error": self.error,
        }


def cuda_status() -> CudaStatus:
    """Check optional PyTorch + CUDA acceleration availability.

    PyTorch is never a hard dependency of HyprFetch — this import is fully
    optional and failure here must never break any other feature.
    """
    try:
        import importlib.util

        if importlib.util.find_spec("torch") is None:
            return CudaStatus(torch_installed=False)
    except Exception as e:
        return CudaStatus(torch_installed=False, error=str(e))

    try:
        import torch  # noqa: WPS433 (intentional lazy/optional import)

        available = bool(torch.cuda.is_available())
        device_name = None
        if available:
            try:
                device_name = torch.cuda.get_device_name(0)
            except Exception:
                device_name = None
        return CudaStatus(
            torch_installed=True,
            torch_version=getattr(torch, "__version__", None),
            cuda_available=available,
            cuda_version=getattr(torch.version, "cuda", None),
            device_name=device_name,
        )
    except Exception as e:
        return CudaStatus(torch_installed=True, cuda_available=False, error=str(e))
