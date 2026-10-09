"""Processus de capture et suivi vision, séparé du rendu/audio (cadrage §4.1).

Pensé pour tourner dans un ``multiprocessing.Process`` : ouvre la caméra, suit
l'embout coloré, détecte les coups, et transmet un flux de ``VisionSample`` par
file. Rien ici ne touche à pygame ni au mixeur : un souci côté vision (caméra
débranchée, calcul lent) ne bloque jamais le reste de l'application.

``track_and_detect`` est la boucle pure (image -> échantillon) : lui passer une
liste ou un générateur d'images de test, au lieu de ``camera_frames()``, permet de
la tester sans caméra. ``run_vision_process`` n'est que le point d'entrée qui la
branche sur une file de sortie.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from batterie.core.events import HitEvent, Source
from batterie.input.vision.color_tracker import ColorRange, TrackedPoint, find_marker
from batterie.input.vision.strike_detector import StrikeDetector

WORKING_WIDTH = 320


@dataclass(frozen=True)
class VisionSample:
    """Un point de télémétrie pour l'écran de débogage (une entrée par image traitée)."""

    t_ns: int
    point: TrackedPoint | None
    velocity_px_per_s: float
    fps: float
    processing_ms: float
    hit_event: HitEvent | None
    frame_preview: np.ndarray | None = None


def camera_frames(device_index: int = 0) -> Iterator[np.ndarray]:
    """Source d'images par défaut : ouvre la webcam ``device_index`` via OpenCV."""
    capture = cv2.VideoCapture(device_index)
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            yield frame
    finally:
        capture.release()


def _resize_if_needed(frame: np.ndarray, target_width: int | None) -> np.ndarray:
    if target_width is None:
        return frame
    height, width = frame.shape[:2]
    if width <= target_width:
        return frame
    scale = target_width / width
    return cv2.resize(frame, (target_width, int(height * scale)))


def track_and_detect(
    frames: Iterator[np.ndarray],
    color_range: ColorRange,
    strike_plane_y: float,
    *,
    element_id: str = "snare",
    detector: StrikeDetector | None = None,
    send_frames: bool = False,
    working_width: int | None = WORKING_WIDTH,
    now_ns: Callable[[], int] = time.perf_counter_ns,
) -> Iterator[VisionSample]:
    """Transforme un flux d'images en flux de ``VisionSample``.

    Chaque image est d'abord réduite à ``working_width`` (si fournie) : le suivi, la
    détection de coup et l'aperçu partagent ensuite le même repère de pixels, donc
    ``strike_plane_y`` et la position reçue se correspondent toujours directement à
    l'écran, quelle que soit la résolution native de la caméra.
    """
    detector = detector or StrikeDetector(strike_plane_y=strike_plane_y)
    last_point: TrackedPoint | None = None
    last_t_ns: int | None = None
    last_loop_ns: int | None = None

    for raw_frame in frames:
        start_ns = now_ns()
        frame = _resize_if_needed(raw_frame, working_width)
        point = find_marker(frame, color_range)

        velocity = 0.0
        hit_event = None
        if point is not None:
            if last_point is not None and last_t_ns is not None:
                dt_s = (start_ns - last_t_ns) / 1_000_000_000
                if dt_s > 0:
                    velocity = (point.y - last_point.y) / dt_s
            if detector.update(start_ns / 1_000_000_000, point.y):
                hit_event = HitEvent(
                    element_id=element_id, velocity=1.0, t_ns=start_ns, source=Source.VISION
                )
            last_point = point
            last_t_ns = start_ns

        fps = 0.0
        if last_loop_ns is not None:
            loop_dt_s = (start_ns - last_loop_ns) / 1_000_000_000
            if loop_dt_s > 0:
                fps = 1.0 / loop_dt_s
        last_loop_ns = start_ns

        preview = frame if send_frames else None
        processing_ms = (now_ns() - start_ns) / 1_000_000

        yield VisionSample(
            t_ns=start_ns,
            point=point,
            velocity_px_per_s=velocity,
            fps=fps,
            processing_ms=processing_ms,
            hit_event=hit_event,
            frame_preview=preview,
        )


def run_vision_process(
    queue: Any,
    color_range: ColorRange,
    strike_plane_y: float,
    *,
    element_id: str = "snare",
    send_frames: bool = False,
    frames: Iterator[np.ndarray] | None = None,
) -> None:
    """Point d'entrée du processus : boucle et pousse les échantillons sur ``queue``.

    ``frames`` permet d'injecter une source d'images de test ; par défaut, ouvre la
    webcam 0. ``queue`` n'a besoin que d'une méthode ``put`` (un vrai
    ``multiprocessing.Queue``, ou un objet compatible dans les tests).
    """
    frame_iter = frames if frames is not None else camera_frames()
    samples = track_and_detect(
        frame_iter, color_range, strike_plane_y, element_id=element_id, send_frames=send_frames
    )
    for sample in samples:
        queue.put(sample)
