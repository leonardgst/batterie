"""Tests de la nuance (S7) : courbe de vitesse, fenêtre de vitesse, traitement, écran, réglages."""

import cv2
import numpy as np
import pygame
import pytest

from batterie.config.settings import (
    Settings,
    VelocitySettings,
    load_settings,
    save_settings,
)
from batterie.core.events import HitEvent, Source
from batterie.input.vision.color_tracker import GREEN, TrackedPoint
from batterie.input.vision.hands import hand_specs
from batterie.input.vision.process import (
    WORKING_WIDTH,
    MarkerSample,
    MarkerSpec,
    VisionSample,
    track_markers,
)
from batterie.input.vision.source import VisionFeed
from batterie.input.vision.velocity import (
    PEAK_WINDOW_S,
    SpeedWindow,
    VelocityCurve,
    curve_from_settings,
)
from batterie.input.vision.zones import Zone, ZoneMap
from batterie.ui import camera_play
from batterie.ui.camera_play import CameraPlayScreen, LastHit
from batterie.ui.kit_view import KitView
from fakes import FakeProcess, FakeQueue

# --- Courbe -----------------------------------------------------------------------

CURVE = VelocityCurve(soft_speed_px_per_s=200.0, hard_speed_px_per_s=1000.0, floor=0.2, gamma=1.0)


def test_the_softest_hit_gets_the_floor_and_the_hardest_gets_full_volume():
    assert CURVE.velocity(200.0) == pytest.approx(0.2)
    assert CURVE.velocity(1000.0) == pytest.approx(1.0)


def test_the_curve_rises_by_equal_decibel_steps_between_the_two_speeds():
    # milieu des vitesses : à mi-chemin des décibels, donc 0,2 ** 0,5 en amplitude
    assert CURVE.velocity(600.0) == pytest.approx(0.2**0.5)
    quarter, three_quarters = CURVE.velocity(400.0), CURVE.velocity(800.0)
    assert quarter / CURVE.velocity(200.0) == pytest.approx(three_quarters / CURVE.velocity(600.0))


def test_a_soft_hit_is_far_enough_below_a_hard_one_to_be_heard():
    # Linéaire de 0,3 à 1 donnait 10 dB : à peine audible. Le défaut va maintenant à 20 dB.
    default = VelocityCurve()
    drop_db = 20 * np.log10(default.velocity(default.soft_speed_px_per_s))
    assert drop_db == pytest.approx(-20.0)


def test_the_curve_is_clamped_outside_the_two_speeds():
    assert CURVE.velocity(0.0) == pytest.approx(0.2)
    assert CURVE.velocity(50.0) == pytest.approx(0.2)
    assert CURVE.velocity(5000.0) == 1.0


def test_a_faster_gesture_never_sounds_softer():
    speeds = range(0, 1500, 25)
    for gamma in (0.5, 1.0, 2.0):
        curve = VelocityCurve(200.0, 1000.0, 0.2, gamma)
        volumes = [curve.velocity(speed) for speed in speeds]
        assert volumes == sorted(volumes)
        assert all(0.0 <= volume <= 1.0 for volume in volumes)


def test_gamma_bends_the_middle_of_the_curve():
    soft = VelocityCurve(200.0, 1000.0, 0.2, gamma=2.0).velocity(600.0)
    even = VelocityCurve(200.0, 1000.0, 0.2, gamma=1.0).velocity(600.0)
    loud = VelocityCurve(200.0, 1000.0, 0.2, gamma=0.5).velocity(600.0)
    assert soft < even < loud


def test_a_floor_of_one_gives_every_hit_full_volume():
    flat = VelocityCurve(200.0, 1000.0, floor=1.0)
    assert {flat.velocity(speed) for speed in (0, 300, 800, 2000)} == {1.0}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"soft_speed_px_per_s": 500.0, "hard_speed_px_per_s": 500.0},
        {"soft_speed_px_per_s": 800.0, "hard_speed_px_per_s": 500.0},
        {"soft_speed_px_per_s": -1.0},
        {"floor": 1.5},
        {"floor": -0.1},
        {"floor": 0.0},
        {"gamma": 0.0},
        {"gamma": -1.0},
    ],
)
def test_an_incoherent_curve_is_refused(kwargs):
    with pytest.raises(ValueError):
        VelocityCurve(**kwargs)


# --- Fenêtre de vitesse ------------------------------------------------------------


def test_the_window_reports_the_fastest_downward_move():
    window = SpeedWindow()
    for t_s, y in [(0.00, 50.0), (0.03, 55.0), (0.06, 80.0), (0.09, 90.0)]:
        window.add(t_s, y)
    assert window.peak_downward_speed() == pytest.approx(25.0 / 0.03)


