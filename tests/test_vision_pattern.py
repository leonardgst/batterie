"""Tests de la séance US7 (--pattern) : ligne de commande, simulateur, déroulé, zones."""

import numpy as np
import pygame
import pytest

import vision_debug
import vision_measure
from batterie.audio.engine import init_mixer
from batterie.config.settings import CameraSettings
from batterie.config.zones import ZonesError
from batterie.core.events import HitEvent, Source
from batterie.input.vision.color_tracker import TrackedPoint
from batterie.input.vision.hands import hand_specs
from batterie.input.vision.measure import US7_PATTERN, US7_PLAN, SessionRecorder, us7_checks
from batterie.input.vision.process import (
    WORKING_WIDTH,
    CameraInfo,
    MarkerSample,
    VisionSample,
    track_markers,
)
from batterie.input.vision.zones import ZoneMap
from fakes import FakeQueue

INTERVAL = US7_PLAN.beat_interval_s


# --- Ligne de commande -------------------------------------------------------------


def test_pattern_selects_the_hands_target_and_the_us7_session():
    options = vision_measure.parse_arguments(["--pattern"])
    assert options.pattern is True
    assert options.target is vision_debug.HANDS
    assert options.simulate is False


def test_pattern_can_be_simulated_and_may_name_the_hands_target():
    options = vision_measure.parse_arguments(["--pattern", "--simulate", "--target", "hands"])
    assert (options.pattern, options.simulate) == (True, True)


def test_pattern_with_another_target_is_rejected():
    with pytest.raises(SystemExit):
        vision_measure.parse_arguments(["--pattern", "--target", "foot"])


def test_without_pattern_the_phase_03_session_is_unchanged():
    options = vision_measure.parse_arguments([])
    assert options.pattern is False
    assert vision_measure.PLAN.hit_count == 50 and vision_measure.PLAN.bpm == 80.0


# --- Zones de la séance ------------------------------------------------------------


def test_simulated_zones_hold_the_four_pattern_elements_side_by_side():
    zones = vision_measure.SIMULATED_ZONES
    assert {zone.element_id for zone in zones} == set(US7_PATTERN)
    assert len(zones) == 4  # ZoneMap a déjà refusé tout chevauchement en largeur


def _fake_zone_loader(monkeypatch, result):
    def load(*_args, **_kwargs):
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(vision_measure, "load_zones", load)


def test_main_refuses_the_session_without_calibrated_zones(monkeypatch, capsys):
    _fake_zone_loader(monkeypatch, ZoneMap())
    monkeypatch.setattr(vision_measure, "run", lambda *a, **k: pytest.fail("fenêtre ouverte"))

    assert vision_measure.main(["--pattern"]) == 1
    assert "Calibrer la caméra" in capsys.readouterr().err


def test_main_refuses_the_session_with_unreadable_zones(monkeypatch, capsys):
    _fake_zone_loader(monkeypatch, ZonesError("zones.toml : fichier illisible"))
    monkeypatch.setattr(vision_measure, "run", lambda *a, **k: pytest.fail("fenêtre ouverte"))

    assert vision_measure.main(["--pattern"]) == 1
    assert "illisible" in capsys.readouterr().err


def test_main_passes_zones_and_camera_settings_to_the_session(monkeypatch):
    zones = vision_measure.SIMULATED_ZONES
    _fake_zone_loader(monkeypatch, zones)
    calls = []
    monkeypatch.setattr(vision_measure, "run", lambda target, **kw: calls.append((target, kw)))

    assert vision_measure.main(["--pattern"]) == 0

    ((target, kwargs),) = calls
    assert target is vision_debug.HANDS
    assert kwargs["pattern"] is True and kwargs["zones"] is zones
    assert isinstance(kwargs["camera"], CameraSettings)


def test_a_simulated_session_needs_no_zones_file(monkeypatch):
    _fake_zone_loader(monkeypatch, AssertionError("ne doit pas lire zones.toml"))
    calls = []
    monkeypatch.setattr(vision_measure, "run", lambda target, **kw: calls.append(kw))

    assert vision_measure.main(["--pattern", "--simulate"]) == 0
    assert calls[0]["zones"] is None


# --- Simulateur : le motif joué de bout en bout dans le vrai traitement -------------


