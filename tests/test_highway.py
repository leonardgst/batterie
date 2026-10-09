"""Tests du couloir de coups : sélection des notes visibles (logique pure)."""

from pathlib import Path

from batterie.core.score import load_score
from batterie.ui.highway import LOOKAHEAD_BEATS, TRAIL_BEATS, visible_notes

ROCK_EXAMPLE = Path(__file__).resolve().parent.parent / "scores" / "rock" / "groove-de-base.toml"


def test_visible_notes_excludes_notes_far_in_the_future():
    score = load_score(ROCK_EXAMPLE)
    current_beat = 0.0

    visible = visible_notes(score, current_beat)

    assert all(offset <= LOOKAHEAD_BEATS for _note, offset in visible)
    assert any(note.beat == 0.0 for note, _offset in visible)


def test_visible_notes_excludes_notes_long_past():
    score = load_score(ROCK_EXAMPLE)
    current_beat = 100.0  # bien après la fin du morceau

    visible = visible_notes(score, current_beat)

    assert visible == []


def test_visible_notes_keeps_a_short_trail_behind_the_strike_line():
    score = load_score(ROCK_EXAMPLE)
    current_beat = 0.0 + TRAIL_BEATS  # juste après le premier temps

    visible = visible_notes(score, current_beat)

    offsets = [offset for note, offset in visible if note.beat == 0.0]
    assert offsets and offsets[0] == -TRAIL_BEATS
