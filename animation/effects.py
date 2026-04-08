"""
Procedural Visual Effects Engine
─────────────────────────────────
Renders all domain expansion visuals via QPainter.
Uses time-based animation for frame-rate independence.

Architecture:
  BaseEffect       → abstract interface (activate / render / reset)
  GojoEffect       → purple void: inward particles, pulsing rings, radial glow
  SukunaEffect     → red shrine: outward burst, slash lines, shockwaves, shake
  AmbientRenderer  → idle-state floating particles + subtle grid
  OverlayRenderer  → vignette, flash, color grading, domain titles
"""

from __future__ import annotations

import math
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import (
    QColor, QPainter, QPen, QBrush, QRadialGradient,
    QLinearGradient, QFont, QConicalGradient,
)

from config import cfg

# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────

def qcolor(rgba: Tuple[int, ...], alpha_override: Optional[int] = None) -> QColor:
    """Create QColor from config tuple, with optional alpha override."""
    r, g, b = rgba[0], rgba[1], rgba[2]
    a = alpha_override if alpha_override is not None else (rgba[3] if len(rgba) > 3 else 255)
    return QColor(r, g, b, a)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


NO_PEN = QPen(QColor(0, 0, 0, 0))


# ──────────────────────────────────────────────
#  Particle
# ──────────────────────────────────────────────

@dataclass
class Particle:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    life: float = 1.0
    decay: float = 0.01
    size: float = 3.0
    r: int = 255
    g: int = 255
    b: int = 255
    a: int = 255


# ──────────────────────────────────────────────
#  Base Effect Interface
# ──────────────────────────────────────────────

class BaseEffect(ABC):
    """All domain effects implement this interface."""

    @abstractmethod
    def activate(self, cx: float, cy: float, w: float, h: float) -> None:
        """Called once when domain activation begins."""

    @abstractmethod
    def render(self, painter: QPainter, cx: float, cy: float,
               w: float, h: float, progress: float, dt: float) -> None:
        """Paint one frame. progress: 0→1 (activation) or 1→0 (fading)."""

    @abstractmethod
    def reset(self) -> None:
        """Clean up all state."""

    @property
    def shake_offset(self) -> Tuple[float, float]:
        return (0.0, 0.0)


# ──────────────────────────────────────────────
#  Gojo — Unlimited Void
# ──────────────────────────────────────────────

