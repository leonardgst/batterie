"""Tests du pipeline caméra → échantillons : sans caméra, sans processus réel."""

import cv2
import numpy as np
import pytest

from batterie.core.events import Source
from batterie.input.vision.color_tracker import GREEN, ORANGE
from batterie.input.vision.process import (
    MarkerSpec,
    VisionSample,
    run_markers_process,
    run_vision_process,
    track_and_detect,
    track_markers,
)
from batterie.input.vision.zones import Zone, ZoneMap

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


# --- Deux marqueurs (phase 04) ---

ORANGE_BGR = _bgr_for_hsv(14, 230, 255)
PLANE_Y = 100.0


def _two_hand_frame(left_y: int | None, right_y: int | None) -> np.ndarray:
    """Image 200x200 : carré orange à gauche (x=50), carré vert à droite (x=150)."""
    frame = np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
    if left_y is not None:
        frame[left_y - 10 : left_y + 10, 40:60] = ORANGE_BGR
    if right_y is not None:
        frame[right_y - 10 : right_y + 10, 140:160] = GREEN_BGR
    return frame


def _hand_specs() -> list[MarkerSpec]:
    return [
        MarkerSpec("left", ORANGE, PLANE_Y, element_id="snare"),
        MarkerSpec("right", GREEN, PLANE_Y, element_id="ride"),
    ]


def test_track_markers_reports_each_marker_separately():
    frames = [_two_hand_frame(60, 150)]
    [sample] = track_markers(iter(frames), _hand_specs(), now_ns=_FakeClock())

    assert set(sample.markers) == {"left", "right"}
    left, right = sample.markers["left"], sample.markers["right"]
    assert left.point is not None and left.point.x == pytest.approx(50, abs=1)
    assert left.point.y == pytest.approx(60, abs=1)
    assert right.point is not None and right.point.x == pytest.approx(150, abs=1)
    assert right.point.y == pytest.approx(150, abs=1)


def test_a_hand_out_of_view_does_not_affect_the_other():
    frames = [_two_hand_frame(60, None), _two_hand_frame(70, None)]
    samples = list(track_markers(iter(frames), _hand_specs(), now_ns=_FakeClock()))

    assert samples[1].markers["right"].point is None
    assert samples[1].markers["left"].point is not None
    assert samples[1].markers["left"].velocity_px_per_s == pytest.approx(500.0, rel=0.05)


def test_each_hand_hits_independently_with_its_own_element():
    # La main gauche franchit le plan (100) entre la 2e et la 3e image, la droite entre
    # la 4e et la 5e : deux coups, aux bons éléments, à des images différentes.
    frames = [
        _two_hand_frame(50, 50),
        _two_hand_frame(70, 50),
        _two_hand_frame(150, 50),
        _two_hand_frame(150, 70),
        _two_hand_frame(150, 150),
    ]
    samples = list(track_markers(iter(frames), _hand_specs(), now_ns=_FakeClock()))

    hits = [(i, e.element_id) for i, s in enumerate(samples) for e in s.hit_events]
    assert hits == [(2, "snare"), (4, "ride")]


def test_a_hit_on_one_hand_does_not_start_the_other_hands_debounce():
    # Les deux mains frappent à la même image : les deux coups sont comptés, l'anti-rebond
    # est propre à chaque main.
    frames = [
        _two_hand_frame(50, 50),
        _two_hand_frame(70, 70),
        _two_hand_frame(150, 150),
    ]
    *_, last = track_markers(iter(frames), _hand_specs(), now_ns=_FakeClock())
    assert len(last.hit_events) == 2


def test_each_hand_keeps_its_own_thresholds():
    specs = [
        MarkerSpec("left", ORANGE, PLANE_Y, min_speed_px_per_s=1e12),  # n'atteindra jamais
        MarkerSpec("right", GREEN, PLANE_Y),
    ]
    frames = [_two_hand_frame(50, 50), _two_hand_frame(70, 70), _two_hand_frame(150, 150)]
    samples = list(track_markers(iter(frames), specs, now_ns=_FakeClock()))
    assert all(s.markers["left"].hit_event is None for s in samples)
    assert samples[2].markers["right"].hit_event is not None


def test_mirror_puts_the_left_hand_on_the_left_of_the_preview():
    # Image non retournée : l'orange est à gauche du carré vert. Le miroir inverse l'ordre.
    frame = _two_hand_frame(60, 150)
    specs = _hand_specs()
    [plain] = track_markers(iter([frame]), specs, now_ns=_FakeClock())
    [mirrored] = track_markers(iter([frame]), specs, mirror=True, now_ns=_FakeClock())

    assert plain.markers["left"].point.x < plain.markers["right"].point.x
    assert mirrored.markers["left"].point.x > mirrored.markers["right"].point.x
    assert mirrored.markers["left"].point.x == pytest.approx(IMAGE_SIZE - 1 - 50, abs=1)


