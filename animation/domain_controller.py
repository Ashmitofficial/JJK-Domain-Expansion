"""
Domain Controller — State machine managing domain activation lifecycle.

States:
  IDLE → CONFIRMING (0.5s hold) → ACTIVATING (0.8s windup) → ACTIVE (hold) → FADING (1.2s) → IDLE

Features:
  - Confirmation window: prevents false triggers
  - Cooldown: prevents spam after domain ends
  - Sound playback: optional, graceful degradation
  - Clean signal emission for UI updates
"""

from __future__ import annotations

import os
import time
from enum import Enum, auto
from typing import Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal

from config import cfg

# ── Optional sound support ──
try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    _SOUND_OK = True
except Exception:
    _SOUND_OK = False


class State(Enum):
    IDLE = auto()
    CONFIRMING = auto()
    ACTIVATING = auto()
    ACTIVE = auto()
    FADING = auto()


class DomainController(QObject):
    """Manages the full domain expansion lifecycle."""

    # Signal: (state_name, domain_type, progress)
    state_changed = pyqtSignal(str, str, float)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        self._state: State = State.IDLE
        self._domain: str = ""
        self._confirm_gesture: str = ""
        self._progress: float = 0.0

        # Timestamps
        self._confirm_start: float = 0.0
        self._activate_start: float = 0.0
        self._active_start: float = 0.0
        self._fade_start: float = 0.0
        self._cooldown_end: float = 0.0

        # Sound cache
        self._sounds: Dict[str, object] = {}
        self._load_sounds()

    # ──────────────────────────────────────────────
    #  Properties
    # ──────────────────────────────────────────────

    @property
    def state(self) -> State:
        return self._state

    @property
    def domain_type(self) -> str:
        return self._domain

    @property
    def progress(self) -> float:
        return self._progress

    @property
    def confirm_gesture(self) -> str:
        return self._confirm_gesture

    # ──────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────

    def on_gesture_detected(self, label: str, confidence: float) -> None:
        """Called when HandTracker emits a valid gesture."""
        now = time.time()
        t = cfg.timing

        if self._state == State.IDLE:
            if now < self._cooldown_end:
                return
            self._state = State.CONFIRMING
            self._confirm_gesture = label
            self._confirm_start = now

        elif self._state == State.CONFIRMING:
            if label != self._confirm_gesture:
                self._confirm_gesture = label
                self._confirm_start = now

    def on_gesture_lost(self) -> None:
        """Called when no valid gesture is detected."""
        if self._state == State.CONFIRMING:
            self._state = State.IDLE
            self._confirm_gesture = ""
            self._progress = 0.0

    def tick(self) -> None:
        """Advance state machine — called at ~60Hz by render timer."""
        now = time.time()
        t = cfg.timing

        if self._state == State.CONFIRMING:
            elapsed = now - self._confirm_start
            self._progress = min(elapsed / t.CONFIRM_HOLD, 1.0)
            if elapsed >= t.CONFIRM_HOLD:
                self._enter_activating(now)

        elif self._state == State.ACTIVATING:
            elapsed = now - self._activate_start
            self._progress = min(elapsed / t.ACTIVATE_WINDUP, 1.0)
            if elapsed >= t.ACTIVATE_WINDUP:
                self._state = State.ACTIVE
                self._active_start = now
                self._progress = 1.0

        elif self._state == State.ACTIVE:
            elapsed = now - self._active_start
            self._progress = 1.0
            if elapsed >= t.MAX_ACTIVE:
                self._enter_fading(now)

        elif self._state == State.FADING:
            elapsed = now - self._fade_start
            self._progress = max(1.0 - elapsed / t.FADE_OUT, 0.0)
            if elapsed >= t.FADE_OUT:
                self._enter_idle(now)

        self.state_changed.emit(self._state.name, self._domain, self._progress)

    def force_deactivate(self) -> None:
        """Immediately begin fading."""
        if self._state in (State.ACTIVATING, State.ACTIVE):
            self._enter_fading(time.time())

    # ──────────────────────────────────────────────
    #  State transitions
    # ──────────────────────────────────────────────

    def _enter_activating(self, now: float) -> None:
        self._state = State.ACTIVATING
        self._domain = self._confirm_gesture
        self._activate_start = now
        self._progress = 0.0
        self._play_sound(self._domain)

    def _enter_fading(self, now: float) -> None:
        self._state = State.FADING
        self._fade_start = now

    def _enter_idle(self, now: float) -> None:
        self._state = State.IDLE
        self._domain = ""
        self._confirm_gesture = ""
        self._progress = 0.0
        self._cooldown_end = now + cfg.timing.COOLDOWN

    # ──────────────────────────────────────────────
    #  Sound
    # ──────────────────────────────────────────────

    def _load_sounds(self) -> None:
        if not _SOUND_OK:
            return
        sounds_dir = os.path.join(cfg.ASSETS_DIR, "sounds")
        for domain_key, meta in cfg.DOMAINS.items():
            path = os.path.join(sounds_dir, meta["sound"])
            if os.path.exists(path):
                try:
                    self._sounds[domain_key] = pygame.mixer.Sound(path)
                except Exception:
                    pass

    def _play_sound(self, domain: str) -> None:
        sound = self._sounds.get(domain)
        if sound:
            try:
                sound.play()
            except Exception:
                pass
