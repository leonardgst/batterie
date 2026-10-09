"""Tests de la détection de coup : franchissement rapide d'un plan, anti-rebond."""

from batterie.input.vision.strike_detector import StrikeDetector


def test_fast_downward_crossing_triggers_a_hit():
    detector = StrikeDetector(strike_plane_y=100.0, min_speed_px_per_s=200.0)
    detector.update(0.0, 80.0)  # au-dessus du plan

    hit = detector.update(0.01, 105.0)  # 2500 px/s vers le bas, franchit 100

    assert hit is True


def test_slow_downward_crossing_does_not_trigger():
    detector = StrikeDetector(strike_plane_y=100.0, min_speed_px_per_s=200.0)
    detector.update(0.0, 80.0)

    hit = detector.update(1.0, 105.0)  # 25 px/s : bien trop lent

    assert hit is False


def test_upward_crossing_does_not_trigger():
    detector = StrikeDetector(strike_plane_y=100.0, min_speed_px_per_s=200.0)
    detector.update(0.0, 120.0)  # en dessous du plan

    hit = detector.update(0.01, 90.0)  # remonte au-dessus, vite

    assert hit is False


def test_staying_below_the_plane_does_not_retrigger():
    detector = StrikeDetector(strike_plane_y=100.0, min_speed_px_per_s=50.0)
    detector.update(0.0, 80.0)
    first = detector.update(0.05, 110.0)  # franchit
    second = detector.update(0.10, 130.0)  # continue vers le bas, déjà franchi

    assert first is True
    assert second is False


def test_refractory_period_blocks_a_second_hit_too_soon():
    detector = StrikeDetector(strike_plane_y=100.0, min_speed_px_per_s=200.0, refractory_s=0.2)
    detector.update(0.0, 80.0)
    first = detector.update(0.01, 105.0)  # premier coup
    # Remonte puis re-descend très vite, avant la fin de l'anti-rebond.
    detector.update(0.02, 80.0)
    second = detector.update(0.03, 105.0)

    assert first is True
    assert second is False


def test_hit_allowed_again_after_the_refractory_period():
    detector = StrikeDetector(strike_plane_y=100.0, min_speed_px_per_s=200.0, refractory_s=0.1)
    detector.update(0.0, 80.0)
    first = detector.update(0.01, 105.0)
    detector.update(0.3, 80.0)
    second = detector.update(0.31, 105.0)  # largement après la fin de l'anti-rebond

    assert first is True
    assert second is True


def test_first_sample_never_triggers():
    detector = StrikeDetector(strike_plane_y=100.0)
    assert detector.update(0.0, 150.0) is False


def test_reset_clears_state_so_the_next_sample_cannot_trigger():
    detector = StrikeDetector(strike_plane_y=100.0, min_speed_px_per_s=200.0)
    detector.update(0.0, 80.0)
    detector.reset()

    hit = detector.update(0.01, 105.0)

    assert hit is False
