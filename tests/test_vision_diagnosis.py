"""Tests du diagnostic des coups manqués : trajectoires synthétiques, aucune caméra."""

import pytest

from batterie.core.events import Source
from batterie.input.vision.diagnosis import (
    MissCause,
    MissDiagnosis,
    diagnose_click,
    diagnose_misses,
    summarize_causes,
)
from batterie.input.vision.measure import (
    EARLY_DETECTION_MARGIN_MS,
    US7_PLAN,
    SessionRecorder,
    format_report,
    hand_for_click,
    hand_stats,
    position_stats,
    us7_checks,
)
from batterie.input.vision.zones import Zone, ZoneMap

ZONE = Zone("snare", 100.0, 160.0, y_top=40.0, strike_plane_y=100.0, y_bottom=150.0)
CLICK_S = 2.0
TOLERANCE_S = 0.2
FRAME_S = 1 / 30  # 30 images/s


def _frames(start: float = 1.5, end: float = 2.3):
    t = start
    while t <= end:
        yield t
        t += FRAME_S


def _stroke(x: float, depth: float, *, bottom_at: float = CLICK_S, half_s: float = 0.2):
    """Aller-retour triangulaire autour de ``bottom_at`` : y va de 50 à 50 + depth."""
    points = []
    for t in _frames():
        dt = abs(t - bottom_at)
        y = 50.0 + depth * max(0.0, 1.0 - dt / half_s)
        points.append((t, x, y))
    return points


def _diagnose(trajectory, **kwargs):
    return diagnose_click(3, ZONE, trajectory, click_s=CLICK_S, tolerance_s=TOLERANCE_S, **kwargs)


# --- Les six causes ----------------------------------------------------------------


def test_a_clean_stroke_in_the_zone_leaves_nothing_abnormal_to_find():
    diagnosis = _diagnose(_stroke(130.0, depth=90.0))
    assert diagnosis == MissDiagnosis(3, MissCause.OTHER)


def test_a_marker_that_is_not_seen_is_reported_as_such():
    trajectory = [(t, None, None) for t in _frames()]
    assert _diagnose(trajectory).cause is MissCause.NOT_SEEN


def test_no_frame_at_all_is_reported_as_not_seen():
    assert _diagnose([]).cause is MissCause.NOT_SEEN


def test_a_marker_seen_only_half_of_the_time_is_reported_as_not_seen():
    stroke = _stroke(130.0, depth=90.0)
    lost = [(t, None, None) if index % 3 else (t, x, y) for index, (t, x, y) in enumerate(stroke)]
    assert _diagnose(lost).cause is MissCause.NOT_SEEN


def test_a_stroke_that_stops_short_of_the_plane_says_by_how_much():
    diagnosis = _diagnose(_stroke(130.0, depth=40.0))  # descend jusqu'à y = 90, plan à 100
    assert diagnosis.cause is MissCause.PLANE_NOT_REACHED
    assert diagnosis.value == pytest.approx(10.0, abs=1.5)


def test_a_stroke_crossing_the_plane_beside_the_zone_says_how_far():
    diagnosis = _diagnose(_stroke(190.0, depth=90.0))  # zone de 100 à 160
    assert diagnosis.cause is MissCause.OUT_OF_ZONE
    assert diagnosis.value == pytest.approx(30.0, abs=0.5)


def test_the_crossing_position_is_interpolated_not_the_nearest_frame():
    # Départ dans la zone, arrivée hors zone : c'est x au moment du franchissement qui compte.
    trajectory = [
        (1.9, 150.0, 80.0),
        (2.0, 170.0, 120.0),  # franchit le plan (y = 100) à mi-chemin : x = 160, au bord
        (2.1, 175.0, 80.0),
    ]
    assert _diagnose(trajectory).cause is MissCause.OTHER  # 160 est dans la zone
    trajectory[1] = (2.0, 190.0, 120.0)  # x = 170 au franchissement : hors zone
    assert _diagnose(trajectory).cause is MissCause.OUT_OF_ZONE


def test_a_slow_crossing_says_the_speed():
    # 2 px par image de 1/30 s = 60 px/s, bien sous les 200 px/s du détecteur.
    trajectory = [(1.5 + i * FRAME_S, 130.0, 70.0 + 2.0 * i) for i in range(30)]
    diagnosis = _diagnose(trajectory)
    assert diagnosis.cause is MissCause.TOO_SLOW
    assert diagnosis.value == pytest.approx(60.0, abs=1.0)


def test_a_hand_that_never_rose_above_the_plane_is_not_rearmed():
    # La main reste juste au-dessus du plan (y = 98), puis le franchit vite : pas remontée.
    trajectory = [(1.5 + i * FRAME_S, 130.0, 98.0) for i in range(12)]
    trajectory += [(1.5 + 12 * FRAME_S, 130.0, 112.0)]
    diagnosis = _diagnose(trajectory)
    assert diagnosis.cause is MissCause.NOT_REARMED
    assert diagnosis.value == pytest.approx(2.0)


