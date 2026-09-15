"""Real GPU compute benchmark.

PyTorch + CUDA is an OPTIONAL acceleration dependency, never a hard
requirement of HyprFetch. This module never reports a fabricated "FPS"
value -- results are either a genuine timed compute measurement (TFLOPS,
ops/sec) or an explicit "unavailable" / "skipped" status explaining why.
"""

from __future__ import annotations

import time
from typing import Optional

from hyprfetch.core import gpu_info

# Matrix sizes chosen to give a meaningful, repeatable FP32 matmul workload
# without risking VRAM exhaustion on a 4-6GB laptop GPU. A 4096^3 FP32 matmul
# needs ~200MB for the three matrices -- trivial next to a 6GB card, and the
# workload is a handful of GFLOPs per iteration so timing stays sub-second
# per iteration even on modest GPUs.
_MATRIX_DIM = 4096
_WARMUP_ITERS = 3
_TIMED_ITERS = 10
_BENCH_TIMEOUT_SEC = 20.0


def _run_torch_cuda_benchmark() -> dict:
    """Attempt the real CUDA compute benchmark. Raises on any failure so the
    caller can fall back cleanly -- never partially reports a bogus number.
    """
    import torch  # optional dependency; only imported when available

    device = torch.device("cuda:0")
    n = _MATRIX_DIM

    a = torch.randn((n, n), device=device, dtype=torch.float32)
    b = torch.randn((n, n), device=device, dtype=torch.float32)

    try:
        # Warm-up: let CUDA kernels JIT/cache and clocks ramp up before timing.
        for _ in range(_WARMUP_ITERS):
            c = torch.matmul(a, b)
        torch.cuda.synchronize()

        elapsed_iters = 0
        start = time.perf_counter()
        for _ in range(_TIMED_ITERS):
            c = torch.matmul(a, b)
            elapsed_iters += 1
            if time.perf_counter() - start > _BENCH_TIMEOUT_SEC:
                break
        torch.cuda.synchronize()
        elapsed = max(1e-6, time.perf_counter() - start)

        # FLOPs for an NxN @ NxN matmul: 2*N^3 (multiply+add per element pair)
        flops_per_iter = 2 * (n ** 3)
        total_flops = flops_per_iter * elapsed_iters
        tflops = (total_flops / elapsed) / 1e12
        ops_per_sec = elapsed_iters / elapsed

        return {
            "backend": "torch-cuda",
            "device_name": torch.cuda.get_device_name(0),
            "matrix_dim": n,
            "iterations": elapsed_iters,
            "elapsed_sec": round(elapsed, 4),
            "tflops": round(tflops, 3),
            "ops_per_sec": round(ops_per_sec, 3),
        }
    finally:
        # Always release GPU memory, even if the benchmark raised partway
        # through -- never leave large tensors resident after a failure.
        del a, b
        try:
            del c
        except NameError:
            pass
        torch.cuda.empty_cache()


def run_gpu_benchmark() -> dict:
    """Run the best available GPU benchmark for this system.

    Returns a dict always containing: status ("ok" | "skipped" | "error"),
    a `reason` when not "ok", plus telemetry about the detected GPU.
    """
    primary = gpu_info.primary_gpu()
    cuda = gpu_info.cuda_status()

    base = {
        "gpu_name": primary.name if primary else "No GPU detected",
        "gpu_available": primary is not None,
        "cuda_available": cuda.cuda_available,
        "cuda_version": cuda.cuda_version,
    }

    if primary is None:
        return {
            **base,
            "status": "skipped",
            "reason": "No GPU detected on this system.",
            "score_eligible": False,
        }

    if primary.vendor != "NVIDIA":
        return {
            **base,
            "status": "skipped",
            "reason": f"No CUDA-capable GPU detected (found {primary.vendor} {primary.type}).",
            "score_eligible": False,
        }

    if not cuda.torch_installed:
        return {
            **base,
            "status": "skipped",
            "reason": "PyTorch is not installed. Install PyTorch with CUDA support for a real compute benchmark.",
            "score_eligible": False,
        }

    if not cuda.cuda_available:
        return {
            **base,
            "status": "skipped",
            "reason": cuda.error or "PyTorch is installed but CUDA is not available to it.",
            "score_eligible": False,
        }

    try:
        result = _run_torch_cuda_benchmark()
        return {
            **base,
            "status": "ok",
            "score_eligible": True,
            **result,
        }
    except Exception as e:
        return {
            **base,
            "status": "error",
            "reason": f"GPU benchmark failed: {e}",
            "score_eligible": False,
        }
