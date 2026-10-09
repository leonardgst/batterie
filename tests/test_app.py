"""Tests du socle applicatif : ouverture de la fenêtre et sortie par Échap ou fermeture."""

import pygame

from batterie.app import WINDOW_SIZE, create_window, handle_events


def test_create_window_opens_at_expected_size():
    screen = create_window()
    assert screen.get_size() == WINDOW_SIZE
    pygame.quit()


def test_handle_events_stops_on_quit_event():
    create_window()
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    assert handle_events() is False
    pygame.quit()


def test_handle_events_stops_on_escape_key():
    create_window()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert handle_events() is False
    pygame.quit()


def test_handle_events_continues_without_events():
    create_window()
    pygame.event.clear()
    assert handle_events() is True
    pygame.quit()
