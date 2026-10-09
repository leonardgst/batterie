"""Tests du format de partition : chargement, grille, swing, erreurs."""

from pathlib import Path

import pytest

from batterie.core.score import discover_scores, load_score

SCORES_DIR = Path(__file__).resolve().parent.parent / "scores"
ROCK_EXAMPLE = SCORES_DIR / "rock" / "groove-de-base.toml"


def test_load_score_reads_metadata():
    score = load_score(ROCK_EXAMPLE)

    assert score.id == "groove-de-base"
    assert score.title == "Rock — groove de base"
    assert score.style == "rock"
    assert score.bpm == 90.0
    assert score.time_signature == (4, 4)
    assert score.grid == 8
    assert score.swing == 0.0
    assert score.difficulty == 1
    assert score.license == "CC0-1.0"


def test_load_score_flattens_notes_from_repeated_section():
    score = load_score(ROCK_EXAMPLE)

    # 8 charlestons + 2 caisses claires + 2 grosses caisses, répété 4 fois.
    assert len(score.notes) == (8 + 2 + 2) * 4


def test_load_score_places_straight_eighths_at_half_beat_steps():
    score = load_score(ROCK_EXAMPLE)

    hihat_beats = sorted(note.beat for note in score.notes if note.element_id == "hihat_closed")
    first_measure = hihat_beats[:8]

    assert first_measure == pytest.approx([i * 0.5 for i in range(8)])


def test_load_score_applies_symbol_velocities():
    score = load_score(ROCK_EXAMPLE)

    kick_notes = [note for note in score.notes if note.element_id == "kick"]
    assert {note.velocity for note in kick_notes} == {0.8}

    snare_notes = [note for note in score.notes if note.element_id == "snare"]
    assert {note.velocity for note in snare_notes} == {0.8}


def test_load_score_measures_repeat_with_increasing_beat_offset():
    score = load_score(ROCK_EXAMPLE)

    kick_beats = sorted(note.beat for note in score.notes if note.element_id == "kick")
    # "x---x---" : un coup au temps 1 et au temps 3 de chaque mesure (4 beats/mesure).
    assert kick_beats == [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0]


def test_duration_beats_covers_the_last_note(tmp_path: Path):
    path = _write_score(
        tmp_path,
        """
        title = "Test"
        style = "rock"
        bpm = 100
        time_signature = [4, 4]
        grid = 4
        [[section]]
        name = "A"
        repeat = 1
        kick = "x---"
        """,
    )
    score = load_score(path)
    assert score.duration_beats == pytest.approx(4.0)


def test_swing_delays_the_off_beat_cell(tmp_path: Path):
    path = _write_score(
        tmp_path,
        """
        title = "Swing test"
        style = "jazz"
        bpm = 120
        time_signature = [4, 4]
        grid = 8
        swing = 0.66
        [[section]]
        name = "A"
        repeat = 1
        ride = "xxxxxxxx"
        """,
    )
    score = load_score(path)
    beats = sorted(note.beat for note in score.notes)

    # Temps (index pair) inchangés ; contretemps (index impair) décalés à 0.66 du temps.
    assert beats[0] == pytest.approx(0.0)
    assert beats[1] == pytest.approx(0.66)
    assert beats[2] == pytest.approx(1.0)
    assert beats[3] == pytest.approx(1.66)


def test_unknown_element_raises(tmp_path: Path):
    path = _write_score(
        tmp_path,
        """
        title = "Bad"
        style = "rock"
        bpm = 100
        time_signature = [4, 4]
        grid = 4
        [[section]]
        name = "A"
        repeat = 1
        banjo = "x---"
        """,
    )
    with pytest.raises(ValueError, match="élément inconnu"):
        load_score(path)


def test_wrong_row_length_raises(tmp_path: Path):
    path = _write_score(
        tmp_path,
        """
        title = "Bad"
        style = "rock"
        bpm = 100
        time_signature = [4, 4]
        grid = 8
        [[section]]
        name = "A"
        repeat = 1
        kick = "x---"
        """,
    )
    with pytest.raises(ValueError, match="case"):
        load_score(path)


def test_unknown_symbol_raises(tmp_path: Path):
    path = _write_score(
        tmp_path,
        """
        title = "Bad"
        style = "rock"
        bpm = 100
        time_signature = [4, 4]
        grid = 4
        [[section]]
        name = "A"
        repeat = 1
        kick = "x?--"
        """,
    )
    with pytest.raises(ValueError, match="symbole"):
        load_score(path)


def test_discover_scores_finds_the_rock_example_and_skips_local():
    local_dir = SCORES_DIR / "local"
    local_dir.mkdir(exist_ok=True)
    decoy = local_dir / "decoy.toml"
    decoy.write_text('title = "decoy"\n', encoding="utf-8")

    try:
        found = discover_scores(SCORES_DIR)
        assert ROCK_EXAMPLE in found
        assert decoy not in found
    finally:
        decoy.unlink()


def _write_score(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "score.toml"
    # Désindente : les blocs sont écrits avec une indentation Python pour la lisibilité.
    lines = [line.strip() for line in content.strip("\n").splitlines()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
