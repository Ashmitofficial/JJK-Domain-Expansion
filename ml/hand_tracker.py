"""
Hand Tracker — Background QThread for camera capture + ML inference.

Architecture:
  ┌─────────────────────────────────────────────────┐
  │               HandTracker (QThread)             │
  │                                                 │
  │  Camera (320×240) → flip → RGB                  │
  │       ↓                                         │
  │  MediaPipe Hands (every Nth frame)              │
  │       ↓                                         │
  │  Wrist-normalized 126-dim vector                │
  │       ↓                                         │
  │  TF model(input, training=False)                │
  │       ↓                                         │
  │  emit frame_ready(QImage)                       │
  │  emit gesture_detected("gojo", 0.98)            │
  │  emit gesture_lost()                            │
  └─────────────────────────────────────────────────┘

Emits Qt signals only — never touches UI directly.
"""

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
import mediapipe as mp
import tensorflow as tf
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

from config import cfg


class HandTracker(QThread):
    """Background thread: captures camera, runs hand detection, emits results."""

    frame_ready = pyqtSignal(QImage)
    gesture_detected = pyqtSignal(str, float)   # (label, confidence)
    gesture_lost = pyqtSignal()

    def __init__(self, parent: Optional[object] = None):
        super().__init__(parent)
        self._running: bool = False

        # ── Load ML Model ──
        self._model = tf.keras.models.load_model(cfg.MODEL_PATH)
        self._classes = np.load(cfg.CLASSES_PATH, allow_pickle=True)

        # ── MediaPipe ──
        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            max_num_hands=cfg.camera.MAX_HANDS,
            min_detection_confidence=cfg.camera.DETECTION_CONFIDENCE,
            min_tracking_confidence=cfg.camera.TRACKING_CONFIDENCE,
        )

    # ──────────────────────────────────────────────
    #  Thread lifecycle
    # ──────────────────────────────────────────────

    def run(self) -> None:
        """Main loop — captures frames and runs inference off the UI thread."""
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.camera.WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.camera.HEIGHT)

        self._running = True
        frame_count = 0

        while self._running:
            ok, frame = cap.read()
            if not ok:
                continue

            frame = cv2.flip(frame, 1)
            frame_count += 1

            # Always emit video frame (smooth webcam feed)
            self._emit_frame(frame)

            # ML inference on every Nth frame only
            if frame_count % cfg.camera.SKIP_FRAMES == 0:
                self._infer(frame)

        cap.release()

    def stop(self) -> None:
        """Cleanly stop the thread."""
        self._running = False
        self.wait()

    # ──────────────────────────────────────────────
    #  Internals
    # ──────────────────────────────────────────────

    def _emit_frame(self, bgr_frame: np.ndarray) -> None:
        """Convert BGR frame → QImage and emit."""
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        q_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.frame_ready.emit(q_img.copy())

    def _infer(self, bgr_frame: np.ndarray) -> None:
        """Run MediaPipe + TF inference on a single frame."""
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb)

        if not results.multi_hand_landmarks:
            self.gesture_lost.emit()
            return

        # Build wrist-normalized 126-dim vector
        landmarks = [0.0] * 126
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            if i >= cfg.camera.MAX_HANDS:
                break
            start = i * 63
            wrist = hand_lms.landmark[0]
            for j, lm in enumerate(hand_lms.landmark):
                landmarks[start + j * 3]     = lm.x - wrist.x
                landmarks[start + j * 3 + 1] = lm.y - wrist.y
                landmarks[start + j * 3 + 2] = lm.z - wrist.z

        # TF inference (direct call — no memory leak)
        input_data = np.array([landmarks], dtype=np.float32)
        prediction = self._model(input_data, training=False).numpy()[0]
        class_idx = int(np.argmax(prediction))
        confidence = float(prediction[class_idx])

        if confidence > cfg.camera.CONFIDENCE_THRESHOLD:
            label = str(self._classes[class_idx]).lower()
            self.gesture_detected.emit(label, confidence)
        else:
            self.gesture_lost.emit()
