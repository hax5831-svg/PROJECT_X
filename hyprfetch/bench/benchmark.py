"""Benchmark suite testing CPU, GPU, Disk, and RAM performance with historical comparisons.

Design notes (see README "Benchmark Interpretation" section for the full
writeup):
  - CPU uses a multiprocessing pool (ProcessPoolExecutor) so results are not
    skewed by the GIL on CPU-bound Python work.
  - RAM benchmark measures actual bulk memory write and copy bandwidth over
    a buffer sized relative to available system RAM.
  - Disk benchmark writes/reads a temp file in the user cache dir and always
    cleans it up, even on failure.
  - GPU benchmark is a genuine timed CUDA matmul workload via optional
    PyTorch, reported as TFLOPS/ops-per-second -- never labeled "FPS" unless
    a real rendering benchmark is performed. If no CUDA backend is available,
    the GPU component is clearly marked skipped rather than faked.
  - The system score is a weighted composite (CPU 30 / GPU 30 / RAM 20 /
    Disk 20) that redistributes a component's weight when that component is
    unavailable, rather than pretending it scored zero or full marks.
"""

import concurrent.futures
import hashlib
import json
import os
import platform
import time
from pathlib import Path
from typing import Optional

from hyprfetch.bench.gpu_bench import run_gpu_benchmark
from hyprfetch.core.cpu import get_cpu_model_name

# ---------------------------------------------------------------------------
# CPU benchmark
# ---------------------------------------------------------------------------

_CPU_ITERATIONS_PER_WORKER = 200_000
_MAX_CPU_WORKERS = 32


def _cpu_worker_task(payload: tuple[int, int]) -> int:
    """CPU-bound SHA-256 workload run in a separate process.

    Must stay a top-level, picklable function for ProcessPoolExecutor.
    """
    worker_id, iterations = payload
    h = hashlib.sha256()
    seed = f"worker_{worker_id}_seed_hyprfetch".encode("utf-8")
    for i in range(iterations):
        h.update(seed + str(i).encode("utf-8"))
    return len(h.digest())


# ---------------------------------------------------------------------------
# RAM benchmark
# ---------------------------------------------------------------------------

_RAM_MIN_TEST_MB = 64
_RAM_MAX_TEST_MB = 512
_RAM_PASSES = 6


def _get_total_ram_mb() -> int:
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 0


# ---------------------------------------------------------------------------
# Disk benchmark
# ---------------------------------------------------------------------------

_DISK_TEST_MB = 256