def test_the_window_ignores_upward_moves():
    window = SpeedWindow()
    for t_s, y in [(0.00, 100.0), (0.03, 60.0), (0.06, 20.0)]:
        window.add(t_s, y)
    assert window.peak_downward_speed() == 0.0


def test_the_window_needs_two_points():
    window = SpeedWindow()
    assert window.peak_downward_speed() == 0.0
    window.add(0.0, 50.0)
    assert window.peak_downward_speed() == 0.0


def test_the_window_keeps_the_peak_even_if_the_last_move_is_slower():
    window = SpeedWindow()
    for t_s, y in [(0.00, 0.0), (0.03, 40.0), (0.06, 44.0)]:
        window.add(t_s, y)
    assert window.peak_downward_speed() == pytest.approx(40.0 / 0.03)


def test_the_window_forgets_what_is_older_than_its_length():
    window = SpeedWindow()
    window.add(0.0, 0.0)
    window.add(0.03, 60.0)  # descente rapide
    window.add(0.03 + PEAK_WINDOW_S + 0.05, 61.0)
    window.add(0.03 + PEAK_WINDOW_S + 0.08, 62.0)  # puis presque immobile
    assert window.peak_downward_speed() == pytest.approx(1.0 / 0.03)


def test_the_window_can_be_reset():
    window = SpeedWindow()
    window.add(0.0, 0.0)
    window.add(0.03, 60.0)
    window.reset()
    assert window.peak_downward_speed() == 0.0


# --- Réglages ----------------------------------------------------------------------


def test_the_curve_comes_from_the_settings_when_enabled():
    settings = VelocitySettings(soft_speed=150.0, hard_speed=700.0, floor=0.4, gamma=1.5)
    assert curve_from_settings(settings) == VelocityCurve(150.0, 700.0, 0.4, 1.5)


def test_a_disabled_nuance_gives_no_curve():
    assert curve_from_settings(VelocitySettings(enabled=False)) is None


def test_default_velocity_settings_make_a_valid_curve():
    assert curve_from_settings(VelocitySettings()) == VelocityCurve()


def test_velocity_defaults_without_a_velocity_section(tmp_path):
    target = tmp_path / "settings.toml"
    target.write_text("volume = 0.5\n", encoding="utf-8")
    assert load_settings(target).velocity == VelocitySettings()


def test_velocity_section_is_read(tmp_path):
    target = tmp_path / "settings.toml"
    target.write_text(
        "[velocity]\nenabled = false\nsoft_speed = 150\nhard_speed = 700.5\n"
        "floor = 0.5\ngamma = 2\n",
        encoding="utf-8",
    )
    assert load_settings(target).velocity == VelocitySettings(
        enabled=False, soft_speed=150.0, hard_speed=700.5, floor=0.5, gamma=2.0
    )


def test_velocity_section_may_set_only_some_values(tmp_path):
    target = tmp_path / "settings.toml"
    target.write_text("[velocity]\nhard_speed = 1500\n", encoding="utf-8")
    velocity = load_settings(target).velocity
    assert velocity.hard_speed == 1500.0
    assert velocity.soft_speed == VelocitySettings().soft_speed
    assert velocity.enabled is True


@pytest.mark.parametrize(
    "section",
    [
        "soft_speed = 900\nhard_speed = 200\n",  # courbe à l'envers
        "floor = 3\n",
        "floor = -1\n",
        "floor = 0\n",
        "gamma = 0\n",
        'soft_speed = "doux"\n',
        "soft_speed = true\n",
    ],
)
def test_an_incoherent_velocity_section_falls_back_to_the_defaults(tmp_path, section):
    target = tmp_path / "settings.toml"
    target.write_text(f"[velocity]\n{section}", encoding="utf-8")
    assert load_settings(target).velocity == VelocitySettings()


def test_an_incoherent_section_still_respects_enabled(tmp_path):
    target = tmp_path / "settings.toml"
    target.write_text("[velocity]\nenabled = false\nfloor = 3\n", encoding="utf-8")
    velocity = load_settings(target).velocity
    assert velocity.enabled is False
    assert velocity.floor == VelocitySettings().floor


def test_default_template_documents_the_velocity_without_activating_the_section(tmp_path):
    target = tmp_path / "settings.toml"
    load_settings(target)
    text = target.read_text(encoding="utf-8")
    assert "# [velocity]" in text and "\n[velocity]" not in text
    assert load_settings(target).velocity == VelocitySettings()


def test_velocity_settings_round_trip(tmp_path):
    target = tmp_path / "settings.toml"
    original = Settings(velocity=VelocitySettings(enabled=False, hard_speed=1200.0, gamma=0.7))
    save_settings(original, target)
    assert load_settings(target).velocity == original.velocity


