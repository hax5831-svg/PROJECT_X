"""Specialized UI widgets: telemetry cards, controls, workspaces, and media player."""

from hyprfetch.modules.audio import AudioManager
from hyprfetch.modules.brightness import BrightnessManager
from hyprfetch.modules.hyprland import HyprlandManager
from hyprfetch.modules.media import MediaManager
from hyprfetch.modules.wallpaper import WallpaperManager
from hyprfetch.ui.gauges import CircularGaugeWidget, SegmentedBarWidget
from hyprfetch.ui.qt_compat import (
    QBrush,
    QColor,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    Qt,
    QVBoxLayout,
    QWidget,
)


class MetricCard(QFrame):
    """Cyberpunk telemetry card displaying device status, gauge, and live values."""

    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.title_text = title

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Header row
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setObjectName("Title")
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch()

        self.badge_lbl = QLabel("")
        self.badge_lbl.setObjectName("SubText")
        header_layout.addWidget(self.badge_lbl)
        layout.addLayout(header_layout)

        # Main Subtitle / Hardware name
        self.subtitle_lbl = QLabel(subtitle)
        self.subtitle_lbl.setObjectName("Value")
        layout.addWidget(self.subtitle_lbl)

        # Progress / Segmented bar
        self.bar = SegmentedBarWidget(segments=14, parent=self)
        layout.addWidget(self.bar)

        # Detail readout row (e.g. 76% | 61°C)
        detail_layout = QHBoxLayout()
        detail_layout.setContentsMargins(0, 4, 0, 0)
        self.stat1_lbl = QLabel("0%")
        self.stat1_lbl.setObjectName("AccentValue")
        self.stat2_lbl = QLabel("")
        self.stat2_lbl.setObjectName("SubText")

        detail_layout.addWidget(self.stat1_lbl)
        detail_layout.addStretch()
        detail_layout.addWidget(self.stat2_lbl)
        layout.addLayout(detail_layout)

    def update_metrics(self, subtitle: str, bar_pct: float, stat1: str, stat2: str = "", badge: str = "", accent_color: str = None):
        self.subtitle_lbl.setText(subtitle)
        self.bar.set_value(bar_pct)
        if accent_color:
            self.bar.set_color(accent_color)
            self.stat1_lbl.setStyleSheet(f"color: {accent_color}; font-size: 18px; font-weight: 800;")
        self.stat1_lbl.setText(stat1)
        self.stat2_lbl.setText(stat2)
        self.badge_lbl.setText(badge)


class HyprlandWorkspaceWidget(QFrame):
    """Visual Hyprland workspace switcher and active window indicator."""

    def __init__(self, hyprland_mgr: HyprlandManager, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.hyprland = hyprland_mgr

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(8)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("HYPRLAND WORKSPACES")
        title.setObjectName("Title")
        hdr.addWidget(title)
        hdr.addStretch()

        self.window_lbl = QLabel("No active window")
        self.window_lbl.setObjectName("SubText")
        self.window_lbl.setMaximumWidth(450)
        hdr.addWidget(self.window_lbl)
        self.main_layout.addLayout(hdr)

        # Workspace buttons row
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_layout.setSpacing(8)
        self.main_layout.addLayout(self.btn_layout)

        self.ws_buttons: dict[int, QPushButton] = {}
        self.refresh()

    def refresh(self):
        workspaces = self.hyprland.get_workspaces()
        active_ws = self.hyprland.get_active_workspace()
        active_win = self.hyprland.get_active_window()

        win_title = active_win.get("title", "")
        win_class = active_win.get("class", "")
        if win_title:
            display_title = f"{win_title} ({win_class})" if win_class else win_title
            if len(display_title) > 50:
                display_title = display_title[:47] + "..."
            self.window_lbl.setText(display_title)
        else:
            self.window_lbl.setText("Desktop")

        # Discover all IDs: at least 1-5 or whatever is open
        all_ids = sorted(list(set([1, 2, 3, 4, 5] + [w.get("id", 1) for w in workspaces])))

        # Ensure buttons exist
        for ws_id in all_ids:
            if ws_id not in self.ws_buttons:
                btn = QPushButton(str(ws_id))
                btn.setFixedSize(38, 32)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda checked, i=ws_id: self._switch_ws(i))
                self.btn_layout.addWidget(btn)
                self.ws_buttons[ws_id] = btn

        # Update styling
        ws_dict = {w.get("id"): w for w in workspaces}
        for ws_id, btn in self.ws_buttons.items():
            is_active = (ws_id == active_ws)
            win_count = ws_dict.get(ws_id, {}).get("windows", 0)

            dot = f" ({win_count})" if win_count > 0 else ""
            btn.setText(f"{ws_id}{dot}")

            if is_active:
                btn.setStyleSheet("background-color: #00f0ff; color: #000000; font-weight: 800; border: none;")
            elif win_count > 0:
                btn.setStyleSheet("background-color: #1e2230; color: #ffffff; border: 1px solid #3c445c;")
            else:
                btn.setStyleSheet("background-color: #12141d; color: #5c667a; border: 1px solid #202433;")

        self.btn_layout.addStretch()

    def _switch_ws(self, ws_id: int):
        self.hyprland.switch_workspace(ws_id)
        self.refresh()