class BenchmarkEngine:
    """Executes synthetic performance benchmarks and tracks system scores."""

    def __init__(self):
        self.bench_dir = Path(os.path.expanduser("~/.local/share/hyprfetch/benchmarks"))
        self.bench_dir.mkdir(parents=True, exist_ok=True)

    def run_all(self, progress_callback=None) -> dict:
        def update_prog(step: str, pct: int):
            if progress_callback:
                progress_callback(step, pct)

        update_prog("Testing CPU (multiprocess)...", 10)
        cpu_res = self.bench_cpu()

        update_prog("Testing RAM Bandwidth...", 35)
        ram_res = self.bench_ram()

        update_prog("Testing Disk I/O Speed...", 60)
        disk_res = self.bench_disk()

        update_prog("Testing GPU Compute...", 85)
        gpu_res = self.bench_gpu()

        update_prog("Calculating System Score...", 95)
        score = self._compute_score(cpu_res, ram_res, disk_res, gpu_res)

        result = {
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "host": platform.node(),
            "cpu_model": cpu_res.get("model", "CPU"),
            "gpu_model": gpu_res.get("model", "GPU"),
            "cpu": cpu_res,
            "ram": ram_res,
            "disk": disk_res,
            "gpu": gpu_res,
            "system_score": score["total"],
            "score_breakdown": score,
        }

        self._save_result(result)
        update_prog("Complete", 100)
        return result

    # ------------------------------------------------------------------
    # CPU
    # ------------------------------------------------------------------
    def bench_cpu(self) -> dict:
        model = get_cpu_model_name()
        logical_cores = os.cpu_count() or 1
        workers = max(1, min(logical_cores, _MAX_CPU_WORKERS))

        start_time = time.perf_counter()
        used_multiprocessing = True
        try:
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
                list(
                    executor.map(
                        _cpu_worker_task,
                        [(i, _CPU_ITERATIONS_PER_WORKER) for i in range(workers)],
                    )
                )
        except Exception:
            # Some restricted/sandboxed environments disallow process spawning.
            # Fall back to sequential execution rather than crashing the benchmark;
            # the timing is still real, just not representative of multi-core scaling.
            used_multiprocessing = False
            for i in range(workers):
                _cpu_worker_task((i, _CPU_ITERATIONS_PER_WORKER))

        elapsed = max(0.001, time.perf_counter() - start_time)
        total_ops = workers * _CPU_ITERATIONS_PER_WORKER
        ops_per_sec = round(total_ops / elapsed)

        return {
            "elapsed_sec": round(elapsed, 3),
            "logical_cores": logical_cores,
            "workers": workers,
            "used_multiprocessing": used_multiprocessing,
            "ops_per_sec": ops_per_sec,
            "model": model,
            "display": f"{round(elapsed, 2)} sec ({workers} workers)",
        }

    # ------------------------------------------------------------------
    # RAM
    # ------------------------------------------------------------------
    def bench_ram(self) -> dict:
        total_ram_mb = _get_total_ram_mb()
        if total_ram_mb > 0:
            size_mb = min(_RAM_MAX_TEST_MB, max(_RAM_MIN_TEST_MB, total_ram_mb // 20))
        else:
            size_mb = _RAM_MIN_TEST_MB
        size_bytes = size_mb * 1024 * 1024

        # Write bandwidth: repeatedly overwrite a buffer (exercises memory writes).
        pattern = bytes(size_bytes)
        dest = bytearray(size_bytes)
        start = time.perf_counter()
        for _ in range(_RAM_PASSES):
            dest[:] = pattern
        write_elapsed = max(1e-6, time.perf_counter() - start)
        write_gbs = round(((size_mb * _RAM_PASSES) / 1024.0) / write_elapsed, 2)

        # Copy/read bandwidth: bulk-copy a randomized source buffer (touches
        # both read and write paths, unlike the all-zeros write-only pass).
        src = bytearray(os.urandom(size_bytes))
        start = time.perf_counter()
        for _ in range(_RAM_PASSES):
            _copy = bytearray(src)
        copy_elapsed = max(1e-6, time.perf_counter() - start)
        copy_gbs = round(((size_mb * _RAM_PASSES) / 1024.0) / copy_elapsed, 2)

        return {
            "test_size_mb": size_mb,
            "passes": _RAM_PASSES,
            "write_bandwidth_gbs": write_gbs,
            "copy_bandwidth_gbs": copy_gbs,
            "bandwidth_gbs": copy_gbs,  # backward-compatible field (used as the primary figure)
            "elapsed_sec": round(write_elapsed + copy_elapsed, 3),
            "display": f"{copy_gbs} GB/s copy / {write_gbs} GB/s write ({size_mb}MB)",
        }

    # ------------------------------------------------------------------
    # Disk
    # ------------------------------------------------------------------
    def bench_disk(self) -> dict:
        cache_dir = Path(os.path.expanduser("~/.cache/hyprfetch"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        tmp_file = cache_dir / "bench_io.tmp"

        block_size = 1024 * 1024  # 1 MiB
        blocks = _DISK_TEST_MB
        data = os.urandom(block_size)

        write_gbs = 0.0
        read_gbs = 0.0
        try:
            start_time = time.perf_counter()
            with open(tmp_file, "wb") as f:
                for _ in range(blocks):
                    f.write(data)
                f.flush()
                os.fsync(f.fileno())
            write_time = max(0.001, time.perf_counter() - start_time)
            write_gbs = round((blocks / 1024.0) / write_time, 2)

            # Drop OS page cache influence as best-effort by reading a size we
            # just wrote; this is not a cold-cache read, but is still a
            # legitimate relative I/O bandwidth signal without root privileges.
            start_time = time.perf_counter()
            with open(tmp_file, "rb") as f:
                while f.read(block_size):
                    pass
            read_time = max(0.001, time.perf_counter() - start_time)
            read_gbs = round((blocks / 1024.0) / read_time, 2)

            return {
                "test_size_mb": blocks,
                "test_path": str(cache_dir),
                "write_speed_gbs": write_gbs,
                "read_speed_gbs": read_gbs,
                "speed_gbs": max(write_gbs, read_gbs),  # backward-compatible field
                "display": f"W {write_gbs} GB/s / R {read_gbs} GB/s ({blocks}MB)",
            }
        except Exception as e:
            return {
                "test_size_mb": blocks,
                "test_path": str(cache_dir),
                "write_speed_gbs": write_gbs,
                "read_speed_gbs": read_gbs,
                "speed_gbs": 0.0,
                "error": str(e),
                "display": "N/A (disk benchmark failed)",
            }
        finally:
            # Never leave the temp file behind, success or failure.
            try:
                if tmp_file.exists():
                    tmp_file.unlink()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # GPU
    # ------------------------------------------------------------------
    def bench_gpu(self) -> dict:
        res = run_gpu_benchmark()
        model = res.get("gpu_name", "GPU")

        if res.get("status") == "ok":
            display = f"{res['tflops']} TFLOPS ({res['device_name']})"
        elif res.get("status") == "skipped":
            display = f"N/A - {res.get('reason', 'unavailable')}"
        else:
            display = f"Error - {res.get('reason', 'benchmark failed')}"

        return {
            **res,
            "model": model,
            "display": display,
        }

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    def _compute_score(self, cpu: dict, ram: dict, disk: dict, gpu: dict) -> dict:
        """Weighted composite score (CPU 30 / GPU 30 / RAM 20 / Disk 20).

        Each component is normalized against a rough reference point for
        modern consumer hardware and capped at 100 so a single outlier
        result can't dominate or break the total. A component that could
        not be measured (e.g. no CUDA GPU) is excluded and its weight is
        redistributed proportionally across the components that *were*
        measured, rather than silently scoring it as zero or full marks.
        """
        weights = {"cpu": 30.0, "gpu": 30.0, "ram": 20.0, "disk": 20.0}
        component_scores: dict[str, Optional[float]] = {}

        # CPU: reference ~1.2M SHA-256 updates/sec/worker on a modern core.
        ops_per_sec = cpu.get("ops_per_sec", 0)
        workers = max(1, cpu.get("workers", 1))
        ops_per_worker = ops_per_sec / workers
        component_scores["cpu"] = min(100.0, max(0.0, (ops_per_worker / 1_200_000.0) * 100.0))

        # RAM: reference ~12 GB/s copy bandwidth.
        ram_bw = ram.get("bandwidth_gbs", 0.0)
        component_scores["ram"] = min(100.0, max(0.0, (ram_bw / 12.0) * 100.0))

        # Disk: reference ~2.0 GB/s sequential (typical NVMe Gen3/4 floor).
        disk_bw = max(disk.get("write_speed_gbs", 0.0), disk.get("read_speed_gbs", 0.0))
        component_scores["disk"] = min(100.0, max(0.0, (disk_bw / 2.0) * 100.0))

        # GPU: reference ~8 TFLOPS FP32 (roughly an RTX 3050-class laptop GPU).
        if gpu.get("score_eligible"):
            tflops = gpu.get("tflops", 0.0)
            component_scores["gpu"] = min(100.0, max(0.0, (tflops / 8.0) * 100.0))
        else:
            component_scores["gpu"] = None

        available = {k: v for k, v in component_scores.items() if v is not None}
        skipped = [k for k, v in component_scores.items() if v is None]

        if not available:
            total = 0
        else:
            available_weight = sum(weights[k] for k in available)
            # Redistribute any skipped component's weight proportionally
            # across the components that were actually measured.
            total_weighted = sum(component_scores[k] * (weights[k] / available_weight) for k in available)
            total = int(round(total_weighted))

        return {
            "total": min(100, max(0, total)),
            "components": {k: (round(v, 1) if v is not None else None) for k, v in component_scores.items()},
            "weights": weights,
            "skipped": skipped,
        }

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------
    def _save_result(self, result: dict):
        ts = int(result["timestamp"])
        filename = self.bench_dir / f"bench_{ts}.json"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
        except Exception:
            pass

    def load_history(self) -> list[dict]:
        """Load prior benchmark runs, oldest schema versions included.

        Older result files (pre score_breakdown / pre GPU-rework) are still
        valid dicts with the fields the history table reads via `.get()`
        defaults, so no migration step is required to display them.
        """
        history = []
        try:
            for p in sorted(self.bench_dir.glob("bench_*.json"), reverse=True):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        history.append(json.load(f))
                except Exception:
                    continue  # skip a corrupt/partial history file, don't fail the whole load
        except Exception:
            pass
        return history