# --- Traitement : la vitesse du geste devient le volume du coup ---------------------


class _Clock:
    """Horloge factice : 20 ms par image (le traitement lit l'heure deux fois par image)."""

    def __init__(self) -> None:
        self._now = 0

    def __call__(self) -> int:
        value = self._now
        self._now += 10_000_000
        return value


GREEN_BGR = tuple(
    int(c) for c in cv2.cvtColor(np.uint8([[[60, 200, 200]]]), cv2.COLOR_HSV2BGR)[0][0]
)
PLANE_Y = 100.0


def _right_hand_frame(y: int) -> np.ndarray:
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    frame[y - 10 : y + 10, 140:160] = GREEN_BGR
    return frame


def _hits(spec: MarkerSpec, ys: list[int]) -> list[MarkerSample]:
    frames = [_right_hand_frame(y) for y in ys]
    samples = track_markers(iter(frames), [spec], now_ns=_Clock(), working_width=None)
    return [sample.markers[spec.name] for sample in samples if sample.hit_event is not None]


SLOW = [60, 70, 80, 90, 105]  # 10 px par image de 20 ms = 500 px/s, 750 px/s au dernier pas
FAST = [60, 60, 60, 80, 120]  # 1000 px/s puis 2000 px/s
CURVE_FOR_TRACKING = VelocityCurve(200.0, 1000.0, 0.2, 1.0)


def test_a_hit_carries_the_speed_of_the_gesture_and_the_volume_it_gives():
    spec = MarkerSpec("right", GREEN, PLANE_Y, velocity_curve=CURVE_FOR_TRACKING)

    [slow] = _hits(spec, SLOW)
    [fast] = _hits(spec, FAST)

    assert slow.hit_speed_px_per_s == pytest.approx(750.0, rel=0.05)
    assert fast.hit_speed_px_per_s == pytest.approx(2000.0, rel=0.05)
    assert slow.hit_event is not None and fast.hit_event is not None
    assert slow.hit_event.velocity == pytest.approx(CURVE_FOR_TRACKING.velocity(750.0), rel=0.05)
    assert 0.2 < slow.hit_event.velocity < 1.0
    assert fast.hit_event.velocity == 1.0


def test_a_softer_gesture_sounds_softer():
    spec = MarkerSpec("right", GREEN, PLANE_Y, velocity_curve=CURVE_FOR_TRACKING)
    [slow] = _hits(spec, SLOW)
    [fast] = _hits(spec, FAST)
    assert slow.hit_event.velocity < fast.hit_event.velocity  # type: ignore[union-attr]


def test_without_a_curve_every_hit_sounds_at_full_volume():
    spec = MarkerSpec("right", GREEN, PLANE_Y)
    [slow] = _hits(spec, SLOW)
    assert slow.hit_event.velocity == 1.0  # type: ignore[union-attr]
    assert slow.hit_speed_px_per_s is not None  # la vitesse est mesurée quand même


def test_the_speed_is_the_peak_just_before_the_hit_not_the_last_step():
    # Descente rapide puis ralentie au moment de franchir le plan : le coup a bien été donné
    # vite, la vitesse du dernier pas seul le sous-estimerait.
    spec = MarkerSpec("right", GREEN, PLANE_Y, velocity_curve=CURVE_FOR_TRACKING)
    [hit] = _hits(spec, [60, 60, 60, 85, 95, 104])
    assert hit.hit_speed_px_per_s == pytest.approx(1250.0, rel=0.05)


def test_a_frame_without_a_hit_has_no_hit_speed():
    spec = MarkerSpec("right", GREEN, PLANE_Y, velocity_curve=CURVE_FOR_TRACKING)
    samples = track_markers(
        iter([_right_hand_frame(y) for y in (50, 50, 50)]),
        [spec],
        now_ns=_Clock(),
        working_width=None,
    )
    assert all(s.markers["right"].hit_speed_px_per_s is None for s in samples)


def test_the_volume_also_follows_the_gesture_when_hits_are_attributed_by_zones():
    zones = ZoneMap((Zone("ride", 120, 180, y_top=40, strike_plane_y=PLANE_Y, y_bottom=180),))
    spec = MarkerSpec("right", GREEN, PLANE_Y, zones=zones, velocity_curve=CURVE_FOR_TRACKING)

    [slow] = _hits(spec, SLOW)
    [fast] = _hits(spec, FAST)

    assert slow.hit_event is not None and fast.hit_event is not None
    assert slow.hit_event.element_id == fast.hit_event.element_id == "ride"
    assert slow.hit_event.velocity < fast.hit_event.velocity == 1.0


