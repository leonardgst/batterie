"""Tests de la bibliothèque de partitions : toutes les partitions versionnées se chargent."""

from pathlib import Path

import pytest

from batterie.core.score import STYLES, discover_scores, load_score

SCORES_DIR = Path(__file__).resolve().parent.parent / "scores"
SCORE_PATHS = discover_scores(SCORES_DIR)


def test_at_least_twelve_scores_are_versioned():
    assert len(SCORE_PATHS) >= 12


@pytest.mark.parametrize("style", STYLES)
def test_each_style_has_at_least_three_scores(style: str):
    count = sum(1 for path in SCORE_PATHS if path.parent.name == style)
    assert count >= 3, f"style {style!r} : seulement {count} partition(s)"


@pytest.mark.parametrize("path", SCORE_PATHS, ids=lambda path: path.stem)
def test_score_loads_without_error(path: Path):
    score = load_score(path)

    assert score.title
    assert score.style in STYLES
    assert score.style == path.parent.name
    assert score.license
    assert score.bpm > 0
    assert score.notes
    assert score.duration_beats > 0


@pytest.mark.parametrize("path", SCORE_PATHS, ids=lambda path: path.stem)
def test_score_ids_are_unique_and_match_filename(path: Path):
    score = load_score(path)
    assert score.id == path.stem
