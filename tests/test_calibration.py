"""Tests de la calibration guidée : repérage des coups, calcul des zones, déroulé complet.

Trajectoires synthétiques, aucune caméra. Les coups imitent un geste réel : l'embout reste en
haut, descend vite, remonte.
"""

import math

import pytest

from batterie.input.vision.calibration import (
    CALIBRATION_ELEMENTS,
    SETTLE_S,
    CalibrationError,
    CalibrationRun,
    Stroke,
    StrokeSegmenter,
    zone_from_strokes,
    zones_from_strokes,
)
from batterie.input.vision.color_tracker import TrackedPoint
from batterie.input.vision.process import MarkerSample, VisionSample
from batterie.input.vision.zones import ZoneStrikeDetector

FPS = 30
DT = 1 / FPS


def _stroke_path(t0: float, x: float, top: float, bottom: float, duration: float = 0.4):
    """Un coup : un temps de repos en haut, la descente puis la remontée, puis un repos."""
    steps = round(duration * FPS)  # pair : le point bas tombe sur une image
    samples = []
    t = t0
    for _ in range(4):  # repos avant
        samples.append((t, x, top))
        t += DT
    for i in range(1, steps + 1):
        u = i / steps
        samples.append((t, x, top + (bottom - top) * (1 - math.cos(2 * math.pi * u)) / 2))
        t += DT
    for _ in range(4):  # repos après
        samples.append((t, x, top))
        t += DT
    return samples


def _segment(samples) -> list[Stroke]:
    segmenter = StrokeSegmenter()
    return [s for s in (segmenter.update(*p) for p in samples) if s is not None]


def _stroke(x: float, top: float, bottom: float, t_s: float = 0.0) -> Stroke:
    return Stroke(t_s=t_s, x=x, top_y=top, bottom_y=bottom, peak_speed_px_per_s=500.0)


# --- Repérage des coups ---------------------------------------------------------


def test_a_stroke_is_found_with_its_contact_point_and_course():
    [stroke] = _segment(_stroke_path(0.0, x=120.0, top=60.0, bottom=150.0))
    assert stroke.x == 120.0
    assert stroke.top_y == pytest.approx(60.0)
    assert stroke.bottom_y == pytest.approx(150.0)
    assert stroke.peak_speed_px_per_s > 150


def test_the_contact_x_is_where_the_marker_is_at_the_lowest_point():
    samples = _stroke_path(0.0, x=100.0, top=60.0, bottom=150.0)
    # L'embout dérive vers la droite pendant la descente : le coup compte là où il touche.
    drifting = [(t, x + 3.0 * i, y) for i, (t, x, y) in enumerate(samples)]
    [stroke] = _segment(drifting)
    lowest = max(drifting, key=lambda p: p[2])
    assert stroke.x == lowest[1]


def test_several_strokes_are_found_one_by_one():
    samples = []
    for index in range(3):
        samples += _stroke_path(index * 1.0, x=120.0, top=60.0, bottom=150.0)
    assert len(_segment(samples)) == 3


def test_hovering_with_jitter_is_not_a_stroke():
    jitter = [(i * DT, 120.0, 100.0 + 2.0 * (-1) ** i) for i in range(90)]
    assert _segment(jitter) == []


def test_a_slow_drift_downward_is_not_a_stroke():
    # 60 px en 3 s : assez de course, bien trop lent pour un coup.
    drift = [(i * DT, 120.0, 80.0 + 0.67 * i) for i in range(90)]
    drift += [(3.0 + i * DT, 120.0, 140.0 - 0.67 * i) for i in range(90)]
    assert _segment(drift) == []


def test_a_tiny_movement_is_not_a_stroke():
    assert _segment(_stroke_path(0.0, x=120.0, top=100.0, bottom=115.0)) == []


