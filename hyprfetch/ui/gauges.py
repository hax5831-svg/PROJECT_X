"""Gauges and visual telemetry meters: circular arcs and segmented cyberpunk bars."""

from hyprfetch.ui.qt_compat import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QRectF,
    Qt,
    QWidget,
)


class CircularGaugeWidget(QWidget):
    """Circular neon arc meter for temperatures and percentages."""

    def __init__(self, title: str = "", unit: str = "%", max_val: float = 100.0, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.max_val = max_val
        self.current_val = 0.0
        self.accent_color = QColor("#00f0ff")
        self.setMinimumSize(110, 110)

    def set_value(self, val: float):
        self.current_val = max(0.0, min(self.max_val, val))
        self.update()

    def set_color(self, hex_color: str):
        self.accent_color = QColor(hex_color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        size = min(w, h) - 16
        rect = QRectF((w - size) / 2.0, (h - size) / 2.0, size, size)

        # Background track arc (270 degrees total)
        start_angle = 225.0
        total_span = 270.0

        track_pen = QPen(QColor("#1f2430"), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, int(start_angle * 16), int(-total_span * 16))

        # Filled value arc
        ratio = self.current_val / self.max_val if self.max_val > 0 else 0.0
        val_span = total_span * ratio

        # Color progression (cool -> warm -> critical red)
        if ratio > 0.85:
            arc_color = QColor("#ff0055")
        elif ratio > 0.70:
            arc_color = QColor("#ffbe0b")
        else:
            arc_color = self.accent_color

        if val_span > 0.5:
            glow_pen = QPen(QColor(arc_color.red(), arc_color.green(), arc_color.blue(), 60), 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(glow_pen)
            painter.drawArc(rect, int(start_angle * 16), int(-val_span * 16))

            value_pen = QPen(arc_color, 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(value_pen)
            painter.drawArc(rect, int(start_angle * 16), int(-val_span * 16))

        # Centered value text
        painter.setFont(QFont("JetBrains Mono", 12, QFont.Weight.ExtraBold))
        painter.setPen(QPen(QColor("#ffffff")))
        val_str = f"{int(round(self.current_val))}{self.unit}"
        painter.drawText(rect.adjusted(0, -6, 0, -6), Qt.AlignmentFlag.AlignCenter, val_str)

        # Title subtitle
        if self.title:
            painter.setFont(QFont("JetBrains Mono", 7, QFont.Weight.Bold))
            painter.setPen(QPen(QColor("#7e8c9f")))
            painter.drawText(rect.adjusted(0, 26, 0, 0), Qt.AlignmentFlag.AlignCenter, self.title)


class SegmentedBarWidget(QWidget):
    """Segmented cyber block gauge (e.g. [||||||||....])."""

    def __init__(self, segments: int = 15, parent=None):
        super().__init__(parent)
        self.segments = segments
        self.value = 0.0  # 0 to 100
        self.accent_color = QColor("#00f0ff")
        self.setFixedHeight(16)
        self.setMinimumWidth(120)

    def set_value(self, val: float):
        self.value = max(0.0, min(100.0, val))
        self.update()

    def set_color(self, hex_color: str):
        self.accent_color = QColor(hex_color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        spacing = 3.0
        seg_w = (w - (self.segments - 1) * spacing) / self.segments

        active_count = int(round((self.value / 100.0) * self.segments))

        for i in range(self.segments):
            x = i * (seg_w + spacing)
            seg_rect = QRectF(x, 2, seg_w, h - 4)

            if i < active_count:
                # Color tint for high loads
                pct = (i + 1) / self.segments
                if pct > 0.85:
                    col = QColor("#ff0055")
                elif pct > 0.70:
                    col = QColor("#ffbe0b")
                else:
                    col = self.accent_color

                painter.setBrush(QBrush(col))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(seg_rect, 2, 2)
            else:
                painter.setBrush(QBrush(QColor("#1f2430")))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(seg_rect, 2, 2)
