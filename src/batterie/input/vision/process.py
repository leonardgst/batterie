"""Processus de capture et suivi vision, séparé du rendu/audio (cadrage §4.1).

Pensé pour tourner dans un ``multiprocessing.Process`` : ouvre la caméra, suit un ou
plusieurs embouts colorés (un par main, par exemple), détecte les coups, et transmet un
flux de ``VisionSample`` par file. Rien ici ne touche à pygame ni au mixeur : un souci
côté vision (caméra débranchée, calcul lent) ne bloque jamais le reste de l'application.

``track_markers`` est la boucle pure (image -> échantillon) : lui passer une liste ou un
générateur d'images de test, au lieu de ``camera_frames()``, permet de la tester sans
caméra. Chaque marqueur (``MarkerSpec``) a sa couleur, son plan de frappe et son propre
détecteur de coup : un coup d'une main ne bloque jamais l'anti-rebond de l'autre.
``track_and_detect`` et ``run_vision_process`` sont les raccourcis pour un seul marqueur
(baguette, pied) ; ``run_markers_process`` est le point d'entrée du processus.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from batterie.core.events import HitEvent, Source
from batterie.input.vision.color_tracker import ColorRange, TrackedPoint, find_marker
from batterie.input.vision.strike_detector import (
    DEFAULT_MIN_SPEED_PX_PER_S,
    DEFAULT_REFRACTORY_S,
    StrikeDetector,
)

WORKING_WIDTH = 320

SINGLE_MARKER_NAME = "marker"


@dataclass(frozen=True)
class MarkerSpec:
    """Un embout à suivre : sa couleur, son plan de frappe et les seuils de son détecteur."""

    name: str  # identifiant dans ``VisionSample.markers`` (« left », « right », ...)
    color_range: ColorRange
    strike_plane_y: float  # pixels, dans l'image réduite (voir WORKING_WIDTH)
    element_id: str = "snare"
    min_speed_px_per_s: float = DEFAULT_MIN_SPEED_PX_PER_S
    refractory_s: float = DEFAULT_REFRACTORY_S


@dataclass(frozen=True)
class MarkerSample:
    """Ce qu'on sait d'un embout sur une image : position, vitesse, coup éventuel."""

    point: TrackedPoint | None
    velocity_px_per_s: float
    hit_event: HitEvent | None


@dataclass(frozen=True)
class VisionSample:
    """Un point de télémétrie (une entrée par image traitée), un ``MarkerSample`` par embout.

    ``point``, ``velocity_px_per_s`` et ``hit_event`` donnent ceux du premier embout :
    pratique quand on n'en suit qu'un (baguette, pied).
    """

    t_ns: int
    markers: dict[str, MarkerSample]
    fps: float
    processing_ms: float
    frame_preview: np.ndarray | None = field(default=None, compare=False)

    def _first(self) -> MarkerSample:
        return next(iter(self.markers.values()))

    @property
    def point(self) -> TrackedPoint | None:
        return self._first().point

    @property
    def velocity_px_per_s(self) -> float:
        return self._first().velocity_px_per_s

    @property
    def hit_event(self) -> HitEvent | None:
        return self._first().hit_event

    @property
    def hit_events(self) -> list[HitEvent]:
        """Les coups de cette image, tous embouts confondus."""
        return [m.hit_event for m in self.markers.values() if m.hit_event is not None]


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


class _MarkerState:
    """Mémoire d'un embout d'une image à la suivante : détecteur, dernier point vu."""

    def __init__(self, spec: MarkerSpec, detector: StrikeDetector | None) -> None:
        self.spec = spec
        self.detector = detector or StrikeDetector(
            strike_plane_y=spec.strike_plane_y,
            min_speed_px_per_s=spec.min_speed_px_per_s,
            refractory_s=spec.refractory_s,
        )
        self.last_point: TrackedPoint | None = None
        self.last_t_ns: int | None = None

    def update(self, frame: np.ndarray, t_ns: int) -> MarkerSample:
        point = find_marker(frame, self.spec.color_range)
        velocity = 0.0
        hit_event = None
        if point is not None:
            if self.last_point is not None and self.last_t_ns is not None:
                dt_s = (t_ns - self.last_t_ns) / 1_000_000_000
                if dt_s > 0:
                    velocity = (point.y - self.last_point.y) / dt_s
            if self.detector.update(t_ns / 1_000_000_000, point.y):
                hit_event = HitEvent(
                    element_id=self.spec.element_id,
                    velocity=1.0,
                    t_ns=t_ns,
                    source=Source.VISION,
                )
            self.last_point = point
            self.last_t_ns = t_ns
        return MarkerSample(point=point, velocity_px_per_s=velocity, hit_event=hit_event)


def track_markers(
    frames: Iterator[np.ndarray],
    specs: Sequence[MarkerSpec],
    *,
    detectors: dict[str, StrikeDetector] | None = None,
    mirror: bool = False,
    send_frames: bool = False,
    working_width: int | None = WORKING_WIDTH,
    now_ns: Callable[[], int] = time.perf_counter_ns,
) -> Iterator[VisionSample]:
    """Transforme un flux d'images en flux de ``VisionSample``, un échantillon par image.

    Chaque image est d'abord réduite à ``working_width`` (si fournie) : le suivi, la
    détection de coup et l'aperçu partagent ensuite le même repère de pixels, donc les
    ``strike_plane_y`` et les positions reçues se correspondent toujours directement à
    l'écran, quelle que soit la résolution native de la caméra.

    ``mirror`` retourne l'image gauche-droite après la réduction : face à la caméra, ta
    main gauche apparaît alors à gauche, comme les éléments sur l'écran du kit.
    ``detectors`` permet d'injecter un détecteur par nom d'embout (tests).
    """
    if not specs:
        raise ValueError("track_markers a besoin d'au moins un marqueur")
    names = [spec.name for spec in specs]
    if len(set(names)) != len(names):
        raise ValueError(f"noms de marqueurs en double : {names}")

    detectors = detectors or {}
    states = [_MarkerState(spec, detectors.get(spec.name)) for spec in specs]
    last_loop_ns: int | None = None

    for raw_frame in frames:
        start_ns = now_ns()
        frame = _resize_if_needed(raw_frame, working_width)
        if mirror:
            frame = cv2.flip(frame, 1)

        markers = {state.spec.name: state.update(frame, start_ns) for state in states}

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
            markers=markers,
            fps=fps,
            processing_ms=processing_ms,
            frame_preview=preview,
        )


def track_and_detect(
    frames: Iterator[np.ndarray],
    color_range: ColorRange,
    strike_plane_y: float,
    *,
    element_id: str = "snare",
    detector: StrikeDetector | None = None,
    min_speed_px_per_s: float = DEFAULT_MIN_SPEED_PX_PER_S,
    refractory_s: float = DEFAULT_REFRACTORY_S,
    send_frames: bool = False,
    working_width: int | None = WORKING_WIDTH,
    now_ns: Callable[[], int] = time.perf_counter_ns,
) -> Iterator[VisionSample]:
    """Raccourci de ``track_markers`` pour un seul embout (baguette, pied).

    ``min_speed_px_per_s`` et ``refractory_s`` règlent le détecteur de coup (ils
    servent à le construire, et sont ignorés si ``detector`` est fourni) : une baguette
    et un pied n'ont pas la même amplitude ni la même vitesse de geste.
    """
    spec = MarkerSpec(
        name=SINGLE_MARKER_NAME,
        color_range=color_range,
        strike_plane_y=strike_plane_y,
        element_id=element_id,
        min_speed_px_per_s=min_speed_px_per_s,
        refractory_s=refractory_s,
    )
    return track_markers(
        frames,
        [spec],
        detectors={SINGLE_MARKER_NAME: detector} if detector is not None else None,
        send_frames=send_frames,
        working_width=working_width,
        now_ns=now_ns,
    )


def run_markers_process(
    queue: Any,
    specs: Sequence[MarkerSpec],
    *,
    mirror: bool = False,
    send_frames: bool = False,
    frames: Iterator[np.ndarray] | None = None,
) -> None:
    """Point d'entrée du processus : boucle et pousse les échantillons sur ``queue``.

    ``frames`` permet d'injecter une source d'images de test ; par défaut, ouvre la
    webcam 0. ``queue`` n'a besoin que d'une méthode ``put`` (un vrai
    ``multiprocessing.Queue``, ou un objet compatible dans les tests).
    """
    frame_iter = frames if frames is not None else camera_frames()
    for sample in track_markers(frame_iter, specs, mirror=mirror, send_frames=send_frames):
        queue.put(sample)


def run_vision_process(
    queue: Any,
    color_range: ColorRange,
    strike_plane_y: float,
    *,
    element_id: str = "snare",
    min_speed_px_per_s: float = DEFAULT_MIN_SPEED_PX_PER_S,
    refractory_s: float = DEFAULT_REFRACTORY_S,
    send_frames: bool = False,
    frames: Iterator[np.ndarray] | None = None,
) -> None:
    """Raccourci de ``run_markers_process`` pour un seul embout (baguette, pied)."""
    spec = MarkerSpec(
        name=SINGLE_MARKER_NAME,
        color_range=color_range,
        strike_plane_y=strike_plane_y,
        element_id=element_id,
        min_speed_px_per_s=min_speed_px_per_s,
        refractory_s=refractory_s,
    )
    run_markers_process(queue, [spec], send_frames=send_frames, frames=frames)
