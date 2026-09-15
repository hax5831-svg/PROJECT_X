"""Automatic diagnostic engine: detects anomalies and explains system issues safely."""

import os
import shutil
from hyprfetch.core.shell import run_query, run_query_raw


class DiagnosticReport:
    """Represents a diagnostic finding with plain-English explanation and safe commands."""

    def __init__(
        self,
        severity: str,  # "INFO", "WARNING", "CRITICAL"
        title: str,
        summary: str,
        details: str,
        culprits: list[dict] = None,
        suggested_commands: list[str] = None,
    ):
        self.severity = severity
        self.title = title
        self.summary = summary
        self.details = details
        self.culprits = culprits or []
        self.suggested_commands = suggested_commands or []

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "title": self.title,
            "summary": self.summary,
            "details": self.details,
            "culprits": self.culprits,
            "suggested_commands": self.suggested_commands,
        }


class DiagnosticEngine:
    """Analyzes hardware states and running processes to explain system degradation."""

    def __init__(self):
        pass

    def run_diagnostics(self, core_snapshot: dict) -> list[DiagnosticReport]:
        reports = []

        # 1. GPU VRAM & Temperature Analysis
        gpu = core_snapshot.get("gpu", {})
        if gpu.get("available"):
            vram_pct = gpu.get("vram_pct", 0.0)
            vram_used = gpu.get("vram_used_mb", 0.0)
            vram_total = gpu.get("vram_total_mb", 0.0)
            temp = gpu.get("temp", 0.0)

            if vram_pct >= 85.0:
                culprits = self._get_gpu_processes()
                reports.append(
                    DiagnosticReport(
                        severity="CRITICAL" if vram_pct >= 95.0 else "WARNING",
                        title="GPU VRAM ALMOST FULL",
                        summary=f"{round(vram_used / 1024, 1)} / {round(vram_total / 1024, 1)} GB ({round(vram_pct)}%) allocated",
                        details=(
                            "GPU video memory is approaching exhaustion. This commonly leads to "
                            "Wayland session stutters, browser crashes, or Out-Of-Memory CUDA kernel aborts."
                        ),
                        culprits=culprits,
                        suggested_commands=[
                            "nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=table",
                            "# To close a heavy process: kill -TERM <PID>",
                        ],
                    )
                )

            if temp >= 80.0:
                reports.append(
                    DiagnosticReport(
                        severity="CRITICAL" if temp >= 87.0 else "WARNING",
                        title="GPU TEMPERATURE HIGH",
                        summary=f"NVIDIA GPU operating at {round(temp)}°C",
                        details=(
                            "Thermal throttling begins near 83-87°C on NVIDIA mobile chips, reducing clocks. "
                            "Verify laptop vents are not obstructed and fans are spinning."
                        ),
                        suggested_commands=[
                            "sensors",
                            "nvidia-smi -q -d TEMPERATURE,FAN",
                        ],
                    )
                )

        # 2. CPU Temperature Analysis
        cpu = core_snapshot.get("cpu", {})
        cpu_temp = cpu.get("temp", 0.0)
        cpu_util = cpu.get("utilization", 0.0)

        if cpu_temp >= 85.0:
            reports.append(
                DiagnosticReport(
                    severity="CRITICAL" if cpu_temp >= 92.0 else "WARNING",
                    title="CPU TEMPERATURE HIGH",
                    summary=f"CPU thermal package at {round(cpu_temp)}°C",
                    details=(
                        "High sustained temperatures cause aggressive power throttling. "
                        "Check if high-priority background compilations or rogue render loops are executing."
                    ),
                    culprits=self._get_top_cpu_processes(limit=3),
                    suggested_commands=[
                        "sensors",
                        "ps -eo pid,comm,%cpu --sort=-%cpu | head -n 6",
                    ],
                )
            )

        if cpu_util >= 85.0:
            top_cpu = self._get_top_cpu_processes(limit=5)
            reports.append(
                DiagnosticReport(
                    severity="WARNING",
                    title="CPU UTILIZATION HIGH",
                    summary=f"System aggregate load at {round(cpu_util)}%",
                    details="One or more threads are pegging your CPU cores. Review the top consumers below.",
                    culprits=top_cpu,
                    suggested_commands=[
                        "top -b -n 1 | head -n 20",
                        "# To pause or kill runaway process: kill -STOP <PID> or kill -TERM <PID>",
                    ],
                )
            )

        # 3. RAM Memory Pressure Analysis
        system = core_snapshot.get("system", {})
        ram = system.get("ram", {})
        ram_pct = ram.get("percent", 0.0)

        if ram_pct >= 85.0:
            top_mem = self._get_top_mem_processes(limit=5)
            reports.append(
                DiagnosticReport(
                    severity="CRITICAL" if ram_pct >= 94.0 else "WARNING",
                    title="SYSTEM RAM EXHAUSTION",
                    summary=f"{ram.get('used_gb', 0)} / {ram.get('total_gb', 0)} GB ({round(ram_pct)}%) consumed",
                    details=(
                        "Heavy physical memory usage can cause Linux to invoke the OOM (Out-of-Memory) killer "
                        "or trigger heavy disk swap thrashing, making Hyprland freeze."
                    ),
                    culprits=top_mem,
                    suggested_commands=[
                        "ps -eo pid,comm,%mem,rss --sort=-rss | head -n 6",
                        "# Safe pagecache purge (root): sudo sysctl vm.drop_caches=3",
                    ],
                )
            )

        # 4. Root Disk Space Analysis
        disk = system.get("disk", {})
        disk_pct = disk.get("percent", 0.0)
        free_gb = round(disk.get("free_bytes", 0) / (1024**3), 1)

        if disk_pct >= 88.0:
            reports.append(
                DiagnosticReport(
                    severity="CRITICAL" if disk_pct >= 95.0 else "WARNING",
                    title="LOW ROOT DISK SPACE",
                    summary=f"Only {free_gb} GB remaining ({round(100 - disk_pct)}% free) on /",
                    details=(
                        "On Arch / EndeavourOS, pacman package cache (/var/cache/pacman/pkg) and systemd logs "
                        "commonly consume gigabytes of storage over time."
                    ),
                    suggested_commands=[
                        "# Clean pacman cached packages (safe):",
                        "sudo paccache -r || sudo pacman -Sc",
                        "# Vacuum systemd logs older than 7 days:",
                        "sudo journalctl --vacuum-time=7d",
                        "# Clear user thumbnail cache:",
                        "rm -rf ~/.cache/thumbnails/*",
                    ],
                )
            )

        # 5. Audio / PipeWire Daemon Health
        audio_ok, audio_msg = self._check_audio_subsystem()
        if not audio_ok:
            reports.append(
                DiagnosticReport(
                    severity="WARNING",
                    title="AUDIO DAEMON DEGRADED",
                    summary=audio_msg,
                    details="PipeWire or WirePlumber may have crashed or lost session D-Bus connection.",
                    suggested_commands=[
                        "systemctl --user restart wireplumber pipewire pipewire-pulse",
                        "wpctl status",
                    ],
                )
            )

        # 6. Battery Health Warning
        bat = core_snapshot.get("battery", {})
        if bat.get("present"):
            health = bat.get("health", 100.0)
            pct = bat.get("percent", 100.0)
            state = bat.get("state", "").lower()
            if health < 60.0:
                reports.append(
                    DiagnosticReport(
                        severity="INFO",
                        title="BATTERY DEGRADATION NOTICE",
                        summary=f"Battery maximum capacity is at {round(health)}% of design",
                        details="The lithium battery cells have degraded from charge cycles and age.",
                        suggested_commands=["upower -i /org/freedesktop/UPower/devices/battery_BAT0"],
                    )
                )
            if pct <= 15.0 and "discharging" in state:
                reports.append(
                    DiagnosticReport(
                        severity="CRITICAL",
                        title="BATTERY CRITICALLY LOW",
                        summary=f"Battery level at {round(pct)}% ({state})",
                        details="System will power off soon. Connect AC adapter.",
                        suggested_commands=["brightnessctl set 30%"],
                    )
                )

        # If all checks pass
        if not reports:
            reports.append(
                DiagnosticReport(
                    severity="INFO",
                    title="ALL SYSTEMS NOMINAL",
                    summary="All monitored telemetry within optimal thresholds",
                    details=(
                        "CPU, GPU, RAM, Disk, and Audio daemons are operating normally with healthy margins. "
                        "No thermal throttling, memory leaks, or space bottlenecks detected."
                    ),
                    suggested_commands=[],
                )
            )

        return reports

    def _get_gpu_processes(self) -> list[dict]:
        culprits = []
        if not shutil.which("nvidia-smi"):
            return culprits

        cmd = ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader,nounits"]
        out = run_query(cmd, timeout=1.5)
        if not out:
            return culprits
        for line in out.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                culprits.append({
                    "pid": parts[0],
                    "name": os.path.basename(parts[1]),
                    "usage": f"{parts[2]} MiB VRAM",
                })
        return culprits

    def _get_top_cpu_processes(self, limit: int = 5) -> list[dict]:
        culprits = []
        out = run_query(["ps", "-eo", "pid,comm,%cpu", "--sort=-%cpu"], timeout=1.5)
        if not out:
            return culprits
        for line in out.splitlines()[1 : limit + 1]:
            parts = line.split(None, 2)
            if len(parts) >= 3:
                culprits.append({
                    "pid": parts[0],
                    "name": parts[1],
                    "usage": f"{parts[2]}% CPU",
                })
        return culprits

    def _get_top_mem_processes(self, limit: int = 5) -> list[dict]:
        culprits = []
        out = run_query(["ps", "-eo", "pid,comm,%mem,rss", "--sort=-rss"], timeout=1.5)
        if not out:
            return culprits
        for line in out.splitlines()[1 : limit + 1]:
            parts = line.split(None, 3)
            if len(parts) >= 4:
                rss_mb = round(int(parts[3]) / 1024, 1)
                culprits.append({
                    "pid": parts[0],
                    "name": parts[1],
                    "usage": f"{rss_mb} MB ({parts[2]}%)",
                })
        return culprits

    def _check_audio_subsystem(self) -> tuple[bool, str]:
        if shutil.which("systemctl"):
            res = run_query_raw(["systemctl", "--user", "is-active", "wireplumber"], timeout=1.0)
            if res is not None and res.returncode != 0:
                return False, "WirePlumber user service is inactive or failed"
        return True, "OK"
