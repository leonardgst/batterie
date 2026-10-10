"""Tests des zones de frappe et du détecteur par zone : trajectoires synthétiques, sans caméra."""

import math

import pytest

from batterie.input.vision.strike_detector import StrikeDetector
from batterie.input.vision.zones import Zone, ZoneMap, ZoneStrikeDetector

FRAME_DT_S = 1 / 30
TOP, PLANE, BOTTOM = 60.0, 150.0, 190.0


def _zone(element_id: str, x_min: float, x_max: float) -> Zone:
    return Zone(element_id, x_min, x_max, y_top=TOP, strike_plane_y=PLANE, y_bottom=BOTTOM)


def _kit() -> ZoneMap:
    """Quatre zones côte à côte, de gauche à droite comme sur l'écran du kit."""
    return ZoneMap(
        (
            _zone("hihat_closed", 10, 70),
            _zone("snare", 90, 150),
            _zone("tom_mid", 170, 230),
            _zone("ride", 250, 310),
        )
    )


def _stroke(t0: float, x: float, *, duration: float = 0.30):
    """Un coup complet : du haut de la zone jusqu'en bas, puis retour, à ``x`` constant."""
    steps = round(duration / FRAME_DT_S)
    for i in range(steps + 1):
        u = i / steps
        y = TOP + (BOTTOM - TOP) * (1 - math.cos(2 * math.pi * u)) / 2
        yield t0 + i * FRAME_DT_S, x, y


def _hits(detector: ZoneStrikeDetector, samples) -> list[str]:
    return [zone.element_id for zone in (detector.update(*s) for s in samples) if zone is not None]


# --- Zone et ZoneMap ---------------------------------------------------------


def test_zone_rejects_an_unknown_element():
    with pytest.raises(ValueError, match="inconnu"):
        Zone("triangle", 0, 10, 0, 5, 9)


def test_zone_rejects_inverted_bounds():
    with pytest.raises(ValueError, match="x_min"):
        Zone("snare", 50, 10, 0, 5, 9)
    with pytest.raises(ValueError, match="strike_plane_y"):
        Zone("snare", 0, 10, 50, 40, 90)  # plan au-dessus du haut
    with pytest.raises(ValueError, match="strike_plane_y"):
        Zone("snare", 0, 10, 0, 90, 50)  # plan sous le bas


def test_rearm_margin_is_a_quarter_of_the_stroke_height_with_a_floor():
    assert _zone("snare", 0, 10).rearm_margin_px == pytest.approx(22.5)
    flat = Zone("snare", 0, 10, y_top=148, strike_plane_y=150, y_bottom=160)
    assert flat.rearm_margin_px == 4.0


def test_zone_map_rejects_the_same_element_twice():
    with pytest.raises(ValueError, match="deux zones"):
        ZoneMap((_zone("snare", 0, 50), _zone("snare", 100, 150)))


def test_zone_map_rejects_zones_that_overlap_in_width():
    with pytest.raises(ValueError, match="chevauchent"):
        ZoneMap((_zone("snare", 0, 100), _zone("tom_high", 80, 180)))


def test_zone_map_accepts_zones_that_touch_and_any_declaration_order():
    zone_map = ZoneMap((_zone("tom_high", 100, 200), _zone("snare", 0, 100)))
    assert [zone.element_id for zone in zone_map] == ["tom_high", "snare"]
    assert len(zone_map) == 2
    assert zone_map.get("snare") is not None
    assert zone_map.get("ride") is None


def test_an_empty_zone_map_never_hits():
    detector = ZoneStrikeDetector(ZoneMap())
    assert _hits(detector, _stroke(0.0, 100)) == []


# --- Attribution à l'élément --------------------------------------------------


@pytest.mark.parametrize(
    ("x", "expected"),
    [(40, "hihat_closed"), (120, "snare"), (200, "tom_mid"), (280, "ride")],
)
def test_a_stroke_hits_the_element_of_the_zone_it_is_in(x, expected):
    detector = ZoneStrikeDetector(_kit())
    assert _hits(detector, _stroke(0.0, x)) == [expected]


def test_a_stroke_between_two_zones_hits_nothing():
    detector = ZoneStrikeDetector(_kit())
    assert _hits(detector, _stroke(0.0, 80)) == []  # entre hihat (70) et snare (90)


def test_two_hands_alternating_over_the_four_zones_hit_the_right_elements():
    kit = _kit()
    left, right = ZoneStrikeDetector(kit), ZoneStrikeDetector(kit)
    pattern = [
        ("left", 40, "hihat_closed"),
        ("right", 120, "snare"),
        ("left", 40, "hihat_closed"),
        ("right", 200, "tom_mid"),
        ("left", 120, "snare"),
        ("right", 280, "ride"),
        ("left", 200, "tom_mid"),
        ("right", 280, "ride"),
    ]
    detectors = {"left": left, "right": right}
    got = []
    for index, (hand, x, _) in enumerate(pattern):
        t0 = index * 0.5  # un coup toutes les 0,5 s, les mains en alternance
        got.append(_hits(detectors[hand], _stroke(t0, x)))
    assert got == [[element] for _, _, element in pattern]