def test_mirror_also_flips_the_preview_so_it_matches_the_tracked_points():
    frame = _two_hand_frame(60, 150)
    [sample] = track_markers(
        iter([frame]), _hand_specs(), mirror=True, send_frames=True, now_ns=_FakeClock()
    )
    assert np.array_equal(sample.frame_preview, frame[:, ::-1])


def test_track_markers_rejects_an_empty_or_duplicated_marker_list():
    with pytest.raises(ValueError):
        list(track_markers(iter([]), [], now_ns=_FakeClock()))
    twin = [MarkerSpec("a", GREEN, PLANE_Y), MarkerSpec("a", ORANGE, PLANE_Y)]
    with pytest.raises(ValueError, match="double"):
        list(track_markers(iter([]), twin, now_ns=_FakeClock()))


def test_single_marker_shortcuts_still_expose_the_first_marker():
    frames = [_frame_at(50), _frame_at(70)]
    samples = list(track_and_detect(iter(frames), GREEN, 1000.0, now_ns=_FakeClock()))
    assert set(samples[0].markers) == {"marker"}
    assert samples[1].point is samples[1].markers["marker"].point
    assert samples[1].velocity_px_per_s == samples[1].markers["marker"].velocity_px_per_s


def test_run_markers_process_pushes_every_sample_with_both_hands():
    frames = [_two_hand_frame(50, 50), _two_hand_frame(70, 70), _two_hand_frame(150, 150)]
    queue = _FakeQueue()

    run_markers_process(queue, _hand_specs(), frames=iter(frames))

    assert len(queue.items) == 3
    assert set(queue.items[0].markers) == {"left", "right"}
    assert sum(len(sample.hit_events) for sample in queue.items) == 2


# --- Zones : attribution à l'élément dans le pipeline (phase 04) ---


def _zones_for_two_hand_frames() -> ZoneMap:
    """Image de test 200x200 : snare autour de x=50 (main orange), ride autour de x=150 (verte)."""
    return ZoneMap(
        (
            Zone("snare", 20, 80, y_top=40, strike_plane_y=PLANE_Y, y_bottom=180),
            Zone("ride", 120, 180, y_top=40, strike_plane_y=PLANE_Y, y_bottom=180),
        )
    )


def test_markers_with_zones_hit_the_element_of_the_zone_they_strike():
    zones = _zones_for_two_hand_frames()
    specs = [
        MarkerSpec("left", ORANGE, PLANE_Y, zones=zones),
        MarkerSpec("right", GREEN, PLANE_Y, zones=zones),
    ]
    frames = [
        _two_hand_frame(50, 50),
        _two_hand_frame(70, 50),
        _two_hand_frame(150, 50),  # la main orange (x=50) frappe : snare
        _two_hand_frame(150, 70),
        _two_hand_frame(150, 150),  # la main verte (x=150) frappe : ride
    ]
    samples = list(track_markers(iter(frames), specs, now_ns=_FakeClock()))

    hits = [
        (i, name, m.hit_event.element_id)
        for i, s in enumerate(samples)
        for name, m in s.markers.items()
        if m.hit_event is not None
    ]
    assert hits == [(2, "left", "snare"), (4, "right", "ride")]


def test_a_hand_outside_every_zone_hits_nothing_even_when_it_crosses_the_plane():
    zones = ZoneMap((Zone("ride", 120, 180, y_top=40, strike_plane_y=PLANE_Y, y_bottom=180),))
    specs = [MarkerSpec("left", ORANGE, PLANE_Y, zones=zones)]  # la main orange est à x=50
    frames = [_two_hand_frame(50, None), _two_hand_frame(70, None), _two_hand_frame(150, None)]
    samples = list(track_markers(iter(frames), specs, now_ns=_FakeClock()))
    assert all(s.markers["left"].hit_event is None for s in samples)


def test_each_hand_has_its_own_rearming_state_with_shared_zones():
    zones = _zones_for_two_hand_frames()
    specs = [
        MarkerSpec("left", ORANGE, PLANE_Y, zones=zones),
        MarkerSpec("right", GREEN, PLANE_Y, zones=zones),
    ]
    frames = [_two_hand_frame(50, 50), _two_hand_frame(70, 70), _two_hand_frame(150, 150)]
    *_, last = track_markers(iter(frames), specs, now_ns=_FakeClock())
    assert sorted(e.element_id for e in last.hit_events) == ["ride", "snare"]