class GojoEffect(BaseEffect):
    """
    Purple void: concentric pulsing rings contract inward,
    particles drift toward a central singularity,
    deep indigo radial glow pulses.
    """

    def __init__(self):
        self._particles: List[Particle] = []
        self._start_time: float = 0.0

    def activate(self, cx: float, cy: float, w: float, h: float) -> None:
        self._start_time = time.time()
        self._particles.clear()

        max_r = math.hypot(w, h) * 0.5
        pcfg = cfg.particles

        for _ in range(pcfg.DOMAIN_COUNT):
            angle = random.uniform(0, math.tau)
            dist = random.uniform(max_r * 0.3, max_r)
            speed = random.uniform(*pcfg.GOJO_SPEED)
            self._particles.append(Particle(
                x=cx + math.cos(angle) * dist,
                y=cy + math.sin(angle) * dist,
                vx=-math.cos(angle) * speed,
                vy=-math.sin(angle) * speed,
                life=1.0,
                decay=random.uniform(0.003, 0.012),
                size=random.uniform(1.5, 4.5),
                r=random.randint(120, 200),
                g=random.randint(80, 160),
                b=255,
                a=random.randint(150, 255),
            ))

    def render(self, painter: QPainter, cx: float, cy: float,
               w: float, h: float, progress: float, dt: float) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        elapsed = time.time() - self._start_time if self._start_time else 0
        pcfg = cfg.particles
        ecfg = cfg.effects

        # ── 1. Radial glow ──
        max_r = math.hypot(w, h) * ecfg.GLOW_RADIUS_FACTOR * progress
        if max_r > 1:
            grad = QRadialGradient(cx, cy, max_r)
            grad.setColorAt(0.0, qcolor(cfg.colors.GOJO_CORE, int(140 * progress)))
            grad.setColorAt(0.4, qcolor(cfg.colors.GOJO_GLOW, int(70 * progress)))
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(NO_PEN)
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(QPointF(cx, cy), max_r, max_r)

        # ── 2. Concentric pulsing rings ──
        for i in range(pcfg.GOJO_RINGS):
            phase = (elapsed * pcfg.GOJO_RING_SPEED + i * 0.2) % 1.0
            ring_r = max_r * phase * progress
            alpha = int(160 * (1.0 - phase) * progress)
            thickness = lerp(2.5, 0.5, phase)
            pen = QPen(qcolor(cfg.colors.GOJO_RING, alpha))
            pen.setWidthF(thickness)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
            if ring_r > 0:
                painter.drawEllipse(QPointF(cx, cy), ring_r, ring_r)

        # ── 3. Particles (inward drift) ──
        alive: List[Particle] = []
        for p in self._particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= p.decay
            if p.life > 0:
                a = int(p.a * p.life * progress)
                painter.setPen(NO_PEN)
                painter.setBrush(QBrush(QColor(p.r, p.g, p.b, a)))
                painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)
                alive.append(p)
        self._particles = alive

        # ── 4. Respawn depleted particles ──
        while len(self._particles) < pcfg.DOMAIN_MIN_ALIVE:
            angle = random.uniform(0, math.tau)
            dist = max_r + random.uniform(50, 250)
            speed = random.uniform(*pcfg.RESPAWN_SPEED_GOJO)
            self._particles.append(Particle(
                x=cx + math.cos(angle) * dist,
                y=cy + math.sin(angle) * dist,
                vx=-math.cos(angle) * speed,
                vy=-math.sin(angle) * speed,
                life=1.0,
                decay=random.uniform(0.005, 0.018),
                size=random.uniform(1.5, 4.0),
                r=random.randint(120, 200),
                g=random.randint(80, 160),
                b=255,
                a=random.randint(150, 255),
            ))

    def reset(self) -> None:
        self._particles.clear()
        self._start_time = 0.0


# ──────────────────────────────────────────────
#  Sukuna — Malevolent Shrine
# ──────────────────────────────────────────────