class MediaControlWidget(QFrame):
    """Media player card with live MPRIS track metadata and playback controls."""

    def __init__(self, media_mgr: MediaManager, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.media = media_mgr

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        # Track & Artist info
        info_col = QVBoxLayout()
        info_col.setContentsMargins(0, 0, 0, 0)
        info_col.setSpacing(2)

        self.title_lbl = QLabel("NOW PLAYING")
        self.title_lbl.setObjectName("Title")
        info_col.addWidget(self.title_lbl)

        self.track_lbl = QLabel("Nothing playing")
        self.track_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
        info_col.addWidget(self.track_lbl)

        self.artist_lbl = QLabel("")
        self.artist_lbl.setObjectName("SubText")
        info_col.addWidget(self.artist_lbl)

        layout.addLayout(info_col, stretch=1)

        # Playback controls
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setFixedSize(36, 32)
        self.prev_btn.clicked.connect(self._prev)

        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("PrimaryBtn")
        self.play_btn.setFixedSize(42, 32)
        self.play_btn.clicked.connect(self._play_pause)

        self.next_btn = QPushButton("⏭")
        self.next_btn.setFixedSize(36, 32)
        self.next_btn.clicked.connect(self._next)

        btn_layout.addWidget(self.prev_btn)
        btn_layout.addWidget(self.play_btn)
        btn_layout.addWidget(self.next_btn)

        layout.addLayout(btn_layout)

    def refresh(self):
        info = self.media.get_info()
        status = info.get("status", "Stopped")
        title = info.get("title", "")
        artist = info.get("artist", "")

        self.track_lbl.setText(title or "Nothing playing")
        self.artist_lbl.setText(artist if artist else ("MPRIS Idle" if title else ""))

        if status == "Playing":
            self.play_btn.setText("⏸")
            self.play_btn.setStyleSheet("background-color: #ff007f; color: #ffffff; font-weight: 800;")
        else:
            self.play_btn.setText("▶")
            self.play_btn.setStyleSheet("background-color: #00f0ff; color: #000000; font-weight: 800;")

    def _play_pause(self):
        self.media.play_pause()
        self.refresh()

    def _prev(self):
        self.media.previous_track()
        self.refresh()

    def _next(self):
        self.media.next_track()
        self.refresh()


class SystemControlWidget(QFrame):
    """Interactive system controls for volume, brightness, audio sinks, wallpapers, and Hyprland."""

    def __init__(
        self,
        audio_mgr: AudioManager,
        brightness_mgr: BrightnessManager,
        wallpaper_mgr: WallpaperManager,
        hyprland_mgr: HyprlandManager,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("Card")
        self.audio = audio_mgr
        self.brightness = brightness_mgr
        self.wallpaper = wallpaper_mgr
        self.hyprland = hyprland_mgr

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # Header
        title = QLabel("SYSTEM CONTROLS")
        title.setObjectName("Title")
        layout.addWidget(title)

        # 1. Volume Control Row
        vol_row = QHBoxLayout()
        vol_label = QLabel("Volume")
        vol_label.setStyleSheet("font-weight: 700; min-width: 85px;")
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_val_lbl = QLabel("0%")
        self.vol_val_lbl.setStyleSheet("min-width: 45px; font-weight: 700;")
        self.mute_btn = QPushButton("Mute")
        self.mute_btn.setFixedWidth(65)

        self.vol_slider.valueChanged.connect(self._on_vol_slider)
        self.mute_btn.clicked.connect(self._on_mute_clicked)

        vol_row.addWidget(vol_label)
        vol_row.addWidget(self.vol_slider, stretch=1)
        vol_row.addWidget(self.vol_val_lbl)
        vol_row.addWidget(self.mute_btn)
        layout.addLayout(vol_row)

        # 2. Brightness Control Row
        br_row = QHBoxLayout()
        br_label = QLabel("Brightness")
        br_label.setStyleSheet("font-weight: 700; min-width: 85px;")
        self.br_slider = QSlider(Qt.Orientation.Horizontal)
        self.br_slider.setRange(5, 100)
        self.br_val_lbl = QLabel("100%")
        self.br_val_lbl.setStyleSheet("min-width: 45px; font-weight: 700;")

        self.br_slider.valueChanged.connect(self._on_brightness_slider)

        br_row.addWidget(br_label)
        br_row.addWidget(self.br_slider, stretch=1)
        br_row.addWidget(self.br_val_lbl)
        layout.addLayout(br_row)

        # 3. Audio Output Sinks
        sink_row = QHBoxLayout()
        sink_label = QLabel("Audio Output")
        sink_label.setStyleSheet("font-weight: 700; min-width: 85px;")
        self.sink_combo = QComboBox()
        self.sink_combo.currentIndexChanged.connect(self._on_sink_selected)

        sink_row.addWidget(sink_label)
        sink_row.addWidget(self.sink_combo, stretch=1)
        layout.addLayout(sink_row)

        # 4. Wallpaper Controls
        wall_row = QHBoxLayout()
        wall_label = QLabel("Wallpaper")
        wall_label.setStyleSheet("font-weight: 700; min-width: 85px;")

        self.wall_prev_btn = QPushButton("Previous")
        self.wall_next_btn = QPushButton("Next")
        self.wall_rand_btn = QPushButton("Random")

        self.wall_prev_btn.clicked.connect(self._on_wall_prev)
        self.wall_next_btn.clicked.connect(self._on_wall_next)
        self.wall_rand_btn.clicked.connect(self._on_wall_rand)

        wall_row.addWidget(wall_label)
        wall_row.addWidget(self.wall_prev_btn)
        wall_row.addWidget(self.wall_next_btn)
        wall_row.addWidget(self.wall_rand_btn)
        wall_row.addStretch()
        layout.addLayout(wall_row)

        # 5. Hyprland Session Actions
        hypr_row = QHBoxLayout()
        hypr_label = QLabel("Hyprland")
        hypr_label.setStyleSheet("font-weight: 700; min-width: 85px;")

        self.reload_btn = QPushButton("Reload")
        self.lock_btn = QPushButton("Lock")
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setStyleSheet("color: #ff0055; border-color: #ff005544;")

        self.reload_btn.clicked.connect(self._on_hypr_reload)
        self.lock_btn.clicked.connect(self._on_hypr_lock)
        self.logout_btn.clicked.connect(self._on_hypr_logout)

        hypr_row.addWidget(hypr_label)
        hypr_row.addWidget(self.reload_btn)
        hypr_row.addWidget(self.lock_btn)
        hypr_row.addWidget(self.logout_btn)
        hypr_row.addStretch()
        layout.addLayout(hypr_row)

        self._init_states()

    def _init_states(self):
        # Init volume
        st = self.audio.get_status()
        self.vol_slider.blockSignals(True)
        self.vol_slider.setValue(st["volume"])
        self.vol_slider.blockSignals(False)
        self.vol_val_lbl.setText(f"{st['volume']}%")
        self.mute_btn.setText("Unmute" if st["muted"] else "Mute")

        # Init brightness
        br = self.brightness.get_brightness()
        self.br_slider.blockSignals(True)
        self.br_slider.setValue(br)
        self.br_slider.blockSignals(False)
        self.br_val_lbl.setText(f"{br}%")

        # Init sinks
        sinks = self.audio.get_sinks()
        self.sink_combo.blockSignals(True)
        self.sink_combo.clear()
        selected_idx = 0
        for idx, s in enumerate(sinks):
            self.sink_combo.addItem(s["name"], s["id"])
            if s.get("is_default"):
                selected_idx = idx
        if sinks:
            self.sink_combo.setCurrentIndex(selected_idx)
        self.sink_combo.blockSignals(False)

    def _on_vol_slider(self, val: int):
        self.vol_val_lbl.setText(f"{val}%")
        self.audio.set_volume(val)

    def _on_mute_clicked(self):
        self.audio.toggle_mute()
        st = self.audio.get_status()
        self.mute_btn.setText("Unmute" if st["muted"] else "Mute")

    def _on_brightness_slider(self, val: int):
        self.br_val_lbl.setText(f"{val}%")
        self.brightness.set_brightness(val)

    def _on_sink_selected(self, index: int):
        sink_id = self.sink_combo.currentData()
        if sink_id:
            self.audio.set_sink(sink_id)

    def _on_wall_prev(self):
        self.wallpaper.previous_wallpaper()

    def _on_wall_next(self):
        self.wallpaper.next_wallpaper()

    def _on_wall_rand(self):
        self.wallpaper.random_wallpaper()

    def _on_hypr_reload(self):
        self.hyprland.reload()

    def _on_hypr_lock(self):
        self.hyprland.lock()

    def _on_hypr_logout(self):
        reply = QMessageBox.question(
            self,
            "Confirm Logout",
            "Exit Hyprland session and return to login manager?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.hyprland.logout()
