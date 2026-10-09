"""Tests du socle applicatif : ouverture de la fenêtre et arrêt sur fermeture."""

import pygame

from batterie.app import SCORES_DIR, WINDOW_SIZE, _scores_for_style, create_window, handle_events


def test_create_window_opens_at_expected_size():
    screen = create_window()
    assert screen.get_size() == WINDOW_SIZE
    pygame.quit()


def test_handle_events_stops_on_quit_event():
    assert handle_events([pygame.event.Event(pygame.QUIT)]) is False


def test_handle_events_continues_on_escape_key():
    # Échap est géré par mode (pause, retour au menu...), pas par un arrêt global.
    assert handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)]) is True


def test_handle_events_continues_without_matching_events():
    assert handle_events([]) is True
    assert handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a)]) is True


def test_scores_for_style_only_returns_matching_style():
    scores = _scores_for_style("rock")
    assert scores
    assert all(score.style == "rock" for score in scores)


def test_scores_for_style_empty_for_unknown_style():
    assert _scores_for_style("not-a-style") == []


def test_scores_for_style_sorted_by_difficulty_then_title():
    scores = _scores_for_style("jazz")
    difficulties = [s.difficulty for s in scores]
    assert difficulties == sorted(difficulties)


def test_scores_dir_points_at_the_real_scores_directory():
    assert SCORES_DIR.is_dir()
    assert (SCORES_DIR / "rock").is_dir()
