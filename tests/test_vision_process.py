"""Tests du pipeline caméra → échantillons : sans caméra, sans processus réel."""

import cv2
import numpy as np
import pytest

from batterie.core.events import Source
from batterie.input.vision.color_tracker import GREEN
from batterie.input.vision.process import VisionSample, run_vision_process, track_and_detect

IMAGE_SIZE = 200


def _bgr_for_hsv(h: int, s: int, v: int) -> tuple[int, int, int]:
    pixel = np.uint8([[[h, s, v]]])
    bgr = cv2.cvtColor(pixel, cv2.COLOR_HSV2BGR)[0][0]
    return int(bgr[0]), int(bgr[1]), int(bgr[2])


GREEN_BGR = _bgr_for_hsv(60, 200, 200)


def _frame_at(y: int) -> np.ndarray:
    frame = np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
    frame[y - 15 : y + 15, 85:115] = GREEN_BGR
    return frame


class _FakeClock:
    """Horloge déterministe : avance d'un pas fixe à chaque appel (pas de vrai temps)."""

    def __init__(self, step_ns: int = 10_000_000) -> None:  # 10 ms par défaut
        self._now = 0
        self._step = step_ns

    def __call__(self) -> int:
        value = self._now
        self._now += self._step
        return value


class _FakeQueue:
    def __init__(self) -> None:
        self.items: list = []

    def put(self, item) -> None:
        self.items.append(item)


def test_track_and_detect_yields_one_sample_per_frame():
    frames = [_frame_at(50), _frame_at(70), _frame_at(150)]
    samples = list(
        track_and_detect(iter(frames), GREEN, strike_plane_y=1000.0, now_ns=_FakeClock())
    )
    assert len(samples) == 3
    assert all(isinstance(s, VisionSample) for s in samples)


def test_track_and_detect_reports_no_point_on_blank_frames():
    frames = [np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)]
    [sample] = track_and_detect(iter(frames), GREEN, strike_plane_y=100.0, now_ns=_FakeClock())
    assert sample.point is None
    assert sample.hit_event is None


def test_track_and_detect_computes_downward_velocity():
    # Horloge truquée : 20 ms s'écoulent entre le 1er et le 2e appel à now_ns()
    # (chaque image consomme 2 ticks : début de traitement puis fin).
    frames = [_frame_at(50), _frame_at(70)]
    samples = list(
        track_and_detect(iter(frames), GREEN, strike_plane_y=1000.0, now_ns=_FakeClock())
    )
    assert samples[0].velocity_px_per_s == 0.0  # pas de point précédent
    assert samples[1].velocity_px_per_s == pytest.approx(1000.0, rel=0.05)


def test_track_and_detect_emits_a_hit_event_on_fast_crossing():
    frames = [_frame_at(50), _frame_at(70), _frame_at(150)]  # franchit 100 entre 70 et 150

    samples = list(
        track_and_detect(
            iter(frames), GREEN, strike_plane_y=100.0, element_id="snare", now_ns=_FakeClock()
        )
    )

    assert samples[0].hit_event is None
    assert samples[1].hit_event is None
    assert samples[2].hit_event is not None
    assert samples[2].hit_event.element_id == "snare"
    assert samples[2].hit_event.source is Source.VISION


def test_track_and_detect_includes_a_preview_frame_only_when_requested():
    frames = [_frame_at(50)]
    [without] = track_and_detect(iter(frames), GREEN, strike_plane_y=100.0, now_ns=_FakeClock())
    [with_preview] = track_and_detect(
        iter(frames), GREEN, strike_plane_y=100.0, now_ns=_FakeClock(), send_frames=True
    )
    assert without.frame_preview is None
    assert with_preview.frame_preview is not None


def test_working_width_resizes_before_detecting_so_coordinates_match_the_preview():
    big_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    big_frame[225:255, 305:335] = GREEN_BGR  # centré en (320, 240) dans l'image 640x480

    [sample] = track_and_detect(
        iter([big_frame]),
        GREEN,
        strike_plane_y=1000.0,
        now_ns=_FakeClock(),
        working_width=320,
        send_frames=True,
    )

    assert sample.point is not None
    # Réduit de moitié (640 -> 320) : le marqueur doit apparaître vers (160, 120).
    assert sample.point.x == pytest.approx(160, abs=2)
    assert sample.point.y == pytest.approx(120, abs=2)
    assert sample.frame_preview.shape[1] == 320


def test_run_vision_process_pushes_every_sample_onto_the_queue():
    frames = [_frame_at(50), _frame_at(70), _frame_at(150)]
    queue = _FakeQueue()

    run_vision_process(queue, GREEN, strike_plane_y=100.0, frames=iter(frames))

    assert len(queue.items) == 3
    assert any(sample.hit_event is not None for sample in queue.items)


def test_detector_thresholds_are_passed_through_to_the_strike_detector():
    # Le franchissement 70 -> 150 se fait en 20 ms d'horloge truquée : ~4000 px/s.
    frames = [_frame_at(50), _frame_at(70), _frame_at(150)]

    default = list(track_and_detect(iter(frames), GREEN, strike_plane_y=100.0, now_ns=_FakeClock()))
    too_slow_for_this_gesture = list(
        track_and_detect(
            iter(frames),
            GREEN,
            strike_plane_y=100.0,
            min_speed_px_per_s=10_000.0,
            now_ns=_FakeClock(),
        )
    )

    assert any(sample.hit_event is not None for sample in default)
    assert all(sample.hit_event is None for sample in too_slow_for_this_gesture)


def test_run_vision_process_forwards_the_detector_thresholds():
    frames = [_frame_at(50), _frame_at(70), _frame_at(150)]
    queue = _FakeQueue()

    # Horloge réelle ici (pas d'horloge injectable) : les vitesses calculées sont énormes,
    # d'où un seuil volontairement inatteignable.
    run_vision_process(
        queue, GREEN, strike_plane_y=100.0, min_speed_px_per_s=1e12, frames=iter(frames)
    )

    assert len(queue.items) == 3
    assert all(sample.hit_event is None for sample in queue.items)
