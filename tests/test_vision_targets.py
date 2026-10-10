"""Tests des préréglages de cible (baguette / pied) : sans caméra, sans fenêtre."""

import math

import pytest

import vision_debug
import vision_measure
from batterie.input.vision.color_tracker import GREEN, ORANGE, TrackedPoint
from batterie.input.vision.process import MarkerSample, MarkerSpec, VisionSample
from batterie.input.vision.strike_detector import StrikeDetector

FRAME_DT_S = 1 / 30  # webcam intégrée : ~30 images/s (31,2 mesurées en phase 03)
TAP_PERIOD_S = 0.75  # un coup par temps à 80 BPM
FOOT_AMPLITUDE_PX = 18.0  # pointe du pied : quelques dizaines de pixels d'amplitude au plus
SAMPLE_OFFSET_S = 0.004  # évite d'échantillonner pile sur le plan de frappe


def _detector_for(preset: vision_debug.MarkerPreset) -> StrikeDetector:
    return StrikeDetector(
        strike_plane_y=preset.strike_plane_y,
        min_speed_px_per_s=preset.min_speed_px_per_s,
        refractory_s=preset.refractory_s,
    )


def _foot_taps(preset: vision_debug.MarkerPreset, taps: int, amplitude_px: float):
    """Trajectoire (t, y) d'une pointe de pied qui frappe ``taps`` fois, une fois par
    ``TAP_PERIOD_S``, à ``FRAME_DT_S`` d'intervalle. Elle franchit le plan vers le bas
    (y croissant) au début de chaque période ; amplitude faible, mouvement lent."""
    frames = round(taps * TAP_PERIOD_S / FRAME_DT_S) + 2
    for index in range(frames):
        t_s = index * FRAME_DT_S + SAMPLE_OFFSET_S
        phase = 2 * math.pi * t_s / TAP_PERIOD_S
        yield t_s, preset.strike_plane_y + amplitude_px * math.sin(phase)


def _count_hits(detector: StrikeDetector, trajectory) -> int:
    return sum(detector.update(t_s, y) for t_s, y in trajectory)


# --- Sélection du préréglage ------------------------------------------------


def test_stick_is_the_default_target():
    assert vision_debug.parse_arguments([]) is vision_debug.STICK
    target, simulate = vision_measure.parse_arguments([])
    assert target is vision_debug.STICK
    assert simulate is False


def test_target_argument_selects_the_preset_in_both_tools():
    assert vision_debug.parse_arguments(["--target", "foot"]) is vision_debug.FOOT
    assert vision_debug.parse_arguments(["--target", "stick"]) is vision_debug.STICK
    target, simulate = vision_measure.parse_arguments(["--target", "foot", "--simulate"])
    assert target is vision_debug.FOOT
    assert simulate is True


def test_unknown_target_is_rejected():
    with pytest.raises(SystemExit):
        vision_debug.parse_arguments(["--target", "head"])


def test_presets_map_to_the_right_drum_elements():
    assert vision_debug.STICK.markers[0].element_id == "snare"
    assert vision_debug.FOOT.markers[0].element_id == "kick"
    assert set(vision_debug.TARGETS) == {"stick", "foot", "hands"}


def test_foot_and_stick_track_the_same_color_during_the_foot_test():
    assert vision_debug.FOOT.markers[0].color_range == vision_debug.STICK.markers[0].color_range


def test_stick_preset_keeps_the_detector_defaults():
    from batterie.input.vision.strike_detector import (
        DEFAULT_MIN_SPEED_PX_PER_S,
        DEFAULT_REFRACTORY_S,
    )

    assert vision_debug.STICK.markers[0].min_speed_px_per_s == DEFAULT_MIN_SPEED_PX_PER_S
    assert vision_debug.STICK.markers[0].refractory_s == DEFAULT_REFRACTORY_S


def test_foot_preset_expects_shorter_and_slower_movement_than_the_stick():
    assert (
        vision_debug.FOOT.markers[0].min_speed_px_per_s
        < vision_debug.STICK.markers[0].min_speed_px_per_s
    )
    assert vision_debug.FOOT.markers[0].refractory_s > vision_debug.STICK.markers[0].refractory_s


# --- Le préréglage pied sur des trajectoires de pied -------------------------


def test_foot_preset_detects_every_small_slow_tap():
    trajectory = _foot_taps(vision_debug.FOOT.markers[0], taps=10, amplitude_px=FOOT_AMPLITUDE_PX)
    assert _count_hits(_detector_for(vision_debug.FOOT.markers[0]), trajectory) == 10