class FakeTime:
    """Horloge et sommeil factices : la simulation de 40 s tient en quelques secondes."""

    def __init__(self) -> None:
        self.now = 0.0

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def now_ns(self) -> int:
        return round(self.now * 1_000_000_000)


def _simulated_session(duration_s: float = 42.0):
    """Fait jouer le motif aux deux mains fictives et mesure ce que le traitement détecte."""
    zones = vision_measure.SIMULATED_ZONES
    specs = hand_specs(zones)
    fake = FakeTime()
    frames = vision_measure._simulated_pattern_frames(
        specs, US7_PLAN, zones, mirror=True, clock=fake.clock, sleep=fake.sleep
    )
    first_beat_s = 16 * INTERVAL  # multiple de la durée du motif (8 clics)
    recorder = SessionRecorder(plan=US7_PLAN, source=Source.VISION, first_beat_s=first_beat_s)
    for sample in track_markers(frames, specs, mirror=True, now_ns=fake.now_ns):
        for hit in sample.hit_events:
            recorder.add_hit(hit.t_ns / 1e9, hit.element_id)
        if sample.t_ns / 1e9 > duration_s:
            break
    return recorder.result()


@pytest.fixture(scope="module")
def simulated_result():
    return _simulated_session()


def test_the_simulated_hands_play_every_click_on_the_right_element(simulated_result):
    result = simulated_result
    assert result.detected == 100
    assert result.extra == 0
    assert result.attributed == 100
    assert result.confusions == ()


def test_the_simulated_session_is_late_by_less_than_two_frames(simulated_result):
    # Le plan de frappe est franchi exactement sur le clic ; la détection ne peut qu'attendre
    # l'image suivante (1/30 s) : l'écart médian reste sous deux images.
    assert simulated_result.offset_ms is not None
    assert 0 <= simulated_result.offset_ms.median <= 2 * 1000 / 30


def test_the_simulated_session_meets_the_first_three_us7_criteria(simulated_result):
    checks = {check.label: check.met for check in us7_checks(simulated_result)}
    assert checks["Coups détectés"] and checks["Faux coups"]
    assert checks["Attribués au bon élément"]
    assert checks["Latence geste → son"] is None  # il manque la séance clavier de référence


def test_simulated_frames_follow_the_mirror_like_a_real_camera():
    zones = vision_measure.SIMULATED_ZONES
    specs = hand_specs(zones)
    snare_x = (zones.get("snare").x_min + zones.get("snare").x_max) / 2  # type: ignore[union-attr]
    ride_x = (zones.get("ride").x_min + zones.get("ride").x_max) / 2  # type: ignore[union-attr]
    positions = {}
    for mirror in (False, True):
        fake = FakeTime()
        fake.now = 0.1
        frames = vision_measure._simulated_pattern_frames(
            specs, US7_PLAN, zones, mirror=mirror, clock=fake.clock, sleep=fake.sleep
        )
        sample = next(track_markers(frames, specs, mirror=mirror, now_ns=fake.now_ns))
        positions[mirror] = (sample.markers["left"].point, sample.markers["right"].point)

    # Mirroir ou non, le traitement remet la main gauche à gauche de la droite.
    for left, right in positions.values():
        assert left is not None and right is not None
        assert left.x < right.x
    assert snare_x < ride_x


# --- Déroulé de la séance dans l'outil ---------------------------------------------


@pytest.fixture
def pygame_ready():
    init_mixer()
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def app(pygame_ready):
    return vision_measure.MeasureApp(vision_debug.HANDS, simulate=True, pattern=True)


def test_the_pattern_app_uses_the_us7_plan_and_the_simulated_zones(app):
    assert app.plan is US7_PLAN
    assert app.zones is vision_measure.SIMULATED_ZONES


def test_the_phase_03_app_keeps_its_plan_and_has_no_zones(pygame_ready):
    classic = vision_measure.MeasureApp(vision_debug.STICK, simulate=True)
    assert classic.plan is vision_measure.PLAN
    assert classic.zones is None


def test_clicks_are_high_in_the_count_in_and_accented_on_the_first_eighth_of_each_pattern(app):
    assert app._click_for(-1) is app._count_in_click
    assert app._click_for(0) is app._accent_click
    assert app._click_for(8) is app._accent_click
    assert app._click_for(1) is app._beat_click
    assert app._click_for(7) is app._beat_click


