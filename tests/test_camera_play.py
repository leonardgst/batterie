"""Tests du jeu à la caméra : flux et moteur audio factices, aucune vraie caméra."""

import cv2
import numpy as np
import pygame
import pytest

from batterie.config.settings import CameraSettings
from batterie.config.zones import save_zones
from batterie.core.events import HitEvent, Source
from batterie.input.vision import process
from batterie.input.vision.color_tracker import TrackedPoint
from batterie.input.vision.hands import hand_specs
from batterie.input.vision.process import (
    WORKING_WIDTH,
    CameraInfo,
    MarkerSample,
    VisionSample,
    camera_frames,
)
from batterie.input.vision.source import VisionFeed
from batterie.input.vision.zones import Zone, ZoneMap
from batterie.ui import camera_play
from batterie.ui.calibration import CAMERA_LOST_MESSAGE
from batterie.ui.camera_play import NO_ZONES_MESSAGE, CameraPlayScreen, Phase
from batterie.ui.kit_view import KitView
from fakes import FakeProcess, FakeQueue

ZONES = ZoneMap(
    (
        Zone("snare", 60.0, 140.0, 50.0, 100.0, 140.0),
        Zone("ride", 180.0, 260.0, 50.0, 100.0, 140.0),
    )
)
CAMERA = CameraInfo(width=640, height=480, fps=30.0, mjpeg=False)


class FakeEngine:
    def __init__(self) -> None:
        self.played: list[tuple[str, float]] = []

    def play(self, element_id: str, velocity: float = 1.0) -> None:
        self.played.append((element_id, velocity))


def _hit(element_id: str) -> HitEvent:
    return HitEvent(element_id=element_id, velocity=1.0, t_ns=0, source=Source.VISION)


def _sample(
    *hits: str,
    camera: CameraInfo | None = None,
    left_seen: bool = True,
) -> VisionSample:
    left = TrackedPoint(100.0, 80.0, 300.0) if left_seen else None
    return VisionSample(
        t_ns=0,
        markers={
            "left": MarkerSample(left, 0.0, _hit(hits[0]) if hits else None),
            "right": MarkerSample(
                TrackedPoint(220.0, 80.0, 300.0), 0.0, _hit(hits[1]) if len(hits) > 1 else None
            ),
        },
        fps=29.5,
        processing_ms=1.2,
        frame_preview=np.zeros((180, WORKING_WIDTH, 3), dtype=np.uint8),
        camera=camera,
    )