class SukunaEffect(BaseEffect):
    """
    Red fury: outward particle burst, expanding shockwaves,
    random diagonal slash lines, screen shake.
    """

    def __init__(self):
        self._particles: List[Particle] = []
        self._slashes: List[dict] = []
        self._start_time: float = 0.0
        self._shake: Tuple[float, float] = (0.0, 0.0)
        self._last_slash: float = 0.0

    @property
    def shake_offset(self) -> Tuple[float, float]:
        return self._shake

    def activate(self, cx: float, cy: float, w: float, h: float) -> None:
        self._start_time = time.time()
        self._particles.clear()
        self._slashes.clear()
        pcfg = cfg.particles

        for _ in range(pcfg.DOMAIN_COUNT):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(*pcfg.SUKUNA_SPEED)
            self._particles.append(Particle(
                x=cx, y=cy,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=1.0,
                decay=random.uniform(0.008, 0.022),
                size=random.uniform(2.0, 5.5),
                r=255,
                g=random.randint(20, 100),
                b=random.randint(0, 30),
                a=random.randint(180, 255),
            ))

    def render(self, painter: QPainter, cx: float, cy: float,
               w: float, h: float, progress: float, dt: float) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        now = time.time()
        elapsed = now - self._start_time if self._start_time else 0
        pcfg = cfg.particles
        ecfg = cfg.effects
        tcfg = cfg.timing

        # ── 1. Screen shake ──
        if progress > 0.3:
            s = ecfg.SCREEN_SHAKE_MAX * progress
            self._shake = (random.uniform(-s, s), random.uniform(-s, s))
        else:
            self._shake = (0.0, 0.0)

        # ── 2. Shockwave rings ──
        max_r = math.hypot(w, h) * 0.5
        for i in range(pcfg.SUKUNA_RINGS):
            phase = (elapsed * pcfg.SUKUNA_RING_SPEED + i * 0.33) % 1.0
            ring_r = max_r * phase * progress
            alpha = int(200 * (1.0 - phase) * progress)
            thickness = lerp(3.5, 0.8, phase)
            pen = QPen(qcolor(cfg.colors.SUKUNA_RING, alpha))
            pen.setWidthF(thickness)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
            if ring_r > 0:
                painter.drawEllipse(QPointF(cx, cy), ring_r, ring_r)

        # ── 3. Radial crimson glow ──
        glow_r = max_r * ecfg.GLOW_RADIUS_FACTOR * progress
        if glow_r > 1:
            grad = QRadialGradient(cx, cy, glow_r)
            grad.setColorAt(0.0, qcolor(cfg.colors.SUKUNA_CORE, int(100 * progress)))
            grad.setColorAt(0.4, qcolor(cfg.colors.SUKUNA_GLOW, int(50 * progress)))
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(NO_PEN)
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(QPointF(cx, cy), glow_r, glow_r)

        # ── 4. Slash lines (Cleave / Dismantle) ──
        if progress > 0.3 and now - self._last_slash > tcfg.SLASH_INTERVAL:
            self._last_slash = now
            self._slashes.append({
                "x1": random.uniform(w * 0.1, w * 0.9),
                "y1": random.uniform(h * 0.1, h * 0.9),
                "x2": random.uniform(w * 0.1, w * 0.9),
                "y2": random.uniform(h * 0.1, h * 0.9),
                "born": now,
            })

        alive_slashes = []
        for s in self._slashes:
            age = now - s["born"]
            if age < tcfg.SLASH_LIFETIME:
                t = age / tcfg.SLASH_LIFETIME
                alpha = int(255 * (1.0 - t))
                pen = QPen(qcolor(cfg.colors.SUKUNA_SLASH, alpha))
                pen.setWidthF(lerp(3.0, 0.5, t))
                painter.setPen(pen)
                painter.drawLine(QPointF(s["x1"], s["y1"]), QPointF(s["x2"], s["y2"]))
                alive_slashes.append(s)
        self._slashes = alive_slashes

        # ── 5. Particles (outward burst) ──
        alive: List[Particle] = []
        for p in self._particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vx *= 0.985
            p.vy *= 0.985
            p.life -= p.decay
            if p.life > 0:
                a = int(p.a * p.life * progress)
                painter.setPen(NO_PEN)
                painter.setBrush(QBrush(QColor(p.r, p.g, p.b, a)))
                painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)
                alive.append(p)
        self._particles = alive

        # ── 6. Respawn ──
        while len(self._particles) < pcfg.DOMAIN_MIN_ALIVE:
            angle = random.uniform(0, math.tau)
            speed = random.uniform(*pcfg.RESPAWN_SPEED_SUKUNA)
            self._particles.append(Particle(
                x=cx + random.uniform(-40, 40),
                y=cy + random.uniform(-40, 40),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=1.0,
                decay=random.uniform(0.012, 0.028),
                size=random.uniform(2.0, 5.0),
                r=255,
                g=random.randint(20, 100),
                b=random.randint(0, 30),
                a=random.randint(180, 255),
            ))

    def reset(self) -> None:
        self._particles.clear()
        self._slashes.clear()
        self._start_time = 0.0
        self._shake = (0.0, 0.0)


# ──────────────────────────────────────────────
#  Ambient Renderer (idle-state atmosphere)
# ──────────────────────────────────────────────

