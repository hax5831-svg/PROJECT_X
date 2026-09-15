"""GPU monitoring module supporting NVIDIA (nvidia-smi) and AMD/Intel sysfs fallbacks.

All actual hardware detection lives in hyprfetch.core.gpu_info -- this module
just polls it on a cadence, keeps rolling history buffers for the dashboard
graphs, and shapes the result into the dict contract the UI/TUI/JSON layers
already expect.
"""

from hyprfetch.core import gpu_info
from hyprfetch.core.system import TimeSeriesBuffer


class GPUMonitor:
    """Queries GPU metrics and stores historical trends."""

    def __init__(self):
        self.util_history = TimeSeriesBuffer(max_points=120, max_seconds=120.0)
        self.temp_history = TimeSeriesBuffer(max_points=120, max_seconds=120.0)
        self.power_history = TimeSeriesBuffer(max_points=120, max_seconds=120.0)
        self.vram_history = TimeSeriesBuffer(max_points=120, max_seconds=120.0)

        # Cache static card info (kept for backwards-compat with UI code
        # that reads `core.gpu.cached_name` directly).
        self.cached_name = None
        self._cuda = None  # lazily resolved, cached -- checking torch import is not free

    def poll(self) -> dict:
        gpus = gpu_info.list_gpus()
        primary = None
        for g in gpus:
            if g.type == "discrete":
                primary = g
                break
        if primary is None and gpus:
            primary = gpus[0]

        if primary is None:
            stats = self._unavailable()
            self._record(stats)
            return stats

        self.cached_name = primary.name

        short_name = primary.name
        for prefix in ("NVIDIA GeForce ", "NVIDIA ", "Laptop GPU", "Graphics"):
            short_name = short_name.replace(prefix, "").strip()
        if not short_name:
            short_name = primary.name

        vram_pct = (
            (primary.vram_used_mb / primary.vram_total_mb * 100.0) if primary.vram_total_mb > 0 else 0.0
        )

        if self._cuda is None:
            self._cuda = gpu_info.cuda_status()

        stats = {
            "available": True,
            "type": primary.detection_source,
            "vendor": primary.vendor,
            "gpu_type": primary.type,
            "index": primary.index,
            "name": primary.name,
            "short_name": short_name,
            "utilization": primary.utilization_percent,
            "temp": primary.temperature_c,
            "vram_used_mb": primary.vram_used_mb,
            "vram_total_mb": primary.vram_total_mb,
            "vram_free_mb": primary.vram_free_mb,
            "vram_pct": round(vram_pct, 1),
            "power_w": primary.power_draw_w,
            "power_limit_w": primary.power_limit_w,
            "fan_pct": 0.0,
            "driver": primary.driver,
            "compute_capability": primary.compute_capability,
            "clock_mhz": primary.clock_mhz,
            "cuda_available": self._cuda.cuda_available,
            "cuda_version": self._cuda.cuda_version,
            "gpu_count": len(gpus),
            "display": (
                f"{round(primary.utilization_percent)}%  {round(primary.temperature_c)}\u00b0C  "
                f"{round(primary.vram_used_mb)}/{round(primary.vram_total_mb)}MiB  "
                f"{round(primary.power_draw_w, 1)}W"
            ),
        }
        self._record(stats)
        return stats

    def _record(self, stats: dict):
        if stats["available"]:
            self.util_history.append(stats.get("utilization", 0.0))
            self.temp_history.append(stats.get("temp", 0.0))
            self.power_history.append(stats.get("power_w", 0.0))
            self.vram_history.append(stats.get("vram_pct", 0.0))

    @staticmethod
    def _unavailable() -> dict:
        return {
            "available": False,
            "type": "none",
            "vendor": "Unknown",
            "gpu_type": "none",
            "index": -1,
            "name": "No GPU detected",
            "short_name": "N/A",
            "utilization": 0.0,
            "temp": 0.0,
            "vram_used_mb": 0.0,
            "vram_total_mb": 0.0,
            "vram_free_mb": 0.0,
            "vram_pct": 0.0,
            "power_w": 0.0,
            "power_limit_w": 0.0,
            "fan_pct": 0.0,
            "driver": None,
            "compute_capability": None,
            "clock_mhz": 0.0,
            "cuda_available": False,
            "cuda_version": None,
            "gpu_count": 0,
            "display": "N/A",
        }