def test_the_crossing_nearest_to_the_click_is_the_one_diagnosed():
    # Deux franchissements : un loin du clic (assez vite), un près du clic (trop lent).
    early = [(1.70, 130.0, 60.0), (1.73, 130.0, 110.0), (1.77, 130.0, 60.0)]
    slow = [(1.95 + i * FRAME_S, 130.0, 80.0 + 3.0 * i) for i in range(12)]
    assert _diagnose(early + slow).cause is MissCause.TOO_SLOW


def test_the_minimum_speed_can_be_changed():
    trajectory = [(1.5 + i * FRAME_S, 130.0, 70.0 + 2.0 * i) for i in range(30)]
    assert _diagnose(trajectory, min_speed_px_per_s=40.0).cause is not MissCause.TOO_SLOW


# --- Plusieurs clics ---------------------------------------------------------------


def test_each_missed_click_is_diagnosed_with_its_own_hand_and_zone():
    zones = ZoneMap((ZONE, Zone("ride", 200.0, 260.0, 40.0, 100.0, 150.0)))
    left = [(t, 130.0, 50.0) for t in _frames()]  # ne descend jamais
    right = _stroke(230.0, depth=90.0)  # frappe correcte dans la zone du ride
    elements = {0: "snare", 1: "ride"}

    diagnoses = diagnose_misses(
        [0, 1],
        zones=zones,
        trajectories={"left": left, "right": right},
        expected_element=elements.get,
        hand_for_click=lambda index: "left" if index == 0 else "right",
        click_time_s=lambda index: CLICK_S,
        tolerance_s=TOLERANCE_S,
    )

    assert [(d.index, d.cause) for d in diagnoses] == [
        (0, MissCause.PLANE_NOT_REACHED),
        (1, MissCause.OTHER),
    ]


def test_a_hand_without_any_trajectory_is_not_seen():
    diagnoses = diagnose_misses(
        [0],
        zones=ZoneMap((ZONE,)),
        trajectories={},
        expected_element=lambda index: "snare",
        hand_for_click=lambda index: "left",
        click_time_s=lambda index: CLICK_S,
        tolerance_s=TOLERANCE_S,
    )
    assert diagnoses[0].cause is MissCause.NOT_SEEN


def test_a_click_whose_element_has_no_zone_cannot_be_diagnosed():
    diagnoses = diagnose_misses(
        [0],
        zones=ZoneMap((ZONE,)),
        trajectories={"left": _stroke(130.0, 90.0)},
        expected_element=lambda index: "ride",
        hand_for_click=lambda index: "left",
        click_time_s=lambda index: CLICK_S,
        tolerance_s=TOLERANCE_S,
    )
    assert diagnoses[0].cause is MissCause.OTHER


def test_causes_are_summarized_from_the_most_frequent_with_their_median():
    diagnoses = [
        MissDiagnosis(1, MissCause.PLANE_NOT_REACHED, 8.0),
        MissDiagnosis(5, MissCause.TOO_SLOW, 150.0),
        MissDiagnosis(9, MissCause.PLANE_NOT_REACHED, 12.0),
        MissDiagnosis(13, MissCause.PLANE_NOT_REACHED, 20.0),
        MissDiagnosis(14, MissCause.NOT_SEEN),
    ]

    summary = summarize_causes(diagnoses)

    assert summary[0] == (MissCause.PLANE_NOT_REACHED, [1, 9, 13], 12.0)
    assert (MissCause.NOT_SEEN, [14], None) in summary
    assert [entry[0] for entry in summary][:2] == [MissCause.PLANE_NOT_REACHED, MissCause.NOT_SEEN]


# --- Dans la séance : positions, mains, rapport ------------------------------------

ZONES = ZoneMap(
    tuple(
        Zone(element_id, x_min, x_max, 60.0, 100.0, 150.0)
        for element_id, (x_min, x_max) in zip(
            ("hihat_closed", "snare", "tom_mid", "ride"),
            ((20.0, 80.0), (100.0, 160.0), (180.0, 240.0), (260.0, 310.0)),
            strict=True,
        )
    )
)
FIRST_BEAT_S = 10.0


def _center(element_id: str) -> float:
    zone = ZONES.get(element_id)
    assert zone is not None
    return (zone.x_min + zone.x_max) / 2


def _session(short_positions=(), lost_positions=(), delay_s: float = 0.0):
    """Séance US7 jouée par deux mains fictives ; les positions données sont manquées.

    ``short_positions`` : la main ne descend pas jusqu'au plan ; ``lost_positions`` : l'embout
    n'est pas vu. ``delay_s`` décale les coups détectés par rapport à leur clic."""
    plan = US7_PLAN
    recorder = SessionRecorder(
        plan=plan, source=Source.VISION, first_beat_s=FIRST_BEAT_S, zones=ZONES
    )
    half_s = 0.2
    t = -0.9
    while t < plan.measured_duration_s:
        for hand in ("left", "right"):
            clicks = [i for i in range(plan.hit_count) if hand_for_click(i) == hand]
            index = min(clicks, key=lambda i: abs(plan.beat_time_s(i) - t))
            position = index % len(plan.pattern)
            dt = abs(t - plan.beat_time_s(index))
            depth = 40.0 if position in short_positions else 90.0
            y = 50.0 + depth * max(0.0, 1.0 - dt / half_s)
            x = _center(plan.expected_element(index))
            lost = position in lost_positions and dt < 0.3
            recorder.add_point(FIRST_BEAT_S + t, hand, None if lost else x, None if lost else y)
        t += FRAME_S
    for index in range(plan.hit_count):
        position = index % len(plan.pattern)
        if position in short_positions or position in lost_positions:
            continue
        crossing = plan.beat_time_s(index) - half_s * (1 - 50 / 90) + delay_s
        recorder.add_hit(FIRST_BEAT_S + crossing, plan.expected_element(index))
    return recorder.result()


