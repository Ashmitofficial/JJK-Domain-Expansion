"""
Centralized Configuration — Every magic number, color, and timing in one place.

Import this anywhere:  from config import cfg
"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class Colors:
    """All application colors as (R, G, B) or (R, G, B, A) tuples."""

    # ── Background ──
    BG_PRIMARY: Tuple[int, ...] = (6, 6, 12)
    BG_VIGNETTE: Tuple[int, ...] = (0, 0, 0, 180)

    # ── Gojo Palette ──
    GOJO_CORE: Tuple[int, ...] = (138, 43, 226)
    GOJO_GLOW: Tuple[int, ...] = (100, 60, 255, 120)
    GOJO_ACCENT: Tuple[int, ...] = (180, 140, 255)
    GOJO_PARTICLE: Tuple[int, ...] = (160, 120, 255)
    GOJO_RING: Tuple[int, ...] = (180, 140, 255)
    GOJO_OVERLAY: Tuple[int, ...] = (60, 0, 120)
    GOJO_TEXT: Tuple[int, ...] = (200, 170, 255)

    # ── Sukuna Palette ──
    SUKUNA_CORE: Tuple[int, ...] = (220, 20, 20)
    SUKUNA_GLOW: Tuple[int, ...] = (255, 40, 40, 100)
    SUKUNA_ACCENT: Tuple[int, ...] = (255, 80, 60)
    SUKUNA_PARTICLE: Tuple[int, ...] = (255, 60, 30)
    SUKUNA_RING: Tuple[int, ...] = (255, 50, 50)
    SUKUNA_OVERLAY: Tuple[int, ...] = (120, 0, 0)
    SUKUNA_TEXT: Tuple[int, ...] = (255, 130, 130)
    SUKUNA_SLASH: Tuple[int, ...] = (255, 70, 70)

    # ── UI Chrome ──
    TEXT_IDLE: Tuple[int, ...] = (120, 120, 150, 200)
    TEXT_CONFIRM: Tuple[int, ...] = (180, 180, 200, 230)
    WEBCAM_BORDER_IDLE: Tuple[int, ...] = (60, 60, 80, 100)
    WEBCAM_BG: Tuple[int, ...] = (10, 10, 18)
    FPS_TEXT: Tuple[int, ...] = (50, 50, 70, 160)
    AMBIENT_PARTICLE: Tuple[int, ...] = (80, 80, 120, 40)
    GRID_LINE: Tuple[int, ...] = (30, 30, 50, 15)
    CONFIRM_RING: Tuple[int, ...] = (200, 200, 230, 200)
    FLASH_WHITE: Tuple[int, ...] = (255, 255, 255)
    FLASH_RED: Tuple[int, ...] = (139, 0, 0)


@dataclass(frozen=True)
class Timing:
    """All durations in seconds."""

    CONFIRM_HOLD: float = 0.5           # gesture must be held this long
    ACTIVATE_WINDUP: float = 0.8        # wind-up animation before full activation
    MAX_ACTIVE: float = 8.0             # auto-fade timeout
    FADE_OUT: float = 1.2               # fade-out duration
    COOLDOWN: float = 3.0               # lockout after domain ends
    FLASH_DURATION: float = 0.15        # activation flash
    SLASH_LIFETIME: float = 0.25        # sukuna slash line duration
    SLASH_INTERVAL: float = 0.08        # time between new slashes
    TYPEWRITER_SPEED: float = 0.04      # seconds per character reveal
    RENDER_INTERVAL_MS: int = 16        # ~60 FPS
    STATUS_POLL_MS: int = 100           # status text update frequency


@dataclass(frozen=True)
class Camera:
    """Camera and ML pipeline settings."""

    WIDTH: int = 320
    HEIGHT: int = 240
    SKIP_FRAMES: int = 2                # process ML every Nth frame
    CONFIDENCE_THRESHOLD: float = 0.95
    MAX_HANDS: int = 2
    DETECTION_CONFIDENCE: float = 0.8
    TRACKING_CONFIDENCE: float = 0.6


@dataclass(frozen=True)
class Layout:
    """UI dimensions and spacing."""

    WEBCAM_W: int = 240
    WEBCAM_H: int = 180
    WEBCAM_PADDING: int = 24
    WEBCAM_BORDER_RADIUS: int = 14
    WEBCAM_BORDER_WIDTH: float = 2.5
    WEBCAM_GLOW_WIDTH: float = 8.0


@dataclass(frozen=True)
class Particles:
    """Particle system tuning."""

    # ── Ambient (idle state) ──
    AMBIENT_COUNT: int = 40
    AMBIENT_SPEED: Tuple[float, float] = (5.0, 20.0)
    AMBIENT_SIZE: Tuple[float, float] = (1.0, 2.5)
    AMBIENT_DECAY: Tuple[float, float] = (0.001, 0.004)

    # ── Domain particles ──
    DOMAIN_COUNT: int = 120
    DOMAIN_MIN_ALIVE: int = 70
    GOJO_SPEED: Tuple[float, float] = (30.0, 80.0)
    SUKUNA_SPEED: Tuple[float, float] = (80.0, 250.0)
    RESPAWN_SPEED_GOJO: Tuple[float, float] = (30.0, 80.0)
    RESPAWN_SPEED_SUKUNA: Tuple[float, float] = (60.0, 180.0)

    # ── Ring effects ──
    GOJO_RINGS: int = 5
    SUKUNA_RINGS: int = 3
    GOJO_RING_SPEED: float = 0.6
    SUKUNA_RING_SPEED: float = 0.8


@dataclass(frozen=True)
class Effects:
    """Visual effect intensities."""

    SCREEN_SHAKE_MAX: float = 5.0
    VIGNETTE_STRENGTH: float = 0.7
    OVERLAY_MAX_ALPHA: int = 50
    GLOW_RADIUS_FACTOR: float = 0.45    # fraction of screen diagonal
    TITLE_Y_POS: float = 0.73           # fraction from top
    KANJI_Y_POS: float = 0.38           # fraction from top
    KANJI_FONT_SIZE: int = 72
    TITLE_FONT_SIZE: int = 26
    STATUS_FONT_SIZE: int = 15


@dataclass(frozen=True)
class AppConfig:
    """Root configuration object."""

    colors: Colors = field(default_factory=Colors)
    timing: Timing = field(default_factory=Timing)
    camera: Camera = field(default_factory=Camera)
    layout: Layout = field(default_factory=Layout)
    particles: Particles = field(default_factory=Particles)
    effects: Effects = field(default_factory=Effects)

    WINDOW_TITLE: str = "JJK Domain Expansion"
    MODEL_PATH: str = "domain_model.h5"
    CLASSES_PATH: str = "classes.npy"
    ASSETS_DIR: str = "assets"

    # ── Domain metadata ──
    DOMAINS: dict = field(default_factory=lambda: {
        "gojo": {
            "kanji": "無量空処",
            "title": "DOMAIN EXPANSION",
            "subtitle": "UNLIMITED VOID",
            "sound": "gojo_activate.wav",
        },
        "sukuna": {
            "kanji": "伏魔御廚子",
            "title": "DOMAIN EXPANSION",
            "subtitle": "MALEVOLENT SHRINE",
            "sound": "sukuna_activate.wav",
        },
    })


# ── Singleton ──
cfg = AppConfig()