def test_losing_the_marker_forgets_the_movement_in_progress():
    segmenter = StrokeSegmenter()
    samples = _stroke_path(0.0, x=120.0, top=60.0, bottom=150.0)
    midway = samples[: len(samples) // 2]
    assert [segmenter.update(*p) for p in midway].count(None) == len(midway)
    segmenter.reset()
    # Une remontée isolée après la perte ne doit pas valider le coup commencé avant.
    assert segmenter.update(5.0, 120.0, 70.0) is None
    assert segmenter.update(5.03, 120.0, 60.0) is None


# --- Calcul d'une zone -----------------------------------------------------------


def test_zone_covers_the_strokes_with_a_margin_and_the_plane_sits_inside_the_course():
    strokes = [_stroke(100, 60, 150), _stroke(110, 70, 140), _stroke(105, 65, 155)]
    zone = zone_from_strokes("snare", strokes)
    assert zone.x_min == 80.0  # 100 - 20
    assert zone.x_max == 130.0  # 110 + 20
    assert zone.y_top == 70.0  # le coup le moins relevé
    assert zone.y_bottom == 155.0
    assert zone.strike_plane_y == pytest.approx(70.0 + 0.6 * (140.0 - 70.0))


def test_zone_is_clipped_to_the_image():
    strokes = [_stroke(5, 60, 150), _stroke(8, 60, 150), _stroke(300, 60, 150)]
    with pytest.raises(CalibrationError):
        zone_from_strokes("snare", strokes)  # trop dispersés
    near_edge = [_stroke(5, 60, 150), _stroke(8, 60, 150), _stroke(10, 60, 150)]
    assert zone_from_strokes("snare", near_edge).x_min == 0.0
    right_edge = [_stroke(312, 60, 150), _stroke(315, 60, 150), _stroke(318, 60, 150)]
    assert zone_from_strokes("snare", right_edge, working_width=320).x_max == 320.0


def test_too_few_strokes_are_refused():
    with pytest.raises(CalibrationError, match="3 coups, 2 reçus"):
        zone_from_strokes("snare", [_stroke(100, 60, 150), _stroke(100, 60, 150)])


def test_strokes_that_are_too_far_apart_are_refused_with_advice():
    strokes = [_stroke(40, 60, 150), _stroke(100, 60, 150), _stroke(180, 60, 150)]
    with pytest.raises(CalibrationError, match="même endroit"):
        zone_from_strokes("snare", strokes)


def test_irregular_strokes_whose_courses_do_not_overlap_are_refused():
    # Le moins relevé part de y=125, le moins profond s'arrête à y=140 : 15 px de course commune.
    strokes = [_stroke(100, 60, 140), _stroke(100, 125, 155), _stroke(100, 70, 150)]
    with pytest.raises(CalibrationError, match="trop petits ou trop irréguliers"):
        zone_from_strokes("snare", strokes)


def test_error_messages_name_the_element_in_french():
    with pytest.raises(CalibrationError, match="Caisse claire"):
        zone_from_strokes("snare", [])


# --- Plusieurs zones : frontières ---------------------------------------------------


def test_neighbouring_zones_that_overlap_are_split_halfway_between_the_strokes():
    zone_map = zones_from_strokes(
        {
            "snare": [_stroke(100, 60, 150), _stroke(110, 60, 150), _stroke(120, 60, 150)],
            "tom_mid": [_stroke(130, 60, 150), _stroke(140, 60, 150), _stroke(150, 60, 150)],
        }
    )
    snare, tom = zone_map.get("snare"), zone_map.get("tom_mid")
    assert snare.x_max == 125.0 and tom.x_min == 125.0  # entre 120 et 130
    assert snare.x_min == 80.0 and tom.x_max == 170.0  # l'autre bord garde sa marge


def test_zones_that_do_not_overlap_keep_their_own_margins():
    zone_map = zones_from_strokes(
        {
            "snare": [_stroke(50, 60, 150), _stroke(55, 60, 150), _stroke(60, 60, 150)],
            "ride": [_stroke(250, 60, 150), _stroke(255, 60, 150), _stroke(260, 60, 150)],
        }
    )
    assert zone_map.get("snare").x_max == 80.0
    assert zone_map.get("ride").x_min == 230.0


def test_interleaved_strokes_cannot_be_split():
    with pytest.raises(CalibrationError, match="se mélangent"):
        zones_from_strokes(
            {
                "snare": [_stroke(100, 60, 150), _stroke(130, 60, 150), _stroke(110, 60, 150)],
                "tom_mid": [_stroke(120, 60, 150), _stroke(125, 60, 150), _stroke(135, 60, 150)],
            }
        )


# --- Déroulé complet ---------------------------------------------------------------


def _sample(t_s: float, left=None, right=None) -> VisionSample:
    def marker(position):
        point = TrackedPoint(position[0], position[1], 300.0) if position else None
        return MarkerSample(point, 0.0, None)

    return VisionSample(
        t_ns=round(t_s * 1_000_000_000),
        markers={"left": marker(left), "right": marker(right)},
        fps=float(FPS),
        processing_ms=1.0,
    )


def _play(run: CalibrationRun, samples, hand: str = "left") -> None:
    for t, x, y in samples:
        position = (x, y)
        run.handle_sample(
            _sample(t, left=position) if hand == "left" else _sample(t, right=position)
        )


# Où l'utilisateur frappe chaque élément (de gauche à droite), et sa course.
KIT_X = {"hihat_closed": 45.0, "snare": 115.0, "tom_mid": 195.0, "ride": 275.0}


def _calibrate_everything(run: CalibrationRun) -> float:
    """Donne 3 coups à chaque élément, en alternant les mains. Renvoie le temps final."""
    t = 0.0
    for element_id in CALIBRATION_ELEMENTS:
        for index in range(3):
            tops = (60.0, 68.0, 64.0)
            bottoms = (150.0, 142.0, 156.0)
            samples = _stroke_path(t, KIT_X[element_id] + index * 3, tops[index], bottoms[index])
            _play(run, samples, hand="left" if index % 2 == 0 else "right")
            t = samples[-1][0] + 0.4
        t += SETTLE_S + 0.5
    return t


def test_run_goes_through_the_four_elements_in_order():
    run = CalibrationRun()
    assert run.current_element == "hihat_closed"
    assert not run.finished
    _calibrate_everything(run)
    assert run.finished
    assert run.current_element is None
    assert [z.element_id for z in run.result()] == list(CALIBRATION_ELEMENTS)


def test_run_progress_is_reported_stroke_by_stroke():
    run = CalibrationRun()
    samples = _stroke_path(0.0, 45.0, 60.0, 150.0) + _stroke_path(1.0, 45.0, 60.0, 150.0)
    _play(run, samples)
    assert run.strokes_done == 2
    assert run.strokes_needed == 3
    assert len(run.contacts) == 2


def test_strokes_from_either_hand_count_for_the_current_element():
    run = CalibrationRun()
    _play(run, _stroke_path(0.0, 45.0, 60.0, 150.0), hand="left")
    _play(run, _stroke_path(1.0, 48.0, 60.0, 150.0), hand="right")
    assert run.strokes_done == 2


def test_the_calibrated_zones_catch_the_strokes_that_defined_them():
    run = CalibrationRun()
    _calibrate_everything(run)
    zones = run.result()

    for element_id in CALIBRATION_ELEMENTS:
        for index, (top, bottom) in enumerate(
            zip((60.0, 68.0, 64.0), (150.0, 142.0, 156.0), strict=True)
        ):
            detector = ZoneStrikeDetector(zones)
            path = _stroke_path(0.0, KIT_X[element_id] + index * 3, top, bottom)
            hits = [z.element_id for z in (detector.update(*p) for p in path) if z]
            assert hits == [element_id], (element_id, index)


def test_a_zone_that_cannot_be_built_is_reported_and_only_that_element_restarts():
    run = CalibrationRun()
    t = 0.0
    for x in (45.0, 45.0, 200.0):  # le 3e coup est loin des deux autres
        samples = _stroke_path(t, x, 60.0, 150.0)
        _play(run, samples)
        t = samples[-1][0] + 0.4

    assert "même endroit" in run.message
    assert "On recommence cet élément" in run.message
    assert run.current_element == "hihat_closed"
    assert run.strokes_done == 0
    assert not run.finished


def test_after_an_error_the_next_good_strokes_continue_the_calibration():
    run = CalibrationRun()
    t = 0.0
    for x in (45.0, 45.0, 200.0, 45.0, 47.0, 49.0):
        samples = _stroke_path(t, x, 60.0, 150.0)
        _play(run, samples)
        t = samples[-1][0] + 0.4
    assert run.current_element == "snare"
    assert run.message == ""


def test_strokes_right_after_an_element_is_done_are_ignored_while_the_user_moves_on():
    run = CalibrationRun()
    t = 0.0
    for _ in range(3):
        samples = _stroke_path(t, 45.0, 60.0, 150.0)
        _play(run, samples)
        t = samples[-1][0] + 0.1
    assert run.current_element == "snare"
    # Un 4e coup sur le charleston, tout de suite : ne compte pas pour la caisse claire.
    samples = _stroke_path(t, 45.0, 60.0, 150.0)
    _play(run, samples)
    assert run.strokes_done == 0


def test_restart_current_clears_only_the_current_element():
    run = CalibrationRun()
    _calibrate_everything_first = _stroke_path(0.0, 45.0, 60.0, 150.0)
    _play(run, _calibrate_everything_first)
    assert run.strokes_done == 1
    run.restart_current()
    assert run.strokes_done == 0
    assert run.current_element == "hihat_closed"


def test_result_before_the_end_is_refused():
    with pytest.raises(CalibrationError):
        CalibrationRun().result()


def test_a_lost_marker_does_not_break_the_run():
    run = CalibrationRun()
    run.handle_sample(_sample(0.0))  # aucune main visible
    _play(run, _stroke_path(0.1, 45.0, 60.0, 150.0))
    assert run.strokes_done == 1


def test_the_run_can_calibrate_a_custom_list_of_elements():
    run = CalibrationRun(elements=("snare",), strokes_per_element=3)
    t = 0.0
    for index in range(3):
        samples = _stroke_path(t, 120.0 + index, 60.0, 150.0)
        _play(run, samples)
        t = samples[-1][0] + 0.4
    assert run.finished
    assert len(run.result()) == 1


def test_a_run_needs_at_least_one_element():
    with pytest.raises(ValueError):
        CalibrationRun(elements=())
