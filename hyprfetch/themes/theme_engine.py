"""Theme engine loading JSON themes and generating Qt styles and ANSI palettes."""

import json
import os
from pathlib import Path


class Theme:
    """Encapsulates color palette, borders, and visual parameters."""

    def __init__(self, data: dict):
        self.name = data.get("name", "Custom")
        self.accent = data.get("accent", "#ff007f")
        self.secondary = data.get("secondary", "#00f0ff")
        self.background = data.get("background", "#0b0c10")
        self.card_bg = data.get("card_bg", "#12141d")
        self.card_border = data.get("card_border", "#282c3f")
        self.text_primary = data.get("text_primary", "#ffffff")
        self.text_secondary = data.get("text_secondary", "#8f9cb5")
        self.success = data.get("success", "#00ff9f")
        self.warning = data.get("warning", "#ffbe0b")
        self.critical = data.get("critical", "#ff0055")
        self.border_radius = int(data.get("border_radius", 14))
        self.animation_speed = float(data.get("animation_speed", 1.0))

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "accent": self.accent,
            "secondary": self.secondary,
            "background": self.background,
            "card_bg": self.card_bg,
            "card_border": self.card_border,
            "text_primary": self.text_primary,
            "text_secondary": self.text_secondary,
            "success": self.success,
            "warning": self.warning,
            "critical": self.critical,
            "border_radius": self.border_radius,
            "animation_speed": self.animation_speed,
        }

    def generate_qss(self) -> str:
        r = self.border_radius
        return f"""
        QMainWindow, QWidget#CentralWidget {{
            background-color: {self.background};
            color: {self.text_primary};
            font-family: 'JetBrains Mono', 'Fira Code', 'Segoe UI', sans-serif;
        }}

        QWidget#Card {{
            background-color: {self.card_bg};
            border: 1px solid {self.card_border};
            border-radius: {r}px;
        }}

        QLabel {{
            color: {self.text_primary};
            background: transparent;
        }}

        QLabel#SubText {{
            color: {self.text_secondary};
            font-size: 11px;
        }}

        QLabel#Title {{
            color: {self.text_secondary};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
        }}

        QLabel#Value {{
            color: {self.text_primary};
            font-size: 20px;
            font-weight: 800;
        }}

        QLabel#AccentValue {{
            color: {self.accent};
            font-size: 20px;
            font-weight: 800;
        }}

        /* Buttons */
        QPushButton {{
            background-color: {self.card_bg};
            color: {self.text_primary};
            border: 1px solid {self.card_border};
            border-radius: 8px;
            padding: 6px 14px;
            font-weight: 600;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {self.accent}22;
            border-color: {self.accent};
            color: {self.accent};
        }}
        QPushButton:pressed {{
            background-color: {self.accent}44;
        }}
        QPushButton#PrimaryBtn {{
            background-color: {self.accent};
            color: #000000;
            border: none;
            font-weight: 700;
        }}
        QPushButton#PrimaryBtn:hover {{
            background-color: {self.secondary};
            color: #000000;
        }}

        /* Sliders */
        QSlider::groove:horizontal {{
            height: 6px;
            background: {self.card_border};
            border-radius: 3px;
        }}
        QSlider::sub-page:horizontal {{
            background: {self.accent};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {self.text_primary};
            border: 2px solid {self.accent};
            width: 14px;
            margin-top: -4px;
            margin-bottom: -4px;
            border-radius: 7px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {self.accent};
        }}

        /* Navigation Tab Buttons */
        QPushButton#NavBtn {{
            background: transparent;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            color: {self.text_secondary};
            font-weight: 700;
            font-size: 12px;
        }}
        QPushButton#NavBtn:hover {{
            color: {self.text_primary};
            background-color: {self.card_bg};
        }}
        QPushButton#NavBtn[active="true"] {{
            color: {self.accent};
            background-color: {self.accent}18;
            border-bottom: 2px solid {self.accent};
        }}

        /* ComboBox */
        QComboBox {{
            background-color: {self.card_bg};
            color: {self.text_primary};
            border: 1px solid {self.card_border};
            border-radius: 8px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 600;
        }}
        QComboBox:hover {{
            border-color: {self.accent};
        }}
        QComboBox QAbstractItemView {{
            background-color: {self.card_bg};
            color: {self.text_primary};
            selection-background-color: {self.accent}33;
            selection-color: {self.accent};
            border: 1px solid {self.card_border};
            border-radius: 6px;
        }}

        /* Scrollbars */
        QScrollBar:vertical {{
            border: none;
            background: {self.background};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {self.card_border};
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {self.accent};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        """

    def get_terminal_palette(self) -> dict:
        """Convert theme hex colors to approximate ANSI escape sequences."""
        def hex_to_rgb(h: str):
            h = h.lstrip("#")
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) if len(h) >= 6 else (255, 255, 255)

        ar, ag, ab = hex_to_rgb(self.accent)
        sr, sg, sb = hex_to_rgb(self.secondary)
        cr, cg, cb = hex_to_rgb(self.critical)
        wr, wg, wb = hex_to_rgb(self.warning)

        return {
            "accent": f"\033[38;2;{ar};{ag};{ab}m",
            "secondary": f"\033[38;2;{sr};{sg};{sb}m",
            "critical": f"\033[38;2;{cr};{cg};{cb}m",
            "warning": f"\033[38;2;{wr};{wg};{wb}m",
            "dim": "\033[38;5;240m",
            "bold": "\033[1m",
            "reset": "\033[0m",
        }


class ThemeEngine:
    """Manages discovery, loading, switching, and persisting of themes."""

    def __init__(self):
        self.themes_dir = Path(__file__).parent
        self.user_theme_file = Path(os.path.expanduser("~/.config/hyprfetch/theme.json"))
        self.available_themes: dict[str, Theme] = {}
        self.active_theme: Theme = None
        self.load_all()

    def load_all(self):
        # 1. Load shipped themes
        for path in self.themes_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    theme = Theme(data)
                    self.available_themes[theme.name.lower()] = theme
            except Exception:
                pass

        # 2. Check user custom theme override
        if self.user_theme_file.exists():
            try:
                with open(self.user_theme_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    user_theme = Theme(data)
                    self.available_themes["custom"] = user_theme
                    self.active_theme = user_theme
            except Exception:
                pass

        if not self.active_theme:
            self.active_theme = self.available_themes.get("nova") or next(iter(self.available_themes.values()), Theme({}))

    def set_theme(self, name: str) -> Theme:
        key = name.lower()
        if key in self.available_themes:
            self.active_theme = self.available_themes[key]
        return self.active_theme

    def save_user_theme(self, theme: Theme):
        self.user_theme_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.user_theme_file, "w", encoding="utf-8") as f:
            json.dump(theme.to_dict(), f, indent=2)
        self.available_themes["custom"] = theme
        self.active_theme = theme
