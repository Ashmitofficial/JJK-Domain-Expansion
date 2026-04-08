"""
Main Window — Industry-level dark-themed PyQt5 application.

Layout:
  ┌──────────────────────────────────────────────────┐
  │  FPS ▪                                ┌────────┐ │
  │                                       │WEBCAM  │ │
  │                                       │+ scan  │ │
  │                                       └────────┘ │
  │              ╔════════════════════╗               │
  │              ║  AMBIENT / DOMAIN  ║               │
  │              ║    ANIMATIONS      ║               │
  │              ╚════════════════════╝               │
  │                                                  │
  │          ┌─────────────────────────┐             │
  │          │   STATUS HUD (faded)    │             │
  │          └─────────────────────────┘             │
  └──────────────────────────────────────────────────┘

Features:
  - Ambient floating particles even in idle
  - Vignette overlay always active
  - Circular confirmation ring (not text bars)
  - Scanline effect on webcam
  - Glow border on webcam changes color per domain
  - Screen shake for Sukuna
  - Smooth fade transitions everywhere
"""

from __future__ import annotations

import time
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QImage, QPixmap,
    QPainterPath, QPalette, QLinearGradient,
)
from PyQt5.QtWidgets import QMainWindow, QWidget, QLabel

from config import cfg
from ml.hand_tracker import HandTracker
from animation.domain_controller import DomainController, State
from animation.effects import (
    GojoEffect, SukunaEffect, AmbientRenderer, OverlayRenderer, qcolor,
)


# ──────────────────────────────────────────────
#  Animation Canvas
# ──────────────────────────────────────────────

