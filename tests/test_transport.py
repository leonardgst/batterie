"""Tests de l'horloge du morceau : conversion beat/secondes, tempo, pause, dérive."""

import pytest

from batterie.core.transport import (
    MAX_TEMPO_FACTOR,
    MIN_TEMPO_FACTOR,
    NS_PER_SECOND,
    Transport,
    clamp_tempo_factor,
)


def test_beats_per_second_matches_bpm_at_normal_tempo():
    transport = Transport(bpm=120.0, time_signature=(4, 4))
    assert transport.beats_per_second() == pytest.approx(2.0)
    assert transport.seconds_per_beat() == pytest.approx(0.5)


def test_tempo_factor_scales_beats_per_second():
    transport = Transport(bpm=120.0, time_signature=(4, 4), tempo_factor=0.5)
    assert transport.beats_per_second() == pytest.approx(1.0)


def test_clamp_tempo_factor_bounds_to_fifty_to_hundred_twenty_percent():
    assert clamp_tempo_factor(0.1) == MIN_TEMPO_FACTOR
    assert clamp_tempo_factor(5.0) == MAX_TEMPO_FACTOR
    assert clamp_tempo_factor(0.75) == pytest.approx(0.75)


def test_set_tempo_factor_clamps():
    transport = Transport(bpm=100.0, time_signature=(4, 4))
    transport.set_tempo_factor(2.0)
    assert transport.tempo_factor == MAX_TEMPO_FACTOR


def test_current_beat_zero_before_start():
    transport = Transport(bpm=120.0, time_signature=(4, 4))
    assert transport.current_beat(now_ns=123) == 0.0


def test_current_beat_advances_with_elapsed_time():
    transport = Transport(bpm=120.0, time_signature=(4, 4))
    transport.start(now_ns=0)

    one_second_later = 1 * NS_PER_SECOND
    assert transport.current_beat(one_second_later) == pytest.approx(2.0)


def test_pause_freezes_current_beat():
    transport = Transport(bpm=120.0, time_signature=(4, 4))
    transport.start(now_ns=0)
    transport.pause(now_ns=1 * NS_PER_SECOND)

    assert transport.current_beat(2 * NS_PER_SECOND) == pytest.approx(2.0)
    assert transport.is_paused


def test_resume_continues_from_the_paused_position():
    transport = Transport(bpm=120.0, time_signature=(4, 4))
    transport.start(now_ns=0)
    transport.pause(now_ns=1 * NS_PER_SECOND)
    transport.resume(now_ns=5 * NS_PER_SECOND)

    assert transport.current_beat(6 * NS_PER_SECOND) == pytest.approx(4.0)
    assert not transport.is_paused


def test_count_in_starts_at_negative_beat_and_reaches_zero():
    transport = Transport(bpm=120.0, time_signature=(4, 4))
    transport.start(now_ns=0, count_in_beats=4.0)

    assert transport.current_beat(now_ns=0) == pytest.approx(-4.0)
    # 4 beats à 120 bpm = 2 secondes de décompte.
    assert transport.current_beat(2 * NS_PER_SECOND) == pytest.approx(0.0)


def test_beat_to_elapsed_seconds_matches_cadrage_formula():
    transport = Transport(bpm=90.0, time_signature=(4, 4))
    # R6 : secondes = beat x 60 / (bpm x facteur).
    assert transport.beat_to_elapsed_seconds(8.0) == pytest.approx(8 * 60 / 90)


def test_beat_to_elapsed_seconds_accounts_for_count_in_offset():
    transport = Transport(bpm=120.0, time_signature=(4, 4))
    transport.start(now_ns=0, count_in_beats=4.0)
    # Le premier vrai temps (beat 0) sonne 2 s après le début du décompte.
    assert transport.beat_to_elapsed_seconds(0.0) == pytest.approx(2.0)


def test_metronome_ticks_one_per_beat_in_range():
    transport = Transport(bpm=120.0, time_signature=(4, 4))
    assert transport.metronome_ticks(from_beat=-4.0, to_beat=2.0) == [
        -4.0,
        -3.0,
        -2.0,
        -1.0,
        0.0,
        1.0,
        2.0,
    ]


def test_metronome_ticks_empty_when_range_is_inverted():
    transport = Transport(bpm=120.0, time_signature=(4, 4))
    assert transport.metronome_ticks(from_beat=5.0, to_beat=1.0) == []


def test_no_synchronisation_drift_over_five_simulated_minutes():
    """US5 : dérive < 5 ms sur 5 minutes, vérifié sans attendre 5 minutes réelles."""
    bpm = 126.0
    transport = Transport(bpm=bpm, time_signature=(4, 4))
    transport.start(now_ns=0)

    bps = transport.beats_per_second()
    max_error_beats = 0.005 * bps  # 5 ms, convertis en beats à ce tempo

    # Simule un balayage à 500 Hz (fréquence de lecture clavier visée) sur 5 minutes.
    step_ns = NS_PER_SECOND // 500
    total_ns = 5 * 60 * NS_PER_SECOND

    now_ns = 0
    while now_ns <= total_ns:
        expected_beat = (now_ns / NS_PER_SECOND) * bps
        actual_beat = transport.current_beat(now_ns)
        assert actual_beat == pytest.approx(expected_beat, abs=max_error_beats)
        now_ns += step_ns
