"""Tests du flux caméra et de l'écran de calibration : caméra et processus factices."""

import math
import queue as queue_module

import numpy as np
import pygame
import pytest

from batterie.config.zones import load_zones
from batterie.input.vision.calibration import CALIBRATION_ELEMENTS, SETTLE_S
from batterie.input.vision.color_tracker import TrackedPoint
from batterie.input.vision.process import WORKING_WIDTH, MarkerSample, VisionSample
from batterie.input.vision.source import VisionFeed
from batterie.ui.calibration import CAMERA_LOST_MESSAGE, CalibrationScreen, Phase

FPS = 30
DT = 1 / FPS


class FakeQueue:
    def __init__(self) -> None:
        self.items: list = []

    def get_nowait(self):
        if not self.items:
            raise queue_module.Empty
        return self.items.pop(0)


class FakeProcess:
    def __init__(self) -> None:
        self.alive = True
        self.terminated = False
        self.joined_with: float | None = None

    def is_alive(self) -> bool:
        return self.alive

    def terminate(self) -> None:
        self.terminated = True
        self.alive = False

    def join(self, timeout: float | None = None) -> None:
        self.joined_with = timeout


def _frame() -> np.ndarray:
    return np.zeros((180, WORKING_WIDTH, 3), dtype=np.uint8)


def _sample(t_s: float, position=None) -> VisionSample:
    point = TrackedPoint(position[0], position[1], 300.0) if position else None
    return VisionSample(
        t_ns=round(t_s * 1_000_000_000),
        markers={
            "left": MarkerSample(point, 0.0, None),
            "right": MarkerSample(None, 0.0, None),
        },
        fps=float(FPS),
        processing_ms=1.0,
        frame_preview=_frame(),
    )


def _stroke_samples(t0: float, x: float, top: float, bottom: float) -> list[VisionSample]:
    steps = 12
    t, out = t0, []
    for _ in range(4):
        out.append(_sample(t, (x, top)))
        t += DT
    for i in range(1, steps + 1):
        y = top + (bottom - top) * (1 - math.cos(2 * math.pi * i / steps)) / 2
        out.append(_sample(t, (x, y)))
        t += DT
    for _ in range(4):
        out.append(_sample(t, (x, top)))
        t += DT
    return out


def _all_samples() -> list[VisionSample]:
    """3 coups sur chacun des 4 éléments, de gauche à droite."""
    xs = {"hihat_closed": 45.0, "snare": 115.0, "tom_mid": 195.0, "ride": 275.0}
    samples: list[VisionSample] = []
    t = 0.0
    for element_id in CALIBRATION_ELEMENTS:
        for index in range(3):
            stroke = _stroke_samples(t, xs[element_id] + index * 3, 60.0, 150.0)
            samples += stroke
            t = stroke[-1].t_ns / 1e9 + 0.4
        t += SETTLE_S + 0.5
    return samples