def test_both_hands_get_the_curve():
    specs = hand_specs(None, CURVE_FOR_TRACKING)
    assert [spec.velocity_curve for spec in specs] == [CURVE_FOR_TRACKING] * 2
    assert [spec.velocity_curve for spec in hand_specs()] == [None, None]


# --- Écran « Jeu caméra » ----------------------------------------------------------

ZONES = ZoneMap((Zone("snare", 60.0, 140.0, 50.0, 100.0, 140.0),))


class FakeEngine:
    def __init__(self) -> None:
        self.played: list[tuple[str, float]] = []

    def play(self, element_id: str, velocity: float = 1.0) -> None:
        self.played.append((element_id, velocity))


def _hit_sample(velocity: float, speed: float | None) -> VisionSample:
    hit = HitEvent("snare", velocity, 0, Source.VISION)
    return VisionSample(
        t_ns=0,
        markers={
            "left": MarkerSample(TrackedPoint(100.0, 80.0, 300.0), 0.0, hit, speed),
            "right": MarkerSample(None, 0.0, None),
        },
        fps=30.0,
        processing_ms=1.0,
        frame_preview=np.zeros((180, WORKING_WIDTH, 3), dtype=np.uint8),
    )


@pytest.fixture
def screen_parts():
    pygame.init()
    queue, engine = FakeQueue(), FakeEngine()
    screen = CameraPlayScreen(VisionFeed(queue, FakeProcess()), ZONES, engine, KitView())
    yield screen, queue, engine
    pygame.quit()


def test_the_engine_plays_each_hit_at_the_volume_the_gesture_gave(screen_parts):
    screen, queue, engine = screen_parts
    queue.items += [_hit_sample(0.45, 520.0), _hit_sample(1.0, 1400.0)]

    screen.update([])

    assert engine.played == [("snare", 0.45), ("snare", 1.0)]


def test_the_screen_remembers_the_last_hit_speed_and_volume(screen_parts):
    screen, queue, _ = screen_parts
    queue.items += [_hit_sample(0.45, 520.0), _hit_sample(0.8, 700.0)]

    screen.update([])

    assert screen.last_hit == LastHit("snare", 700.0, 0.8)


def test_the_nuance_lines_guide_the_tuning(screen_parts):
    screen, queue, _ = screen_parts
    assert "désactivée" in screen._nuance_lines()[0]

    screen.nuance = True
    assert "joue un coup" in screen._nuance_lines()[0]

    queue.items.append(_hit_sample(0.45, 520.0))
    screen.update([])
    assert screen._nuance_lines() == [
        "dernier coup : Caisse claire",
        "  vitesse 520 px/s -> volume 45 %",
    ]


def test_the_screen_draws_with_the_nuance_on(screen_parts):
    screen, queue, _ = screen_parts
    surface = pygame.display.set_mode((1280, 720))
    screen.nuance = True
    queue.items.append(_hit_sample(0.45, 520.0))
    screen.update([])
    screen.draw(surface, surface.get_rect())


@pytest.fixture
def started(monkeypatch):
    pygame.init()
    calls: list[dict] = []

    def fake_start(specs, **kwargs):
        calls.append({"specs": specs, **kwargs})
        return VisionFeed(FakeQueue(), FakeProcess())

    monkeypatch.setattr(camera_play.VisionFeed, "start", staticmethod(fake_start))
    yield calls
    pygame.quit()


def _open_with(tmp_path, velocity):
    from batterie.config.settings import CameraSettings
    from batterie.config.zones import save_zones

    zones_file = tmp_path / "zones.toml"
    save_zones(ZONES, zones_file, working_width=WORKING_WIDTH)
    return CameraPlayScreen.open(
        FakeEngine(), KitView(), CameraSettings(), velocity=velocity, zones_file=zones_file
    )


def test_opening_the_screen_gives_the_settings_curve_to_both_hands(tmp_path, started):
    settings = VelocitySettings(soft_speed=150.0, hard_speed=700.0)

    screen = _open_with(tmp_path, settings)

    (call,) = started
    assert [spec.velocity_curve for spec in call["specs"]] == [curve_from_settings(settings)] * 2
    assert screen.nuance is True


def test_a_disabled_nuance_opens_the_screen_without_a_curve(tmp_path, started):
    screen = _open_with(tmp_path, VelocitySettings(enabled=False))

    assert [spec.velocity_curve for spec in started[0]["specs"]] == [None, None]
    assert screen.nuance is False


def test_opening_without_velocity_settings_keeps_every_hit_at_full_volume(tmp_path, started):
    screen = _open_with(tmp_path, None)

    assert [spec.velocity_curve for spec in started[0]["specs"]] == [None, None]
    assert screen.nuance is False