def test_stick_preset_misses_the_same_foot_taps():
    # Preuve que le préréglage pied est nécessaire : avec les seuils de la baguette,
    # un geste de pied de cette amplitude ne dépasse pas la vitesse minimale.
    trajectory = _foot_taps(vision_debug.STICK.markers[0], taps=10, amplitude_px=FOOT_AMPLITUDE_PX)
    assert _count_hits(_detector_for(vision_debug.STICK.markers[0]), trajectory) == 0


def test_foot_preset_still_detects_a_faster_stronger_tap():
    trajectory = _foot_taps(vision_debug.FOOT.markers[0], taps=10, amplitude_px=45.0)
    assert _count_hits(_detector_for(vision_debug.FOOT.markers[0]), trajectory) == 10


def test_foot_preset_ignores_sub_pixel_jitter_around_the_plane():
    plane = vision_debug.FOOT.markers[0].strike_plane_y
    detector = _detector_for(vision_debug.FOOT.markers[0])
    jitter = ((index * FRAME_DT_S, plane + 0.5 * (-1) ** index) for index in range(300))
    assert _count_hits(detector, jitter) == 0


def test_foot_preset_merges_two_crossings_closer_than_its_refractory_period():
    def two_quick_dips(plane: float):
        # Deux descentes rapides à 0,167 s d'intervalle : un rebond pour le pied (0,20 s),
        # deux vrais coups pour la baguette (0,15 s).
        return [
            (0.000, plane - 10),
            (0.033, plane + 10),
            (0.100, plane - 10),
            (0.167, plane - 10),
            (0.200, plane + 10),
        ]

    foot, stick = vision_debug.FOOT.markers[0], vision_debug.STICK.markers[0]
    assert _count_hits(_detector_for(foot), two_quick_dips(foot.strike_plane_y)) == 1
    assert _count_hits(_detector_for(stick), two_quick_dips(stick.strike_plane_y)) == 2


# --- Deux mains (phase 04) ---------------------------------------------------


def test_hands_target_tracks_orange_on_the_left_and_green_on_the_right():
    left, right = vision_debug.HANDS.markers
    assert (left.name, left.color_range) == ("left", ORANGE)
    assert (right.name, right.color_range) == ("right", GREEN)


def test_only_the_hands_target_is_mirrored():
    assert vision_debug.HANDS.mirror is True
    assert vision_debug.STICK.mirror is False
    assert vision_debug.FOOT.mirror is False


def test_hands_target_is_selected_in_both_tools():
    assert vision_debug.parse_arguments(["--target", "hands"]) is vision_debug.HANDS
    target, _ = vision_measure.parse_arguments(["--target", "hands"])
    assert target is vision_debug.HANDS


def test_marker_presets_become_process_specs_with_their_own_thresholds():
    specs = vision_debug.FOOT.specs()
    assert specs == [
        MarkerSpec(
            name="foot",
            color_range=vision_debug.MARKER_COLOR,
            strike_plane_y=100.0,
            element_id="kick",
            min_speed_px_per_s=80.0,
            refractory_s=0.20,
        )
    ]
    assert [spec.name for spec in vision_debug.HANDS.specs()] == ["left", "right"]


def test_describe_names_the_element_only_for_a_single_marker():
    assert vision_debug.FOOT.describe() == "pied (kick)"
    assert vision_debug.HANDS.describe() == "deux mains"


def _hands_sample() -> VisionSample:
    return VisionSample(
        t_ns=0,
        markers={
            "left": MarkerSample(TrackedPoint(100.0, 80.0, 400.0), 250.0, None),
            "right": MarkerSample(None, 0.0, None),
        },
        fps=30.0,
        processing_ms=1.5,
    )


def test_sidebar_for_two_hands_reports_each_hand_separately():
    lines = vision_debug.sidebar_lines(vision_debug.HANDS, _hands_sample(), {"left": 7, "right": 5})
    text = "\n".join(lines)
    assert "Coups détectés : 12" in text
    assert "Main gauche (orange) : 7 coups" in text
    assert "Main droite (verte) : 5 coups" in text
    assert "(100, 80)" in text  # la main gauche est vue
    assert "non détecté" in text  # la main droite ne l'est pas


def test_sidebar_before_the_first_image_does_not_crash():
    lines = vision_debug.sidebar_lines(vision_debug.HANDS, None, {"left": 0, "right": 0})
    assert any("Images/s : —" in line for line in lines)