class AnimationCanvas(QWidget):
    """
    Full-screen compositing canvas.
    Paint order: ambient → domain effects → overlay (vignette, flash, titles).
    """

    def __init__(self, controller: DomainController, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._controller = controller
        self._gojo = GojoEffect()
        self._sukuna = SukunaEffect()
        self._ambient = AmbientRenderer()
        self._overlay = OverlayRenderer()
        self._last_time = time.time()
        self._activated = False

        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    @property
    def shake_offset(self) -> tuple:
        if self._controller.domain_type == "sukuna":
            return self._sukuna.shake_offset
        return (0.0, 0.0)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = float(self.width()), float(self.height())
        cx, cy = w / 2, h / 2
        now = time.time()
        dt = min(now - self._last_time, 0.05)  # cap dt to prevent explosion
        self._last_time = now

        state = self._controller.state
        domain = self._controller.domain_type
        progress = self._controller.progress

        # ── Layer 1: Ambient particles + grid (always) ──
        self._ambient.render(painter, w, h, dt)

        # ── Layer 2: Confirmation ring ──
        if state == State.CONFIRMING:
            self._overlay.render_confirm_ring(
                painter, cx, cy, progress,
                self._controller.confirm_gesture,
            )

        # ── Layer 3: Domain effects ──
        is_domain_active = state in (State.ACTIVATING, State.ACTIVE, State.FADING)

        if is_domain_active and domain:
            effect = self._gojo if domain == "gojo" else self._sukuna
            elapsed = now - effect._start_time if effect._start_time else 0

            # Activate on first frame
            if state == State.ACTIVATING and not self._activated:
                self._activated = True
                effect.activate(cx, cy, w, h)

            # Render
            effect.render(painter, cx, cy, w, h, progress, dt)

            # Color grading overlay
            self._overlay.render_color_grading(painter, w, h, domain, progress)

            # Activation flash
            self._overlay.render_flash(painter, w, h, domain, elapsed)

            # Domain title (kanji + typewriter)
            self._overlay.render_domain_title(painter, w, h, domain, progress)
        else:
            self._activated = False
            self._gojo.reset()
            self._sukuna.reset()

        # ── Layer 4: Vignette (always on top) ──
        self._overlay.render_vignette(painter, w, h)

        painter.end()


# ──────────────────────────────────────────────
#  Webcam Widget
# ──────────────────────────────────────────────

class WebcamWidget(QWidget):
    """
    Small webcam feed with:
    - Rounded corners
    - Animated glow border (color shifts per domain)
    - Subtle scanline overlay for cyberpunk feel
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        lo = cfg.layout
        self._feed_w = lo.WEBCAM_W
        self._feed_h = lo.WEBCAM_H
        self._total_w = lo.WEBCAM_W + lo.WEBCAM_PADDING
        self._total_h = lo.WEBCAM_H + lo.WEBCAM_PADDING
        self.setFixedSize(self._total_w, self._total_h)

        self._pixmap: Optional[QPixmap] = None
        self._glow_color = qcolor(cfg.colors.WEBCAM_BORDER_IDLE)
        self._border_radius = lo.WEBCAM_BORDER_RADIUS

    def set_frame(self, q_image: QImage) -> None:
        scaled = q_image.scaled(
            self._feed_w, self._feed_h,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self._pixmap = QPixmap.fromImage(scaled)
        self.update()

    def set_glow(self, color: QColor) -> None:
        self._glow_color = color
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        lo = cfg.layout

        pad = lo.WEBCAM_PADDING // 2
        outer = QRectF(2, 2, self.width() - 4, self.height() - 4)
        inner = QRectF(pad, pad, self._feed_w, self._feed_h)

        # ── Outer glow (soft, wide) ──
        glow_pen = QPen(QColor(
            self._glow_color.red(),
            self._glow_color.green(),
            self._glow_color.blue(),
            self._glow_color.alpha() // 3,
        ))
        glow_pen.setWidthF(lo.WEBCAM_GLOW_WIDTH)
        painter.setPen(glow_pen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.drawRoundedRect(outer, self._border_radius + 4, self._border_radius + 4)

        # ── Border ──
        border_pen = QPen(self._glow_color)
        border_pen.setWidthF(lo.WEBCAM_BORDER_WIDTH)
        painter.setPen(border_pen)
        painter.setBrush(QBrush(qcolor(cfg.colors.WEBCAM_BG)))
        painter.drawRoundedRect(outer, self._border_radius, self._border_radius)

        # ── Webcam image (clipped to rounded rect) ──
        if self._pixmap:
            clip = QPainterPath()
            clip.addRoundedRect(inner, self._border_radius - 2, self._border_radius - 2)
            painter.setClipPath(clip)
            painter.drawPixmap(int(inner.x()), int(inner.y()), self._pixmap)
            painter.setClipping(False)

            # ── Scanline overlay ──
            scanline_pen = QPen(QColor(0, 0, 0, 20))
            scanline_pen.setWidthF(1)
            painter.setPen(scanline_pen)
            for y in range(int(inner.y()), int(inner.y() + inner.height()), 3):
                painter.drawLine(
                    QPointF(inner.x(), y),
                    QPointF(inner.x() + inner.width(), y),
                )

            # ── Top gradient fade (subtle) ──
            fade_h = 20
            fade_grad = QLinearGradient(inner.x(), inner.y(), inner.x(), inner.y() + fade_h)
            fade_grad.setColorAt(0.0, QColor(6, 6, 12, 120))
            fade_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(QPen(QColor(0, 0, 0, 0)))
            painter.setBrush(QBrush(fade_grad))
            painter.drawRect(QRectF(inner.x(), inner.y(), inner.width(), fade_h))

        # ── "LIVE" indicator dot ──
        painter.setPen(QPen(QColor(0, 0, 0, 0)))
        pulse = abs(time.time() % 2 - 1)  # 0→1→0 over 2s
        dot_alpha = int(100 + 155 * pulse)
        painter.setBrush(QBrush(QColor(255, 50, 50, dot_alpha)))
        painter.drawEllipse(QPointF(outer.right() - 16, outer.top() + 16), 4, 4)

        # "LIVE" text
        painter.setPen(QPen(QColor(255, 50, 50, dot_alpha)))
        painter.setFont(QFont("Consolas", 8, QFont.Bold))
        painter.drawText(QRectF(outer.right() - 50, outer.top() + 8, 28, 16),
                         Qt.AlignRight, "LIVE")

        painter.end()


# ──────────────────────────────────────────────
#  Main Window
# ──────────────────────────────────────────────

class MainWindow(QMainWindow):
    """Root application window — wires all modules together."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(cfg.WINDOW_TITLE)
        self.setStyleSheet(f"background-color: rgb{cfg.colors.BG_PRIMARY};")

        central = QWidget()
        self.setCentralWidget(central)

        # ── Controller ──
        self._controller = DomainController(parent=self)

        # ── Animation canvas ──
        self._canvas = AnimationCanvas(self._controller, central)

        # ── Webcam ──
        self._webcam = WebcamWidget(central)

        # ── Status HUD ──
        self._status = QLabel("SCANNING FOR CURSED ENERGY...", central)
        self._status.setAlignment(Qt.AlignCenter)
        self._apply_status_style("idle")

        # ── FPS counter ──
        self._fps_label = QLabel("", central)
        self._fps_label.setStyleSheet(f"""
            QLabel {{
                color: rgba{cfg.colors.FPS_TEXT};
                font-family: 'Consolas', monospace;
                font-size: 10px;
                background: transparent;
            }}
        """)

        # ── Hand tracker (ML thread) ──
        self._tracker = HandTracker(parent=self)
        self._tracker.frame_ready.connect(self._on_frame)
        self._tracker.gesture_detected.connect(self._controller.on_gesture_detected)
        self._tracker.gesture_lost.connect(self._controller.on_gesture_lost)
        self._tracker.start()

        # ── Render loop ──
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(cfg.timing.RENDER_INTERVAL_MS)

        # ── FPS tracking ──
        self._frame_count = 0
        self._fps_time = time.time()

        self.showFullScreen()

    # ──────────────────────────────────────────────
    #  Layout
    # ──────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        w, h = self.width(), self.height()
        self._canvas.setGeometry(0, 0, w, h)
        self._webcam.move(w - self._webcam.width() - 20, 20)
        self._status.setGeometry(0, h - 80, w, 40)
        self._fps_label.setGeometry(16, 16, 100, 16)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_F:
            if self.isFullScreen():
                self.showNormal()
                self.resize(1280, 720)
            else:
                self.showFullScreen()

    def closeEvent(self, event) -> None:
        self._tracker.stop()
        event.accept()

    # ──────────────────────────────────────────────
    #  Signal handlers
    # ──────────────────────────────────────────────

    def _on_frame(self, q_image: QImage) -> None:
        self._webcam.set_frame(q_image)

    # ──────────────────────────────────────────────
    #  Render tick
    # ──────────────────────────────────────────────

    def _tick(self) -> None:
        self._controller.tick()

        state = self._controller.state
        domain = self._controller.domain_type
        progress = self._controller.progress

        # ── Status text ──
        if state == State.IDLE:
            self._status.setText("SCANNING FOR CURSED ENERGY...")
            self._apply_status_style("idle")
            self._webcam.set_glow(qcolor(cfg.colors.WEBCAM_BORDER_IDLE))

        elif state == State.CONFIRMING:
            self._status.setText("CURSED ENERGY DETECTED...")
            gesture = self._controller.confirm_gesture
            glow = qcolor(cfg.colors.GOJO_ACCENT, 180) if gesture == "gojo" \
                else qcolor(cfg.colors.SUKUNA_ACCENT, 180)
            self._webcam.set_glow(glow)
            self._apply_status_style("confirm")

        elif state in (State.ACTIVATING, State.ACTIVE):
            if domain == "gojo":
                self._status.setText("領域展開  —  UNLIMITED VOID")
                self._apply_status_style("gojo")
                self._webcam.set_glow(qcolor(cfg.colors.GOJO_CORE, 240))
            else:
                self._status.setText("領域展開  —  MALEVOLENT SHRINE")
                self._apply_status_style("sukuna")
                self._webcam.set_glow(qcolor(cfg.colors.SUKUNA_CORE, 240))

        elif state == State.FADING:
            pass  # keep last text, it fades with the animation

        # ── Screen shake ──
        sx, sy = self._canvas.shake_offset
        self._canvas.move(int(sx), int(sy))

        # ── Repaint ──
        self._canvas.update()

        # ── FPS ──
        self._frame_count += 1
        now = time.time()
        if now - self._fps_time >= 1.0:
            fps = self._frame_count / (now - self._fps_time)
            self._fps_label.setText(f"FPS {fps:.0f}")
            self._frame_count = 0
            self._fps_time = now

    # ──────────────────────────────────────────────
    #  Style helpers
    # ──────────────────────────────────────────────

    def _apply_status_style(self, mode: str) -> None:
        styles = {
            "idle": f"""QLabel {{
                color: rgba{cfg.colors.TEXT_IDLE};
                font-family: 'Segoe UI', 'Consolas', monospace;
                font-size: {cfg.effects.STATUS_FONT_SIZE}px;
                font-weight: bold; letter-spacing: 5px;
                background: transparent;
            }}""",
            "confirm": f"""QLabel {{
                color: rgba{cfg.colors.TEXT_CONFIRM};
                font-family: 'Segoe UI', monospace;
                font-size: {cfg.effects.STATUS_FONT_SIZE}px;
                font-weight: bold; letter-spacing: 4px;
                background: transparent;
            }}""",
            "gojo": f"""QLabel {{
                color: rgba({cfg.colors.GOJO_TEXT[0]}, {cfg.colors.GOJO_TEXT[1]}, {cfg.colors.GOJO_TEXT[2]}, 240);
                font-family: 'Segoe UI', monospace;
                font-size: 18px; font-weight: bold; letter-spacing: 6px;
                background: transparent;
            }}""",
            "sukuna": f"""QLabel {{
                color: rgba({cfg.colors.SUKUNA_TEXT[0]}, {cfg.colors.SUKUNA_TEXT[1]}, {cfg.colors.SUKUNA_TEXT[2]}, 240);
                font-family: 'Segoe UI', monospace;
                font-size: 18px; font-weight: bold; letter-spacing: 6px;
                background: transparent;
            }}""",
        }
        self._status.setStyleSheet(styles.get(mode, styles["idle"]))