class AmbientRenderer:
    """
    Subtle floating particles + faint grid lines even when idle.
    Makes the app feel alive instead of dead-black.
    """

    def __init__(self):
        self._particles: List[Particle] = []
        self._initialized = False

    def render(self, painter: QPainter, w: float, h: float, dt: float) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        pcfg = cfg.particles

        # ── Initialize on first call ──
        if not self._initialized:
            self._initialized = True
            for _ in range(pcfg.AMBIENT_COUNT):
                self._spawn(w, h)

        # ── Faint grid lines ──
        grid_pen = QPen(qcolor(cfg.colors.GRID_LINE))
        grid_pen.setWidthF(0.5)
        painter.setPen(grid_pen)
        spacing = 80
        for x in range(0, int(w) + spacing, spacing):
            painter.drawLine(QPointF(x, 0), QPointF(x, h))
        for y in range(0, int(h) + spacing, spacing):
            painter.drawLine(QPointF(0, y), QPointF(w, y))

        # ── Floating particles ──
        alive: List[Particle] = []
        for p in self._particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= p.decay
            if p.life > 0:
                a = int(p.a * p.life)
                painter.setPen(NO_PEN)
                painter.setBrush(QBrush(QColor(p.r, p.g, p.b, a)))
                painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)
                alive.append(p)

        self._particles = alive
        while len(self._particles) < pcfg.AMBIENT_COUNT:
            self._spawn(w, h)

    def _spawn(self, w: float, h: float) -> None:
        pcfg = cfg.particles
        c = cfg.colors.AMBIENT_PARTICLE
        self._particles.append(Particle(
            x=random.uniform(0, w),
            y=random.uniform(0, h),
            vx=random.uniform(-1, 1) * random.uniform(*pcfg.AMBIENT_SPEED),
            vy=random.uniform(-1, 1) * random.uniform(*pcfg.AMBIENT_SPEED),
            life=1.0,
            decay=random.uniform(*pcfg.AMBIENT_DECAY),
            size=random.uniform(*pcfg.AMBIENT_SIZE),
            r=c[0], g=c[1], b=c[2], a=c[3] if len(c) > 3 else 40,
        ))


# ──────────────────────────────────────────────
#  Overlay Renderer (vignette, flash, titles)
# ──────────────────────────────────────────────

