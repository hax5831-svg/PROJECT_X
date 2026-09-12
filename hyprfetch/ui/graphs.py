"""Neon real-time time-series graph widgets for GPU, CPU, RAM, Network, and Power telemetry."""

import time
from hyprfetch.core.system import TimeSeriesBuffer
from hyprfetch.ui.qt_compat import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPointF,
    QRectF,
    Qt,
    QWidget,
)


class RealtimeGraphWidget(QWidget):
    """Cyberpunk anti-aliased graph widget rendering glowing curves and time-series history."""

    def __init__(
        self,
        title: str,
        unit: str = "%",
        primary_buffer: TimeSeriesBuffer = None,
        secondary_buffer: TimeSeriesBuffer = None,
        fixed_max: float = None,
        primary_color: str = "#00f0ff",
        secondary_color: str = "#ff007f",
        parent=None,
    ):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.primary_buffer = primary_buffer or TimeSeriesBuffer(120, 120.0)
        self.secondary_buffer = secondary_buffer
        self.fixed_max = fixed_max
        self.primary_color = QColor(primary_color)
        self.secondary_color = QColor(secondary_color)
        self.setMinimumHeight(150)
        self.setMinimumWidth(220)

    def set_colors(self, primary: str, secondary: str = None):
        self.primary_color = QColor(primary)
        if secondary:
            self.secondary_color = QColor(secondary)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())

        # Card container bounds
        rect = QRectF(0, 0, w, h)

        # Draw Card background
        painter.setPen(QPen(QColor("#252836"), 1))
        painter.setBrush(QBrush(QColor("#10121a")))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 10, 10)

        # Layout metrics
        padding_left = 42.0
        padding_right = 16.0
        padding_top = 34.0
        padding_bottom = 24.0

        graph_w = w - padding_left - padding_right
        graph_h = h - padding_top - padding_bottom
        graph_bottom = h - padding_bottom
        graph_top = padding_top

        # Latest values
        p_latest = self.primary_buffer.latest
        s_latest = self.secondary_buffer.latest if self.secondary_buffer else None

        # Title and current value header
        painter.setFont(QFont("JetBrains Mono", 9, QFont.Weight.Bold))
        painter.setPen(QPen(QColor("#8f9cb5")))
        painter.drawText(int(padding_left), 22, self.title)

        # Value readout
        if s_latest is not None:
            val_text = f"↓ {round(p_latest, 1)}  ↑ {round(s_latest, 1)} {self.unit}"
        else:
            val_text = f"{round(p_latest, 1)} {self.unit}"

        painter.setFont(QFont("JetBrains Mono", 10, QFont.Weight.ExtraBold))
        painter.setPen(QPen(self.primary_color))
        painter.drawText(QRectF(w - 220, 8, 205, 20), Qt.AlignmentFlag.AlignRight, val_text)

        # Determine scale
        if self.fixed_max is not None:
            max_val = self.fixed_max
        else:
            max_p = self.primary_buffer.max
            max_s = self.secondary_buffer.max if self.secondary_buffer else 0.0
            max_val = max(10.0, max_p, max_s) * 1.15

        # Horizontal Grid Lines (4 levels)
        painter.setFont(QFont("JetBrains Mono", 7))
        for i in range(4):
            val = (max_val / 3.0) * (3 - i)
            y = graph_top + (graph_h / 3.0) * i

            # Grid line
            painter.setPen(QPen(QColor(255, 255, 255, 18), 1, Qt.PenStyle.DashLine))
            painter.drawLine(int(padding_left), int(y), int(w - padding_right), int(y))

            # Y-axis label
            painter.setPen(QPen(QColor("#5c667a")))
            lbl = f"{int(round(val))}" if val >= 10 else f"{round(val, 1)}"
            painter.drawText(QRectF(4, y - 6, padding_left - 8, 12), Qt.AlignmentFlag.AlignRight, lbl)

        # Baseline axis line
        painter.setPen(QPen(QColor("#2c3245"), 1))
        painter.drawLine(int(padding_left), int(graph_bottom), int(w - padding_right), int(graph_bottom))

        # Time labels
        painter.setPen(QPen(QColor("#5c667a")))
        painter.drawText(int(padding_left), int(h - 8), "-60s")
        painter.drawText(int(padding_left + graph_w * 0.5 - 12), int(h - 8), "-30s")
        painter.drawText(int(w - padding_right - 28), int(h - 8), "NOW")

        # Draw series
        now = time.time()
        time_window = 60.0  # display 60 seconds

        if self.secondary_buffer:
            self._draw_series(
                painter,
                self.secondary_buffer,
                self.secondary_color,
                now,
                time_window,
                max_val,
                padding_left,
                graph_top,
                graph_w,
                graph_h,
                graph_bottom,
            )

        self._draw_series(
            painter,
            self.primary_buffer,
            self.primary_color,
            now,
            time_window,
            max_val,
            padding_left,
            graph_top,
            graph_w,
            graph_h,
            graph_bottom,
        )

    def _draw_series(
        self,
        painter: QPainter,
        buf: TimeSeriesBuffer,
        color: QColor,
        now: float,
        time_window: float,
        max_val: float,
        left: float,
        top: float,
        width: float,
        height: float,
        bottom: float,
    ):
        points = buf.points()
        if not points:
            return

        coords = []
        for ts, val in points:
            age = max(0.0, now - ts)
            if age > time_window:
                continue
            x = left + width * (1.0 - (age / time_window))
            normalized = max(0.0, min(1.0, val / max_val))
            y = bottom - (normalized * height)
            coords.append(QPointF(x, y))

        if len(coords) < 2:
            if coords:
                coords.insert(0, QPointF(left, coords[0].y()))
            else:
                return

        # Build smooth line path
        path = QPainterPath()
        path.moveTo(coords[0])

        for i in range(1, len(coords)):
            p0 = coords[i - 1]
            p1 = coords[i]
            # Smooth cubic bezier
            cpx = (p0.x() + p1.x()) / 2.0
            path.cubicTo(cpx, p0.y(), cpx, p1.y(), p1.x(), p1.y())

        # Area gradient fill
        fill_path = QPainterPath(path)
        fill_path.lineTo(coords[-1].x(), bottom)
        fill_path.lineTo(coords[0].x(), bottom)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, top, 0, bottom)
        grad.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), 75))
        grad.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
        painter.fillPath(fill_path, QBrush(grad))

        # Glowing line stroke (multi-pass glow)
        glow_pen = QPen(QColor(color.red(), color.green(), color.blue(), 45), 4)
        painter.setPen(glow_pen)
        painter.drawPath(path)

        main_pen = QPen(color, 2)
        painter.setPen(main_pen)
        painter.drawPath(path)

        # Pulse dot on latest coordinate
        last_pt = coords[-1]
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.setPen(QPen(color, 2))
        painter.drawEllipse(last_pt, 3.5, 3.5)