def test_a_session_where_one_position_never_reaches_the_plane_is_diagnosed():
    result = _session(short_positions={2})  # 3ᵉ position : caisse claire, main gauche

    assert result.detected == 100 - 13
    assert len(result.misses) == 13
    assert {miss.cause for miss in result.misses} == {MissCause.PLANE_NOT_REACHED}
    assert [miss.index % 8 for miss in result.misses] == [2] * 13


def test_position_stats_show_where_the_session_breaks():
    result = _session(short_positions={2})
    stats = {stat.position: stat for stat in position_stats(result)}

    assert (stats[3].detected, stats[3].total) == (0, 13)
    assert (stats[3].hand, stats[3].element_id) == ("left", "snare")
    assert (stats[1].detected, stats[1].total) == (13, 13)
    assert (stats[5].detected, stats[5].total) == (12, 12)


def test_hand_stats_split_the_clicks_by_hand():
    result = _session(short_positions={2})
    assert hand_stats(result) == {"left": (37, 50), "right": (50, 50)}


def test_a_lost_marker_is_diagnosed_as_not_seen():
    result = _session(lost_positions={5})
    assert {miss.cause for miss in result.misses} == {MissCause.NOT_SEEN}


def test_a_perfect_session_has_no_misses():
    result = _session()
    assert result.detected == 100
    assert result.misses == ()
    assert result.detected_clicks == tuple(range(100))


def test_no_diagnosis_without_zones_or_trajectory():
    bare = SessionRecorder(plan=US7_PLAN, source=Source.VISION, first_beat_s=0.0)
    assert bare.result().misses == ()


def test_the_report_gives_each_position_each_hand_and_the_causes():
    text = "\n".join(format_report(_session(short_positions={2})))

    assert "Détail par position du motif" in text
    assert "3  G  Caisse claire" in text and "0 / 13" in text
    assert "Par main : gauche 37 / 50, droite 50 / 50" in text
    assert "Coups manqués : 13" in text
    assert "plan de frappe jamais atteint (course trop courte) : 13" in text
    assert "il manque 10 px (médiane) pour atteindre le plan" in text


def test_a_phase_03_style_report_has_no_diagnosis_section():
    from batterie.input.vision.measure import SessionPlan

    plan = SessionPlan(bpm=120.0, hit_count=4, count_in_beats=2)
    recorder = SessionRecorder(plan=plan, source=Source.VISION, first_beat_s=0.0)
    text = "\n".join(format_report(recorder.result()))
    assert "Détail par position" not in text


# --- Latence négative --------------------------------------------------------------


def _reference(offset_s: float = 0.0):
    recorder = SessionRecorder(plan=US7_PLAN, source=Source.KEYBOARD, first_beat_s=FIRST_BEAT_S)
    for index in range(US7_PLAN.hit_count):
        recorder.add_hit(FIRST_BEAT_S + US7_PLAN.beat_time_s(index) + offset_s)
    return recorder.result()


def _checks(result, reference):
    return {check.label: check for check in us7_checks(result, reference)}


def test_a_detection_well_before_the_keyboard_is_not_called_a_success():
    result = _session(delay_s=0.0)  # coups au franchissement du plan, ≈ 90 ms avant le clic
    latency = _checks(result, _reference(0.0))["Latence geste → son"]

    assert latency.met is None
    assert latency.undetermined == "à interpréter"
    assert "AVANT la référence clavier" in latency.value


def test_the_report_flags_an_early_detection():
    text = "\n".join(format_report(_session(delay_s=0.0), _reference(0.0)))
    assert "(la caméra détecte avant le clavier)" in text
    assert "critère ≤ 60 ms : à interpréter" in text


def test_a_small_negative_offset_is_measurement_noise_not_an_early_detection():
    margin_s = EARLY_DETECTION_MARGIN_MS / 1000
    result = _session(delay_s=0.09 - margin_s / 2)  # ≈ −5 ms par rapport à la référence
    latency = _checks(result, _reference(0.0))["Latence geste → son"]

    assert latency.met is True


def test_a_late_detection_is_still_judged_against_the_60_ms_criterion():
    late = _checks(_session(delay_s=0.16), _reference(0.0))["Latence geste → son"]  # ≈ +70 ms
    assert late.met is False
    on_time = _checks(_session(delay_s=0.12), _reference(0.0))["Latence geste → son"]  # ≈ +30 ms
    assert on_time.met is True