class OverlayRenderer:
    """
    Screen-level effects layered on top of everything:
    vignette, activation flash, color grading, domain titles.
    """

    def __init__(self):
        self._typewriter_start: float = 0.0
        self._last_domain: str = ""

    def render_vignette(self, painter: QPainter, w: float, h: float) -> None:
        """Dark edges → bright center vignette."""
        cx, cy = w / 2, h / 2
        radius = math.hypot(w, h) * 0.55
        grad = QRadialGradient(cx, cy, radius)
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.6, QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, qcolor(cfg.colors.BG_VIGNETTE))
        painter.setPen(NO_PEN)
        painter.setBrush(QBrush(grad))
        painter.drawRect(QRectF(0, 0, w, h))

    def render_flash(self, painter: QPainter, w: float, h: float,
                     domain: str, elapsed: float) -> None:
        """Brief activation flash."""
        dur = cfg.timing.FLASH_DURATION
        if elapsed >= dur:
            return
        t = elapsed / dur
        alpha = int(220 * (1.0 - t))
        color = cfg.colors.FLASH_WHITE if domain == "gojo" else cfg.colors.FLASH_RED
        painter.fillRect(QRectF(0, 0, w, h), qcolor(color, alpha))

    def render_color_grading(self, painter: QPainter, w: float, h: float,
                             domain: str, progress: float) -> None:
        """Subtle full-screen color tint."""
        ecfg = cfg.effects
        alpha = int(ecfg.OVERLAY_MAX_ALPHA * progress)
        color = cfg.colors.GOJO_OVERLAY if domain == "gojo" else cfg.colors.SUKUNA_OVERLAY
        painter.fillRect(QRectF(0, 0, w, h), qcolor(color, alpha))

    def render_domain_title(self, painter: QPainter, w: float, h: float,
                            domain: str, progress: float) -> None:
        """
        Kanji calligraphy (large, center) + typewriter subtitle.
        """
        if domain not in cfg.DOMAINS or progress < 0.15:
            return

        meta = cfg.DOMAINS[domain]
        ecfg = cfg.effects
        is_gojo = domain == "gojo"
        text_color = cfg.colors.GOJO_TEXT if is_gojo else cfg.colors.SUKUNA_TEXT
        glow_color = cfg.colors.GOJO_CORE if is_gojo else cfg.colors.SUKUNA_CORE

        # Track typewriter resets
        if domain != self._last_domain:
            self._last_domain = domain
            self._typewriter_start = time.time()

        # ── Fade multiplier ──
        fade = min(1.0, (progress - 0.15) / 0.25)

        # ── Large kanji ──
        kanji_alpha = int(200 * fade * progress)
        kanji_font = QFont("Yu Gothic", ecfg.KANJI_FONT_SIZE, QFont.Bold)
        if not kanji_font.exactMatch():
            kanji_font = QFont("Segoe UI", ecfg.KANJI_FONT_SIZE, QFont.Bold)
        painter.setFont(kanji_font)

        kanji_rect = QRectF(0, h * ecfg.KANJI_Y_POS, w, ecfg.KANJI_FONT_SIZE + 20)

        # Glow passes
        painter.setPen(QPen(qcolor(glow_color, kanji_alpha // 4)))
        for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2)]:
            painter.drawText(kanji_rect.adjusted(dx, dy, 0, 0),
                             Qt.AlignHCenter | Qt.AlignTop, meta["kanji"])

        # Crisp kanji
        painter.setPen(QPen(qcolor(text_color, kanji_alpha)))
        painter.drawText(kanji_rect, Qt.AlignHCenter | Qt.AlignTop, meta["kanji"])

        # ── Typewriter subtitle ──
        elapsed_tw = time.time() - self._typewriter_start
        full_text = f'{meta["title"]}:  {meta["subtitle"]}'
        chars_visible = min(len(full_text),
                            int(elapsed_tw / cfg.timing.TYPEWRITER_SPEED))
        visible_text = full_text[:chars_visible]

        if visible_text:
            title_alpha = int(240 * fade * progress)
            title_font = QFont("Segoe UI", ecfg.TITLE_FONT_SIZE, QFont.Bold)
            title_font.setLetterSpacing(QFont.AbsoluteSpacing, 5)
            painter.setFont(title_font)

            title_rect = QRectF(0, h * ecfg.TITLE_Y_POS, w, 50)

            # Glow
            painter.setPen(QPen(qcolor(glow_color, title_alpha // 5)))
            for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                painter.drawText(title_rect.adjusted(dx, dy, 0, 0),
                                 Qt.AlignHCenter | Qt.AlignTop, visible_text)

            # Crisp
            painter.setPen(QPen(qcolor(text_color, title_alpha)))
            painter.drawText(title_rect, Qt.AlignHCenter | Qt.AlignTop, visible_text)

            # Blinking cursor
            if chars_visible < len(full_text):
                cursor_text = visible_text + "▌"
                painter.drawText(title_rect, Qt.AlignHCenter | Qt.AlignTop, cursor_text)

    def render_confirm_ring(self, painter: QPainter, cx: float, cy: float,
                            progress: float, domain_hint: str) -> None:
        """
        Circular progress indicator during gesture confirmation.
        A ring that fills clockwise around the center.
        """
        if progress <= 0:
            return

        radius = 60
        is_gojo = domain_hint == "gojo"
        color = cfg.colors.GOJO_ACCENT if is_gojo else cfg.colors.SUKUNA_ACCENT

        # Background ring (dim)
        pen = QPen(qcolor(color, 40))
        pen.setWidthF(3)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # Progress arc
        arc_pen = QPen(qcolor(color, 220))
        arc_pen.setWidthF(3.5)
        arc_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(arc_pen)

        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        start_angle = 90 * 16  # 12 o'clock
        span_angle = int(-progress * 360 * 16)  # clockwise
        painter.drawArc(rect, start_angle, span_angle)

        # Center percentage
        pct = int(progress * 100)
        painter.setPen(QPen(qcolor(color, 200)))
        painter.setFont(QFont("Consolas", 14, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, f"{pct}%")