def _key(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


@pytest.fixture
def pygame_ready():
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def parts(pygame_ready):
    queue, process_ = FakeQueue(), FakeProcess()
    engine = FakeEngine()
    kit_view = KitView()
    screen = CameraPlayScreen(VisionFeed(queue, process_), ZONES, engine, kit_view)
    return screen, queue, process_, engine, kit_view


# --- Jouer -------------------------------------------------------------------------


def test_each_hit_plays_its_element_as_soon_as_it_is_read(parts):
    screen, queue, _, engine, _ = parts
    queue.items += [_sample("snare"), _sample(), _sample("ride")]

    screen.update([])

    assert engine.played == [("snare", 1.0), ("ride", 1.0)]
    assert screen.hits == 2


def test_two_hands_hitting_on_the_same_image_both_sound(parts):
    screen, queue, _, engine, _ = parts
    queue.items.append(_sample("snare", "ride"))

    screen.update([])

    assert engine.played == [("snare", 1.0), ("ride", 1.0)]


def test_a_hit_lights_up_the_kit(parts):
    screen, queue, _, _, kit_view = parts
    queue.items.append(_sample("snare"))

    screen.update([])

    assert "snare" in kit_view._flash_until
    assert "ride" not in kit_view._flash_until


def test_nothing_plays_without_a_hit(parts):
    screen, queue, _, engine, _ = parts
    queue.items += [_sample(), _sample()]

    screen.update([])

    assert engine.played == []
    assert screen.hits == 0


def test_the_screen_starts_playing_at_the_first_sample(parts):
    screen, queue, *_ = parts
    assert screen.phase is Phase.STARTING

    screen.update([])
    assert screen.phase is Phase.STARTING

    queue.items.append(_sample())
    screen.update([])
    assert screen.phase is Phase.PLAYING


def test_the_granted_camera_settings_are_remembered(parts):
    screen, queue, *_ = parts
    queue.items.append(_sample(camera=CAMERA))

    screen.update([])

    assert screen.camera == CAMERA


# --- Fermer, erreurs ---------------------------------------------------------------


def test_escape_closes_the_screen_and_releases_the_camera(parts):
    screen, _, process_, *_ = parts

    assert screen.update([_key(pygame.K_ESCAPE)]) is False
    screen.close()

    assert process_.terminated


def test_enter_does_not_close_the_screen_while_playing(parts):
    screen, queue, *_ = parts
    queue.items.append(_sample())

    assert screen.update([_key(pygame.K_RETURN)]) is True


def test_a_lost_camera_shows_a_clear_error(parts):
    screen, _, process_, *_ = parts
    process_.alive = False

    assert screen.update([]) is True

    assert screen.phase is Phase.ERROR
    assert screen.error == CAMERA_LOST_MESSAGE
    assert screen.update([_key(pygame.K_RETURN)]) is False


def test_no_sound_after_the_camera_is_lost(parts):
    screen, queue, process_, engine, _ = parts
    process_.alive = False
    screen.update([])
    queue.items.append(_sample("snare"))

    screen.update([])

    assert engine.played == []


# --- Ouverture : zones et caméra ----------------------------------------------------


@pytest.fixture
def started(monkeypatch, pygame_ready):
    """Remplace le démarrage de la vraie caméra ; liste les démarrages demandés."""
    calls: list[dict] = []

    def fake_start(specs, **kwargs):
        calls.append({"specs": specs, **kwargs})
        return VisionFeed(FakeQueue(), FakeProcess())

    monkeypatch.setattr(camera_play.VisionFeed, "start", staticmethod(fake_start))
    return calls


def test_open_without_zones_does_not_start_the_camera(tmp_path, started):
    screen = CameraPlayScreen.open(
        FakeEngine(), KitView(), CameraSettings(), zones_file=tmp_path / "zones.toml"
    )

    assert screen.phase is Phase.NO_ZONES
    assert screen.feed is None
    assert started == []
    assert screen.update([]) is True
    assert screen.update([_key(pygame.K_RETURN)]) is False


def test_open_with_an_unreadable_zones_file_explains_it(tmp_path, started):
    zones_file = tmp_path / "zones.toml"
    zones_file.write_text("pas du toml [[[", encoding="utf-8")

    screen = CameraPlayScreen.open(FakeEngine(), KitView(), CameraSettings(), zones_file=zones_file)

    assert screen.phase is Phase.ERROR
    assert "Calibrer la caméra" in screen.error
    assert started == []


def test_open_with_zones_from_another_image_width_is_refused(tmp_path, started):
    zones_file = tmp_path / "zones.toml"
    save_zones(ZONES, zones_file, working_width=WORKING_WIDTH * 2)

    screen = CameraPlayScreen.open(FakeEngine(), KitView(), CameraSettings(), zones_file=zones_file)

    assert screen.phase is Phase.ERROR
    assert started == []


def test_open_with_zones_starts_both_hands_on_those_zones_with_the_camera_settings(
    tmp_path, started
):
    zones_file = tmp_path / "zones.toml"
    save_zones(ZONES, zones_file, working_width=WORKING_WIDTH)
    settings = CameraSettings(device_index=1, width=1280, height=720, fps=60, mjpeg=True)

    screen = CameraPlayScreen.open(FakeEngine(), KitView(), settings, zones_file=zones_file)

    assert screen.phase is Phase.STARTING
    (call,) = started
    assert call["camera"] == settings
    assert call["mirror"] is True and call["send_frames"] is True
    assert [spec.name for spec in call["specs"]] == ["left", "right"]
    assert all(spec.zones is not None and len(spec.zones) == 2 for spec in call["specs"])


# --- Dessin ------------------------------------------------------------------------


def test_every_phase_draws_without_error(parts):
    screen, queue, process_, *_ = parts
    surface = pygame.display.set_mode((1280, 720))
    area = surface.get_rect()

    screen.draw(surface, area)  # STARTING
    queue.items += [_sample("snare", camera=CAMERA), _sample(left_seen=False)]
    screen.update([])
    screen.draw(surface, area)  # PLAYING, main gauche non vue
    process_.alive = False
    screen.update([])
    screen.draw(surface, area)  # ERROR
    CameraPlayScreen(None, ZoneMap(), FakeEngine(), KitView()).draw(surface, area)  # NO_ZONES


def test_the_no_zones_message_points_to_the_calibration():
    assert "Calibrer la caméra" in NO_ZONES_MESSAGE


# --- Caméra : ce qui est demandé, ce qui est accordé -------------------------------


class FakeCapture:
    """Caméra factice : note ce qu'on lui demande, accorde 640×480 à 30 i/s en MJPEG."""

    last: "FakeCapture"

    def __init__(self, index: int) -> None:
        self.index = index
        self.requested: dict[int, float] = {}
        self.released = False
        self.reads = 2
        FakeCapture.last = self

    def set(self, prop: int, value: float) -> bool:
        self.requested[prop] = value
        return True

    def get(self, prop: int) -> float:
        granted = {
            cv2.CAP_PROP_FRAME_WIDTH: 640,
            cv2.CAP_PROP_FRAME_HEIGHT: 480,
            cv2.CAP_PROP_FPS: 30,
            cv2.CAP_PROP_FOURCC: int.from_bytes(b"MJPG", "little"),
        }
        return granted.get(prop, 0)

    def isOpened(self) -> bool:  # noqa: N802 - nom imposé par OpenCV
        return True

    def read(self):
        self.reads -= 1
        return (self.reads >= 0, np.zeros((480, 640, 3), dtype=np.uint8))

    def release(self) -> None:
        self.released = True


class FakeSink:
    def __init__(self) -> None:
        self.items: list[VisionSample] = []

    def put(self, item: VisionSample) -> None:
        self.items.append(item)


def test_camera_frames_asks_for_the_settings_and_reports_what_it_got(monkeypatch):
    monkeypatch.setattr(process.cv2, "VideoCapture", FakeCapture)
    granted: list[CameraInfo] = []
    settings = CameraSettings(device_index=2, width=1280, height=720, fps=60, mjpeg=True)

    frames = list(camera_frames(settings, on_open=granted.append))

    capture = FakeCapture.last
    assert capture.index == 2
    assert capture.requested[cv2.CAP_PROP_FRAME_WIDTH] == 1280
    assert capture.requested[cv2.CAP_PROP_FRAME_HEIGHT] == 720
    assert capture.requested[cv2.CAP_PROP_FPS] == 60
    assert cv2.CAP_PROP_FOURCC in capture.requested
    assert granted == [CameraInfo(width=640, height=480, fps=30.0, mjpeg=True)]
    assert len(frames) == 2
    assert capture.released


def test_camera_frames_without_settings_opens_camera_zero_untouched(monkeypatch):
    monkeypatch.setattr(process.cv2, "VideoCapture", FakeCapture)

    list(camera_frames())

    assert FakeCapture.last.index == 0
    assert FakeCapture.last.requested == {}


def test_camera_frames_does_not_force_mjpeg_unless_asked(monkeypatch):
    monkeypatch.setattr(process.cv2, "VideoCapture", FakeCapture)

    list(camera_frames(CameraSettings(mjpeg=False)))

    assert cv2.CAP_PROP_FOURCC not in FakeCapture.last.requested


def test_the_process_stamps_every_sample_with_the_granted_camera(monkeypatch):
    monkeypatch.setattr(process.cv2, "VideoCapture", FakeCapture)
    sink = FakeSink()

    process.run_markers_process(sink, hand_specs(), camera=CameraSettings())

    assert len(sink.items) == 2
    assert all(sample.camera == CameraInfo(640, 480, 30.0, True) for sample in sink.items)
