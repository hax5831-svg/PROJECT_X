"""Main Cyberdeck GUI application dashboard for HyprFetch 2.0."""

import sys
import time
from hyprfetch.bench.benchmark import BenchmarkEngine
from hyprfetch.core import HyprFetchCore
from hyprfetch.diagnose.engine import DiagnosticEngine
from hyprfetch.modules import AudioManager, BrightnessManager, HyprlandManager, MediaManager, WallpaperManager, WeatherManager
from hyprfetch.themes.theme_engine import ThemeEngine
from hyprfetch.ui.graphs import RealtimeGraphWidget
from hyprfetch.ui.qt_compat import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)
from hyprfetch.ui.widgets import (
    HyprlandWorkspaceWidget,
    MediaControlWidget,
    MetricCard,
    SystemControlWidget,
)


class HyprFetchDashboard(QMainWindow):
    """HyprFetch 2.0 main cyberdeck desktop window."""

    def __init__(self, core: HyprFetchCore = None, theme_engine: ThemeEngine = None):
        super().__init__()
        self.core = core or HyprFetchCore()
        self.theme_engine = theme_engine or ThemeEngine()
        self.audio_mgr = AudioManager()
        self.brightness_mgr = BrightnessManager()
        self.wallpaper_mgr = WallpaperManager()
        self.hyprland_mgr = HyprlandManager()
        self.media_mgr = MediaManager()
        self.weather_mgr = WeatherManager()
        self.diag_engine = DiagnosticEngine()
        self.bench_engine = BenchmarkEngine()

        self.setWindowTitle("HyprFetch 2.0 — Cyberdeck")
        self.resize(1100, 780)
        self.setMinimumSize(880, 620)

        self._init_ui()
        self._apply_theme()

        # Telemetry refresh timer (1 second)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(1000)

        # Initial tick
        self._on_tick()

    def _init_ui(self):
        self.central_widget = QWidget()
        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)

        self.root_layout = QVBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(18, 14, 18, 14)
        self.root_layout.setSpacing(12)

        # 1. Top Cyberpunk Header
        self._build_header()

        # 2. Nav Bar
        self._build_navbar()

        # 3. Stacked View Area
        self.stack = QStackedWidget()
        self.root_layout.addWidget(self.stack, stretch=1)

        # Build pages
        self._build_dashboard_page()
        self._build_controls_page()
        self._build_diagnostics_page()
        self._build_benchmark_page()

        self.stack.setCurrentIndex(0)

    def _build_header(self):
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(14)

        # Host badge
        sys_info = self.core.system.cached_info
        host_title = f"{sys_info['user'].upper()}@{sys_info['host'].upper()}"
        self.host_lbl = QLabel(host_title)
        self.host_lbl.setStyleSheet("font-size: 16px; font-weight: 900; letter-spacing: 1px;")

        self.version_badge = QLabel("HYPRFETCH v2.0")
        self.version_badge.setStyleSheet(
            "background-color: #00f0ff22; color: #00f0ff; border: 1px solid #00f0ff55; "
            "padding: 3px 8px; border-radius: 6px; font-size: 10px; font-weight: 800;"
        )

        header.addWidget(self.host_lbl)
        header.addWidget(self.version_badge)
        header.addStretch()

        # Weather readout
        self.weather_lbl = QLabel("⛅ Measuring...")
        self.weather_lbl.setObjectName("SubText")
        header.addWidget(self.weather_lbl)

        # Uptime readout
        self.uptime_lbl = QLabel("Up: 0m")
        self.uptime_lbl.setObjectName("SubText")
        header.addWidget(self.uptime_lbl)

        # Theme Selector Dropdown
        theme_lbl = QLabel("THEME:")
        theme_lbl.setObjectName("Title")
        header.addWidget(theme_lbl)

        self.theme_combo = QComboBox()
        for name in sorted(self.theme_engine.available_themes.keys()):
            display_name = self.theme_engine.available_themes[name].name
            self.theme_combo.addItem(display_name, name)

        cur_idx = self.theme_combo.findData(self.theme_engine.active_theme.name.lower())
        if cur_idx >= 0:
            self.theme_combo.setCurrentIndex(cur_idx)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        header.addWidget(self.theme_combo)

        self.root_layout.addLayout(header)

    def _build_navbar(self):
        nav = QHBoxLayout()
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(8)

        self.nav_btns = []
        labels = [
            ("📊 DASHBOARD", 0),
            ("🎛️ CONTROLS", 1),
            ("🧠 DIAGNOSTICS", 2),
            ("🧪 BENCHMARK", 3),
        ]

        for text, idx in labels:
            btn = QPushButton(text)
            btn.setObjectName("NavBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=idx: self._switch_tab(i))
            nav.addWidget(btn)
            self.nav_btns.append(btn)

        nav.addStretch()
        self.nav_btns[0].setProperty("active", "true")
        self.root_layout.addLayout(nav)

    def _switch_tab(self, idx: int):
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate(self.nav_btns):
            btn.setProperty("active", "true" if i == idx else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ---------------- PAGE 1: DASHBOARD ----------------
    def _build_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 1. Top Metric Cards Row (GPU, CPU, RAM, Network)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.gpu_card = MetricCard("GPU", "Detecting...")
        self.cpu_card = MetricCard("CPU", "Detecting...")
        self.ram_card = MetricCard("RAM", "0 / 0 GB")
        self.net_card = MetricCard("NETWORK", "Measuring...")

        cards_layout.addWidget(self.gpu_card)
        cards_layout.addWidget(self.cpu_card)
        cards_layout.addWidget(self.ram_card)
        cards_layout.addWidget(self.net_card)
        layout.addLayout(cards_layout)

        # 2. Real-Time Graphs Grid (2 rows x 3 columns)
        graphs_grid = QGridLayout()
        graphs_grid.setSpacing(12)

        self.g_gpu = RealtimeGraphWidget(
            "GPU UTILIZATION",
            unit="%",
            primary_buffer=self.core.gpu.util_history,
            fixed_max=100.0,
            primary_color=self.theme_engine.active_theme.accent,
        )
        self.g_cpu = RealtimeGraphWidget(
            "CPU UTILIZATION",
            unit="%",
            primary_buffer=self.core.cpu.util_history,
            fixed_max=100.0,
            primary_color=self.theme_engine.active_theme.secondary,
        )
        self.g_ram = RealtimeGraphWidget(
            "RAM ALLOCATION",
            unit="%",
            primary_buffer=self.core.system.ram_history,
            fixed_max=100.0,
            primary_color="#38bdf8",
        )
        self.g_temp = RealtimeGraphWidget(
            "TEMPERATURES (CPU / GPU)",
            unit="°C",
            primary_buffer=self.core.cpu.temp_history,
            secondary_buffer=self.core.gpu.temp_history,
            fixed_max=105.0,
            primary_color="#f59e0b",
            secondary_color="#ef4444",
        )
        self.g_net = RealtimeGraphWidget(
            "NETWORK TRAFFIC",
            unit="KB/s",
            primary_buffer=self.core.network.rx_history,
            secondary_buffer=self.core.network.tx_history,
            primary_color="#00f0ff",
            secondary_color="#ff007f",
        )
        self.g_power = RealtimeGraphWidget(
            "POWER CONSUMPTION",
            unit="W",
            primary_buffer=self.core.gpu.power_history,
            secondary_buffer=self.core.battery.power_history,
            primary_color="#10b981",
            secondary_color="#a855f7",
        )

        graphs_grid.addWidget(self.g_gpu, 0, 0)
        graphs_grid.addWidget(self.g_cpu, 0, 1)
        graphs_grid.addWidget(self.g_ram, 0, 2)
        graphs_grid.addWidget(self.g_temp, 1, 0)
        graphs_grid.addWidget(self.g_net, 1, 1)
        graphs_grid.addWidget(self.g_power, 1, 2)

        layout.addLayout(graphs_grid, stretch=1)

        # 3. Bottom Row: Hyprland Workspaces & Media Player
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        self.ws_widget = HyprlandWorkspaceWidget(self.hyprland_mgr)
        self.media_widget = MediaControlWidget(self.media_mgr)

        bottom_row.addWidget(self.ws_widget, stretch=3)
        bottom_row.addWidget(self.media_widget, stretch=2)
        layout.addLayout(bottom_row)

        self.stack.addWidget(page)

    # ---------------- PAGE 2: CONTROLS ----------------
    def _build_controls_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self.controls_widget = SystemControlWidget(
            self.audio_mgr,
            self.brightness_mgr,
            self.wallpaper_mgr,
            self.hyprland_mgr,
            parent=page,
        )
        layout.addWidget(self.controls_widget)

        # Extra Hardware Information breakdown card
        info_card = QFrame()
        info_card.setObjectName("Card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 16, 20, 16)
        info_layout.setSpacing(10)

        info_title = QLabel("SYSTEM INFORMATION SPECIFICATION")
        info_title.setObjectName("Title")
        info_layout.addWidget(info_title)

        sys_info = self.core.system.cached_info
        specs = [
            ("Operating System", sys_info["os"]),
            ("Kernel Release", sys_info["kernel"]),
            ("Compositor", sys_info["wm"]),
            ("Default Shell", sys_info["shell"]),
            ("CPU Processor", self.core.cpu.name),
            ("Logical Cores", str(self.core.cpu.core_count)),
            ("GPU Adapter", self.core.gpu.cached_name or "NVIDIA / Integrated"),
            ("Network Adapter", self.core.network.iface),
        ]

        grid = QGridLayout()
        grid.setSpacing(10)
        for row, (k, v) in enumerate(specs):
            k_lbl = QLabel(k)
            k_lbl.setStyleSheet("color: #7e8c9f; font-weight: 700; font-size: 11px;")
            v_lbl = QLabel(v)
            v_lbl.setStyleSheet("color: #ffffff; font-weight: 600; font-size: 12px;")
            grid.addWidget(k_lbl, row, 0)
            grid.addWidget(v_lbl, row, 1)

        info_layout.addLayout(grid)
        layout.addWidget(info_card)
        layout.addStretch()

        self.stack.addWidget(page)

    # ---------------- PAGE 3: DIAGNOSTICS ----------------
    def _build_diagnostics_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Header card with Diagnose button
        hdr_card = QFrame()
        hdr_card.setObjectName("Card")
        hdr_layout = QHBoxLayout(hdr_card)
        hdr_layout.setContentsMargins(20, 16, 20, 16)

        col = QVBoxLayout()
        col.setSpacing(4)
        title = QLabel("SYSTEM DIAGNOSTICS & ANOMALY RADAR")
        title.setObjectName("Title")
        self.diag_status_lbl = QLabel("Telemetry scanner active. Ready for deep analysis.")
        self.diag_status_lbl.setObjectName("SubText")
        col.addWidget(title)
        col.addWidget(self.diag_status_lbl)
        hdr_layout.addLayout(col)
        hdr_layout.addStretch()

        self.diag_btn = QPushButton("🔍 DIAGNOSE SYSTEM")
        self.diag_btn.setObjectName("PrimaryBtn")
        self.diag_btn.setFixedSize(170, 38)
        self.diag_btn.clicked.connect(self._run_diagnostics)
        hdr_layout.addWidget(self.diag_btn)
        layout.addWidget(hdr_card)

        # Scroll Area for diagnostic findings
        self.diag_scroll = QScrollArea()
        self.diag_scroll.setWidgetResizable(True)
        self.diag_scroll.setStyleSheet("background: transparent; border: none;")

        self.diag_container = QWidget()
        self.diag_container.setStyleSheet("background: transparent;")
        self.diag_list_layout = QVBoxLayout(self.diag_container)
        self.diag_list_layout.setContentsMargins(0, 0, 0, 0)
        self.diag_list_layout.setSpacing(12)

        self.diag_scroll.setWidget(self.diag_container)
        layout.addWidget(self.diag_scroll, stretch=1)

        self.stack.addWidget(page)

    def _run_diagnostics(self):
        # Clear existing items
        while self.diag_list_layout.count() > 0:
            item = self.diag_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        snap = self.core.snapshot()
        reports = self.diag_engine.run_diagnostics(snap)

        issue_count = sum(1 for r in reports if r.severity in ("WARNING", "CRITICAL"))
        if issue_count > 0:
            self.diag_status_lbl.setText(f"⚠ {issue_count} anomalous condition(s) detected. See explanations below.")
            self.diag_status_lbl.setStyleSheet("color: #ffbe0b; font-weight: 700;")
        else:
            self.diag_status_lbl.setText("All monitored subsystems operating within optimal nominal envelopes.")
            self.diag_status_lbl.setStyleSheet("color: #00ff9f; font-weight: 700;")

        for rep in reports:
            card = QFrame()
            card.setObjectName("Card")
            clayout = QVBoxLayout(card)
            clayout.setContentsMargins(18, 14, 18, 14)
            clayout.setSpacing(8)

            # Title row
            t_row = QHBoxLayout()
            sev_badge = QLabel(f"[{rep.severity}]")
            if rep.severity == "CRITICAL":
                sev_badge.setStyleSheet("color: #ff0055; font-weight: 900;")
            elif rep.severity == "WARNING":
                sev_badge.setStyleSheet("color: #ffbe0b; font-weight: 900;")
            else:
                sev_badge.setStyleSheet("color: #00ff9f; font-weight: 900;")

            t_lbl = QLabel(rep.title)
            t_lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #ffffff;")
            t_row.addWidget(sev_badge)
            t_row.addWidget(t_lbl)
            t_row.addStretch()

            clayout.addLayout(t_row)

            sum_lbl = QLabel(rep.summary)
            sum_lbl.setStyleSheet("color: #00f0ff; font-weight: 700; font-size: 12px;")
            clayout.addWidget(sum_lbl)

            det_lbl = QLabel(rep.details)
            det_lbl.setStyleSheet("color: #8f9cb5; font-size: 12px;")
            det_lbl.setWordWrap(True)
            clayout.addWidget(det_lbl)

            # Culprits
            if rep.culprits:
                cul_box = QFrame()
                cul_box.setStyleSheet("background-color: #0a0c12; border-radius: 6px; padding: 6px;")
                cul_lay = QVBoxLayout(cul_box)
                cul_lay.setSpacing(4)
                cul_hdr = QLabel("Top Consumer Processes:")
                cul_hdr.setStyleSheet("font-size: 10px; font-weight: 700; color: #7e8c9f;")
                cul_lay.addWidget(cul_hdr)

                for c in rep.culprits:
                    c_txt = f"PID {c['pid']} — {c['name']}  ({c['usage']})"
                    c_lbl = QLabel(c_txt)
                    c_lbl.setStyleSheet("font-family: 'JetBrains Mono'; font-size: 11px; color: #ffffff;")
                    cul_lay.addWidget(c_lbl)
                clayout.addWidget(cul_box)

            # Suggested Safe Commands
            if rep.suggested_commands:
                cmd_box = QFrame()
                cmd_box.setStyleSheet("background-color: #08090d; border-radius: 6px; padding: 8px;")
                cmd_lay = QVBoxLayout(cmd_box)
                cmd_lay.setSpacing(6)
                cmd_hdr = QLabel("Safe Remediation Commands (Safe Mode: Run manually as needed):")
                cmd_hdr.setStyleSheet("font-size: 10px; font-weight: 700; color: #00ff9f;")
                cmd_lay.addWidget(cmd_hdr)

                for cmd_str in rep.suggested_commands:
                    cmd_row = QHBoxLayout()
                    c_code = QLabel(cmd_str)
                    c_code.setStyleSheet("font-family: 'JetBrains Mono'; font-size: 11px; color: #fcee0a;")
                    cmd_row.addWidget(c_code, stretch=1)

                    if not cmd_str.startswith("#"):
                        copy_btn = QPushButton("Copy")
                        copy_btn.setFixedSize(55, 24)
                        copy_btn.clicked.connect(lambda ch, s=cmd_str: QApplication.clipboard().setText(s))
                        cmd_row.addWidget(copy_btn)

                    cmd_lay.addLayout(cmd_row)
                clayout.addWidget(cmd_box)

            self.diag_list_layout.addWidget(card)

        self.diag_list_layout.addStretch()

    # ---------------- PAGE 4: BENCHMARK ----------------
    def _build_benchmark_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Header card with Run Benchmark action
        card = QFrame()
        card.setObjectName("Card")
        c_layout = QHBoxLayout(card)
        c_layout.setContentsMargins(20, 16, 20, 16)

        col = QVBoxLayout()
        col.setSpacing(4)
        title = QLabel("HYPRFETCH BENCHMARK SUITE")
        title.setObjectName("Title")
        sub = QLabel("Standardized multi-threaded CPU, GPU, RAM, and Disk I/O benchmark.")
        sub.setObjectName("SubText")
        col.addWidget(title)
        col.addWidget(sub)
        c_layout.addLayout(col)
        c_layout.addStretch()

        self.run_bench_btn = QPushButton("⚡ RUN BENCHMARK")
        self.run_bench_btn.setObjectName("PrimaryBtn")
        self.run_bench_btn.setFixedSize(170, 38)
        self.run_bench_btn.clicked.connect(self._run_benchmark)
        c_layout.addWidget(self.run_bench_btn)
        layout.addWidget(card)

        # Progress bar
        self.bench_progress = QProgressBar()
        self.bench_progress.setRange(0, 100)
        self.bench_progress.setValue(0)
        self.bench_progress.setFixedHeight(8)
        self.bench_progress.setTextVisible(False)
        self.bench_progress.setStyleSheet(
            "QProgressBar { background: #12141d; border: 1px solid #282c3f; border-radius: 4px; }"
            "QProgressBar::chunk { background: #00f0ff; border-radius: 4px; }"
        )
        layout.addWidget(self.bench_progress)

        # Results Cards Row
        res_row = QHBoxLayout()
        res_row.setSpacing(12)

        self.b_score_card = MetricCard("SYSTEM SCORE", "0 / 100")
        self.b_cpu_card = MetricCard("CPU BENCH", "-- sec")
        self.b_gpu_card = MetricCard("GPU BENCH", "-- TFLOPS")
        self.b_ram_card = MetricCard("RAM BANDWIDTH", "-- GB/s")
        self.b_disk_card = MetricCard("DISK I/O", "-- GB/s")

        res_row.addWidget(self.b_score_card)
        res_row.addWidget(self.b_cpu_card)
        res_row.addWidget(self.b_gpu_card)
        res_row.addWidget(self.b_ram_card)
        res_row.addWidget(self.b_disk_card)
        layout.addLayout(res_row)

        # History Table
        hist_card = QFrame()
        hist_card.setObjectName("Card")
        hist_lay = QVBoxLayout(hist_card)
        hist_lay.setContentsMargins(18, 14, 18, 14)
        hist_lay.setSpacing(8)

        htitle = QLabel("BENCHMARK HISTORY (Today vs Previous Runs)")
        htitle.setObjectName("Title")
        hist_lay.addWidget(htitle)

        self.hist_table = QTableWidget()
        self.hist_table.setColumnCount(6)
        self.hist_table.setHorizontalHeaderLabels(["Date & Time", "Score", "CPU", "GPU", "RAM", "Disk"])
        self.hist_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.hist_table.verticalHeader().setVisible(False)
        self.hist_table.setStyleSheet(
            "QTableWidget { background-color: #0d0f17; border: 1px solid #202433; color: #ffffff; gridline-color: #1f2430; }"
            "QHeaderView::section { background-color: #121520; color: #8f9cb5; font-weight: 700; border: none; padding: 6px; }"
        )
        hist_lay.addWidget(self.hist_table)
        layout.addWidget(hist_card, stretch=1)

        self._refresh_bench_history()
        self.stack.addWidget(page)

    def _run_benchmark(self):
        self.run_bench_btn.setEnabled(False)
        self.run_bench_btn.setText("Running tests...")
        QApplication.processEvents()

        def on_prog(step, pct):
            self.bench_progress.setValue(pct)
            self.run_bench_btn.setText(step)
            QApplication.processEvents()

        try:
            res = self.bench_engine.run_all(progress_callback=on_prog)
            score = res.get("system_score", 0)
            components = res.get("score_breakdown", {}).get("components", {})

            accent = self.theme_engine.active_theme.accent
            self.b_score_card.update_metrics("RATING", score, f"{score}/100", "Normalized", accent_color=accent)
            self.b_cpu_card.update_metrics(
                res["cpu"]["model"], components.get("cpu") or 0, res["cpu"]["display"], "Multi-process"
            )

            gpu_res = res["gpu"]
            if gpu_res.get("status") == "ok":
                gpu_subtitle = gpu_res.get("device_name", gpu_res["model"])
                gpu_stat2 = "Compute (TFLOPS)"
            else:
                gpu_subtitle = "Unavailable"
                gpu_stat2 = gpu_res.get("reason", "GPU benchmark skipped")
            self.b_gpu_card.update_metrics(gpu_subtitle, components.get("gpu") or 0, gpu_res["display"], gpu_stat2)

            self.b_ram_card.update_metrics(
                "Bandwidth", components.get("ram") or 0, res["ram"]["display"], "Write + Copy"
            )
            self.b_disk_card.update_metrics(
                "NVMe / SSD", components.get("disk") or 0, res["disk"]["display"], "Sequential"
            )

            self._refresh_bench_history()
        finally:
            self.run_bench_btn.setEnabled(True)
            self.run_bench_btn.setText("⚡ RUN BENCHMARK")
            self.bench_progress.setValue(100)

    def _refresh_bench_history(self):
        history = self.bench_engine.load_history()
        self.hist_table.setRowCount(len(history))
        for r, item in enumerate(history):
            self.hist_table.setItem(r, 0, QTableWidgetItem(item.get("date", "N/A")))
            score_item = QTableWidgetItem(f"{item.get('system_score', 0)} / 100")
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.hist_table.setItem(r, 1, score_item)
            self.hist_table.setItem(r, 2, QTableWidgetItem(item.get("cpu", {}).get("display", "N/A")))
            self.hist_table.setItem(r, 3, QTableWidgetItem(item.get("gpu", {}).get("display", "N/A")))
            self.hist_table.setItem(r, 4, QTableWidgetItem(item.get("ram", {}).get("display", "N/A")))
            self.hist_table.setItem(r, 5, QTableWidgetItem(item.get("disk", {}).get("display", "N/A")))

    # ---------------- PERIODIC TICK ----------------
    def _on_tick(self):
        snap = self.core.snapshot()

        # Update Header
        self.uptime_lbl.setText(f"Up: {snap['system']['uptime']}")
        self.weather_lbl.setText(f"⛅ {self.weather_mgr.get_weather()}")

        # Update Metric Cards
        theme = self.theme_engine.active_theme
        accent = theme.accent

        # GPU Card
        gpu = snap["gpu"]
        if gpu["available"]:
            vram_used_gb = gpu["vram_used_mb"] / 1024.0
            vram_total_gb = gpu["vram_total_mb"] / 1024.0
            self.gpu_card.update_metrics(
                gpu["short_name"],
                gpu["utilization"],
                f"{round(gpu['utilization'])}%",
                f"{round(gpu['temp'])}°C  {round(gpu['power_w'], 1)}W",
                badge=f"VRAM {vram_used_gb:.1f}/{vram_total_gb:.1f} GB",
                accent_color=accent,
            )
        else:
            self.gpu_card.update_metrics("No GPU", 0, "N/A", "")

        # CPU Card
        cpu = snap["cpu"]
        self.cpu_card.update_metrics(
            cpu["short_name"],
            cpu["utilization"],
            f"{round(cpu['utilization'])}%",
            f"{round(cpu['temp'])}°C  {cpu['freq_ghz']}GHz",
            badge=f"{cpu['cores']} Cores",
            accent_color=theme.secondary,
        )

        # RAM Card
        ram = snap["system"]["ram"]
        self.ram_card.update_metrics(
            ram["display"],
            ram["percent"],
            f"{round(ram['percent'])}%",
            f"Available {round(ram['available_bytes'] / (1024**3), 1)}GB",
            badge="Physical",
            accent_color="#38bdf8",
        )

        # Network Card
        net = snap["network"]
        self.net_card.update_metrics(
            net["iface"],
            min(100.0, net["rx_rate_kbs"] / 10.0),
            f"↓ {net['rx_formatted']}",
            f"↑ {net['tx_formatted']}",
            badge="Active",
            accent_color="#00f0ff",
        )

        # Update Workspaces & Media
        self.ws_widget.refresh()
        self.media_widget.refresh()

        # Redraw Graphs
        self.g_gpu.update()
        self.g_cpu.update()
        self.g_ram.update()
        self.g_temp.update()
        self.g_net.update()
        self.g_power.update()

    def _on_theme_changed(self, index: int):
        theme_key = self.theme_combo.currentData()
        if theme_key:
            self.theme_engine.set_theme(theme_key)
            self._apply_theme()

    def _apply_theme(self):
        theme = self.theme_engine.active_theme
        qss = theme.generate_qss()
        self.setStyleSheet(qss)

        # Update graph colors
        self.g_gpu.set_colors(theme.accent)
        self.g_cpu.set_colors(theme.secondary)
        self.g_ram.set_colors("#38bdf8")
        self.g_temp.set_colors(theme.warning, theme.critical)
        self.g_net.set_colors(theme.secondary, theme.accent)
        self.g_power.set_colors(theme.success, theme.accent)
