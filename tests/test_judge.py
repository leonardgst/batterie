"""Tests du jugement des coups (cadrage R7) : classement, association, notes ratées."""

import pytest

from batterie.core.judge import GOOD_WINDOW_MS, PERFECT_WINDOW_MS, Judge, classify


def test_classify_perfect_within_35ms():
    assert classify(0.0) == "perfect"
    assert classify(PERFECT_WINDOW_MS) == "perfect"
    assert classify(-PERFECT_WINDOW_MS) == "perfect"


def test_classify_good_between_35_and_90ms():
    assert classify(PERFECT_WINDOW_MS + 1) == "good"
    assert classify(GOOD_WINDOW_MS) == "good"
    assert classify(-GOOD_WINDOW_MS) == "good"


def test_classify_miss_beyond_90ms():
    assert classify(GOOD_WINDOW_MS + 1) == "miss"
    assert classify(-1000.0) == "miss"


@pytest.fixture
def judge() -> Judge:
    # 120 bpm -> 0.5 s/beat -> 1 beat = 500 ms.
    return Judge(notes_by_element={"snare": [0.0, 1.0, 2.0]}, seconds_per_beat=0.5)


def test_register_hit_exactly_on_time_is_perfect(judge: Judge):
    judgement = judge.register_hit("snare", hit_beat=0.0)
    assert judgement is not None
    assert judgement.rating == "perfect"
    assert judgement.error_ms == pytest.approx(0.0)


def test_register_hit_slightly_late_is_good(judge: Judge):
    # 1 beat = 500 ms ; 0.1 beat = 50 ms de retard -> "bien".
    judgement = judge.register_hit("snare", hit_beat=0.1)
    assert judgement is not None
    assert judgement.rating == "good"
    assert judgement.error_ms == pytest.approx(50.0)


def test_register_hit_far_off_is_a_miss(judge: Judge):
    judgement = judge.register_hit("snare", hit_beat=0.5)
    assert judgement is not None
    assert judgement.rating == "miss"


def test_register_hit_matches_the_closest_unconsumed_note(judge: Judge):
    first = judge.register_hit("snare", hit_beat=0.05)
    second = judge.register_hit("snare", hit_beat=0.05)

    assert first is not None and first.rating == "perfect"
    # La note à 0.0 est déjà prise : la deuxième frappe s'associe à celle à 1.0.
    assert second is not None
    assert second.error_ms == pytest.approx((0.05 - 1.0) * 0.5 * 1000)


def test_register_hit_for_unknown_element_returns_none(judge: Judge):
    assert judge.register_hit("kick", hit_beat=0.0) is None


def test_register_hit_when_no_notes_left_returns_none():
    judge = Judge(notes_by_element={"snare": [0.0]}, seconds_per_beat=0.5)
    judge.register_hit("snare", hit_beat=0.0)
    assert judge.register_hit("snare", hit_beat=0.0) is None


def test_expire_missed_notes_counts_notes_past_their_window(judge: Judge):
    # Note à 0.0, fenêtre de 90 ms = 0.18 beat à 120 bpm. current_beat=1.0 largement dépassé.
    missed = judge.expire_missed_notes(current_beat=0.5)
    assert missed == 1
    assert judge.counts["miss"] == 1


def test_expire_missed_notes_does_not_double_count(judge: Judge):
    judge.expire_missed_notes(current_beat=0.5)
    missed_again = judge.expire_missed_notes(current_beat=0.6)
    assert missed_again == 0
    assert judge.counts["miss"] == 1


def test_expire_missed_notes_skips_already_hit_notes(judge: Judge):
    judge.register_hit("snare", hit_beat=0.0)
    missed = judge.expire_missed_notes(current_beat=0.5)
    assert missed == 0


def test_accuracy_is_zero_with_no_judged_hits(judge: Judge):
    assert judge.accuracy == 0.0


def test_accuracy_counts_perfect_and_good_not_miss():
    judge = Judge(notes_by_element={"snare": [0.0, 1.0, 2.0, 3.0]}, seconds_per_beat=0.5)
    judge.register_hit("snare", hit_beat=0.0)  # perfect
    judge.register_hit("snare", hit_beat=1.1)  # good
    judge.expire_missed_notes(current_beat=10.0)  # les 2 restantes ratées

    assert judge.total == 4
    assert judge.accuracy == pytest.approx(0.5)