def test_both_hands_can_hit_at_the_same_instant():
    kit = _kit()
    left, right = ZoneStrikeDetector(kit), ZoneStrikeDetector(kit)
    got = list(zip(_hits(left, _stroke(0.0, 40)), _hits(right, _stroke(0.0, 280)), strict=True))
    assert got == [("hihat_closed", "ride")]


# --- Seuils : vitesse, sens ----------------------------------------------------


def test_a_slow_crossing_is_not_a_hit():
    detector = ZoneStrikeDetector(_kit(), min_speed_px_per_s=200.0)
    slow = [(0.0, 120, PLANE - 1), (1.0, 120, PLANE + 1)]  # 2 px/s
    assert _hits(detector, slow) == []


def test_an_upward_crossing_is_not_a_hit():
    detector = ZoneStrikeDetector(_kit())
    up = [(0.0, 120, PLANE + 20), (0.033, 120, PLANE - 20)]
    assert _hits(detector, up) == []


# --- Position du franchissement ------------------------------------------------


def test_a_diagonal_stroke_is_attributed_where_it_crosses_the_plane_not_where_it_starts():
    detector = ZoneStrikeDetector(_kit())
    # Part de la zone snare (x=140), franchit le plan à mi-chemin à x=180 : tom_mid.
    diagonal = [(0.0, 140, 148), (0.01, 220, 152)]
    assert _hits(detector, diagonal) == ["tom_mid"]


def test_one_step_crossing_two_planes_hits_the_highest_plane_first():
    zones = ZoneMap(
        (
            Zone("snare", 0, 100, y_top=40, strike_plane_y=100, y_bottom=190),
            Zone("tom_mid", 100, 200, y_top=40, strike_plane_y=150, y_bottom=190),
        )
    )
    detector = ZoneStrikeDetector(zones)
    # Un seul pas franchit les deux plans (y=100 à x≈64, y=150 à x≈136) : le plus haut gagne.
    assert _hits(detector, [(0.0, 50, 90), (0.01, 150, 160)]) == ["snare"]


# --- Anti-double-coup -----------------------------------------------------------


def test_a_stroke_that_crosses_two_planes_counts_once():
    zones = ZoneMap(
        (
            Zone("snare", 0, 100, y_top=40, strike_plane_y=100, y_bottom=190),
            Zone("tom_mid", 120, 220, y_top=40, strike_plane_y=160, y_bottom=190),
        )
    )
    detector = ZoneStrikeDetector(zones)
    # Descente en diagonale à 45° : traverse le plan snare (x≈90) puis le plan tom_mid (x≈150),
    # plus de 0,15 s plus tard : seul le ré-armement empêche un deuxième coup, pas l'anti-rebond.
    steps = 20
    diagonal = [(i * 0.03, 50 + 140 * i / steps, 60 + 140 * i / steps) for i in range(steps + 1)]
    assert _hits(detector, diagonal) == ["snare"]


def test_jitter_around_the_plane_counts_once_where_the_plain_detector_counts_many():
    jitter = [(i * FRAME_DT_S, 120, PLANE + 3 * (-1) ** i) for i in range(60)]  # 2 s
    zone_detector = ZoneStrikeDetector(_kit(), min_speed_px_per_s=50.0)
    plain = StrikeDetector(strike_plane_y=PLANE, min_speed_px_per_s=50.0)

    assert len(_hits(zone_detector, jitter)) == 1
    assert sum(plain.update(t, y) for t, _, y in jitter) > 3


def test_the_next_stroke_needs_a_real_rise_above_the_plane():
    detector = ZoneStrikeDetector(_kit())  # marge de ré-armement : 22,5 px
    samples = [
        (0.00, 120, PLANE - 30),
        (0.03, 120, PLANE + 5),  # coup n°1
        (0.30, 120, PLANE - 10),  # remonte de 10 px seulement (< 22,5)
        (0.33, 120, PLANE + 5),  # redescend : pas de coup
        (0.60, 120, PLANE - 30),  # remonte de 30 px : ré-armé
        (0.63, 120, PLANE + 5),  # coup n°2
    ]
    assert _hits(detector, samples) == ["snare", "snare"]
    detector.reset()
    samples_without_rise = samples[:4]
    assert _hits(detector, samples_without_rise) == ["snare"]


def test_two_strokes_closer_than_the_refractory_period_count_once():
    fast = [
        (0.000, 120, PLANE - 30),
        (0.030, 120, PLANE + 5),  # coup n°1
        (0.060, 120, PLANE - 30),  # remonte vite : ré-armé
        (0.090, 120, PLANE + 5),  # 0,06 s après le coup n°1 : trop tôt (< 0,15 s)
        (0.200, 120, PLANE - 30),
        (0.230, 120, PLANE + 5),  # 0,20 s après : accepté
    ]
    detector = ZoneStrikeDetector(_kit(), refractory_s=0.15)
    assert _hits(detector, fast) == ["snare", "snare"]


def test_losing_and_finding_the_marker_again_does_not_double_count():
    detector = ZoneStrikeDetector(_kit())
    samples = list(_stroke(0.0, 120))
    assert len(_hits(detector, samples)) == 1
    # Le marqueur disparaît 2 s (aucun échantillon), puis réapparaît en haut : prêt à frapper.
    assert len(_hits(detector, list(_stroke(2.5, 120)))) == 1