def test_a_simulated_session_starts_on_a_multiple_of_the_pattern_duration(app):
    app.source = Source.VISION
    app._start_session(123_456_789_000)

    assert app._recorder is not None
    pattern_s = len(US7_PATTERN) * INTERVAL
    assert app._recorder.first_beat_s / pattern_s == pytest.approx(
        round(app._recorder.first_beat_s / pattern_s)
    )
    assert app._next_click == -US7_PLAN.count_in_beats


def test_hits_are_recorded_with_their_element_for_the_attribution(app):
    app.source = Source.VISION
    app._start_session(0)
    assert app._recorder is not None
    first = app._recorder.first_beat_s
    sample = VisionSample(
        t_ns=round((first + 0.05) * 1e9),
        markers={
            "left": MarkerSample(
                TrackedPoint(100.0, 80.0, 300.0),
                0.0,
                HitEvent("ride", 1.0, round((first + 0.05) * 1e9), Source.VISION),
            ),
            "right": MarkerSample(None, 0.0, None),
        },
        fps=30.0,
        processing_ms=1.0,
        camera=CameraInfo(640, 480, 30.0, False),
    )
    app._queue = FakeQueue()
    app._queue.items.append(sample)

    app._drain_camera()

    result = app._recorder.result()
    assert result.detected == 1
    assert result.attributed == 0  # le motif attend la charleston sur le premier clic
    assert result.confusions == (("hihat_closed", "ride", 1),)
    assert app.camera_info == CameraInfo(640, 480, 30.0, False)


def test_every_screen_of_the_pattern_session_draws(app):
    screen = pygame.display.set_mode(vision_measure.WINDOW_SIZE)
    frame = np.zeros((180, WORKING_WIDTH, 3), dtype=np.uint8)
    sample = VisionSample(
        t_ns=0,
        markers={
            "left": MarkerSample(TrackedPoint(100.0, 80.0, 300.0), 0.0, None),
            "right": MarkerSample(None, 0.0, None),
        },
        fps=30.0,
        processing_ms=1.0,
        frame_preview=frame,
    )

    app.draw(screen, 0)  # menu
    app.source = Source.VISION
    app._latest = sample
    app.phase = vision_measure.Phase.READY
    app.draw(screen, 0)
    app._start_session(0)
    for clicks in (-US7_PLAN.count_in_beats + 1, 0, 3):
        app._next_click = clicks
        app.draw(screen, 0)
    app.source = Source.KEYBOARD
    app.draw(screen, 0)


def test_the_real_camera_gets_the_zones_and_the_camera_settings(pygame_ready, monkeypatch):
    started = []

    class FakeProcess:
        def __init__(self, target, args, kwargs, daemon):
            started.append((target, args, kwargs))

        def start(self) -> None:
            pass

    monkeypatch.setattr(vision_measure.mp, "Process", FakeProcess)
    monkeypatch.setattr(vision_measure.mp, "Queue", lambda maxsize: FakeQueue())
    zones = vision_measure.SIMULATED_ZONES
    camera = CameraSettings(fps=60, mjpeg=True)
    real = vision_measure.MeasureApp(vision_debug.HANDS, pattern=True, zones=zones, camera=camera)

    real._start_camera()

    ((target, args, kwargs),) = started
    assert target is vision_measure.run_markers_process
    specs = args[1]
    assert [spec.name for spec in specs] == ["left", "right"]
    assert all(spec.zones is zones for spec in specs)
    assert kwargs == {"mirror": True, "send_frames": True, "camera": camera}


def test_a_summary_names_the_camera_that_was_really_obtained(pygame_ready):
    real = vision_measure.MeasureApp(
        vision_debug.HANDS, pattern=True, zones=vision_measure.SIMULATED_ZONES
    )
    recorder = SessionRecorder(plan=US7_PLAN, source=Source.VISION, first_beat_s=0.0)
    real.results[Source.VISION] = recorder.result()
    real.camera_info = CameraInfo(1280, 720, 60.0, True)

    text = "\n".join(real.summary_lines())

    assert "Caméra obtenue : 1280×720, 60 i/s annoncées, MJPEG" in text
    assert "Critères US7 :" in text