def _key(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


@pytest.fixture
def parts(tmp_path):
    queue, process = FakeQueue(), FakeProcess()
    feed = VisionFeed(queue, process)
    screen = CalibrationScreen(feed, zones_file=tmp_path / "zones.toml")
    return screen, queue, process, tmp_path / "zones.toml"


def _calibrate(screen, queue) -> None:
    queue.items += _all_samples()
    screen.update([])


# --- VisionFeed ----------------------------------------------------------------------


def test_feed_poll_returns_everything_waiting_without_blocking():
    queue, process = FakeQueue(), FakeProcess()
    feed = VisionFeed(queue, process)
    assert feed.poll() == []
    queue.items += [_sample(0.0), _sample(0.1)]
    got = feed.poll()
    assert [s.t_ns for s in got] == [0, 100_000_000]
    assert feed.latest is got[-1]
    assert feed.poll() == []
    assert feed.latest is got[-1]  # le dernier échantillon reste disponible


def test_feed_reports_a_dead_process_and_closes_it():
    queue, process = FakeQueue(), FakeProcess()
    feed = VisionFeed(queue, process)
    assert feed.is_alive()
    feed.close()
    assert process.terminated
    assert process.joined_with is not None
    assert not feed.is_alive()


# --- Écran : déroulé -------------------------------------------------------------------


def test_screen_waits_for_the_first_image_then_calibrates(parts):
    screen, queue, _, _ = parts
    assert screen.update([]) is True
    assert screen.phase is Phase.STARTING
    queue.items.append(_sample(0.0))
    screen.update([])
    assert screen.phase is Phase.CALIBRATING


def test_screen_reaches_review_when_every_element_is_done_and_writes_nothing_yet(parts):
    screen, queue, _, zones_file = parts
    _calibrate(screen, queue)
    assert screen.phase is Phase.REVIEW
    assert not zones_file.exists()


def test_enter_in_review_saves_the_zones_and_a_second_enter_closes(parts):
    screen, queue, _, zones_file = parts
    _calibrate(screen, queue)

    assert screen.update([_key(pygame.K_RETURN)]) is True
    assert screen.phase is Phase.SAVED
    saved = load_zones(zones_file, working_width=WORKING_WIDTH)
    assert [z.element_id for z in saved] == list(CALIBRATION_ELEMENTS)

    assert screen.update([_key(pygame.K_RETURN)]) is False


def test_escape_closes_at_every_phase_without_writing(parts):
    screen, queue, _, zones_file = parts
    assert screen.update([_key(pygame.K_ESCAPE)]) is False  # pendant l'ouverture

    queue.items.append(_sample(0.0))
    assert screen.update([_key(pygame.K_ESCAPE)]) is False  # pendant la calibration

    _calibrate(screen, queue)
    assert screen.phase is Phase.REVIEW
    assert screen.update([_key(pygame.K_ESCAPE)]) is False  # à la validation
    assert not zones_file.exists()


def test_escape_leaves_the_existing_zones_untouched(parts):
    screen, queue, _, zones_file = parts
    zones_file.write_text("# mes anciennes zones\n", encoding="utf-8")
    _calibrate(screen, queue)
    assert screen.update([_key(pygame.K_ESCAPE)]) is False
    assert zones_file.read_text(encoding="utf-8") == "# mes anciennes zones\n"


def test_r_restarts_the_current_element(parts):
    screen, queue, _, _ = parts
    queue.items += _stroke_samples(0.0, 45.0, 60.0, 150.0)
    screen.update([])
    assert screen.run.strokes_done == 1
    screen.update([_key(pygame.K_r)])
    assert screen.run.strokes_done == 0


def test_enter_does_nothing_before_the_calibration_is_finished(parts):
    screen, queue, _, zones_file = parts
    queue.items.append(_sample(0.0))
    assert screen.update([_key(pygame.K_RETURN)]) is True
    assert screen.phase is Phase.CALIBRATING
    assert not zones_file.exists()


# --- Écran : erreurs ---------------------------------------------------------------------


def test_camera_lost_before_the_first_image_is_reported(parts):
    screen, _, process, _ = parts
    process.alive = False
    screen.update([])
    assert screen.phase is Phase.ERROR
    assert screen.error == CAMERA_LOST_MESSAGE
    assert screen.update([_key(pygame.K_RETURN)]) is False


def test_camera_lost_during_the_calibration_is_reported(parts):
    screen, queue, process, _ = parts
    queue.items.append(_sample(0.0))
    screen.update([])
    process.alive = False
    screen.update([])
    assert screen.phase is Phase.ERROR


def test_losing_the_camera_after_the_last_element_still_lets_you_save(parts):
    screen, queue, process, zones_file = parts
    _calibrate(screen, queue)
    process.alive = False
    screen.update([])
    assert screen.phase is Phase.REVIEW
    screen.update([_key(pygame.K_RETURN)])
    assert screen.phase is Phase.SAVED
    assert zones_file.exists()


def test_a_failed_write_is_reported_instead_of_crashing(tmp_path):
    queue, process = FakeQueue(), FakeProcess()
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("je suis un fichier", encoding="utf-8")
    screen = CalibrationScreen(VisionFeed(queue, process), zones_file=blocker / "zones.toml")
    _calibrate(screen, queue)

    screen.update([_key(pygame.K_RETURN)])

    assert screen.phase is Phase.ERROR
    assert "enregistrer" in screen.error


def test_close_stops_the_camera(parts):
    screen, _, process, _ = parts
    screen.close()
    assert process.terminated


# --- Écran : dessin ----------------------------------------------------------------------


@pytest.mark.parametrize("stage", ["starting", "calibrating", "error", "review", "saved"])
def test_every_phase_can_be_drawn(parts, stage):
    screen, queue, process, _ = parts
    surface = pygame.Surface((1280, 720))
    area = surface.get_rect()

    if stage == "starting":
        pass
    elif stage == "calibrating":
        queue.items += _stroke_samples(0.0, 45.0, 60.0, 150.0)
    elif stage == "error":
        process.alive = False
    else:
        _calibrate(screen, queue)
        if stage == "saved":
            screen.update([_key(pygame.K_RETURN)])
    screen.update([])
    surface.fill((0, 0, 0))

    screen.draw(surface, area)

    if stage != "starting":
        # Quelque chose a été dessiné dans la colonne de droite.
        panel = surface.subsurface(pygame.Rect(700, 60, 560, 400))
        assert pygame.surfarray.array3d(panel).any()


def test_a_long_error_message_is_wrapped_inside_the_window(parts):
    screen, _, process, _ = parts
    process.alive = False
    screen.update([])
    surface = pygame.Surface((1280, 720))
    screen.draw(surface, surface.get_rect())
    # Rien ne dépasse du bord droit de la fenêtre : la dernière colonne reste vide.
    assert not pygame.surfarray.array3d(surface)[-1].any()
