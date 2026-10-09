"""Tests de la lecture clavier : correspondance scancode -> élément, pas de répétition."""

import pygame
import pytest

from batterie.input.keyboard import SCANCODE_TO_ELEMENT, Keyboard


@pytest.fixture(autouse=True)
def _pygame_init():
    pygame.init()
    yield
    pygame.quit()


def _keydown(scancode: int, *, repeat: bool = False) -> pygame.event.Event:
    return pygame.event.Event(
        pygame.KEYDOWN, scancode=scancode, key=pygame.K_UNKNOWN, repeat=repeat
    )


def test_scancode_map_covers_all_ten_elements():
    assert len(SCANCODE_TO_ELEMENT) == 10


def test_poll_returns_element_for_known_scancode():
    keyboard = Keyboard()
    assert keyboard.poll([_keydown(pygame.KSCAN_SPACE)]) == ["kick"]


def test_poll_ignores_unknown_scancode():
    keyboard = Keyboard()
    assert keyboard.poll([_keydown(pygame.KSCAN_UNKNOWN)]) == []


def test_poll_ignores_non_keydown_events():
    keyboard = Keyboard()
    event = pygame.event.Event(pygame.KEYUP, scancode=pygame.KSCAN_SPACE)
    assert keyboard.poll([event]) == []


def test_poll_ignores_repeated_keydown():
    keyboard = Keyboard()
    assert keyboard.poll([_keydown(pygame.KSCAN_SPACE, repeat=True)]) == []


def test_poll_reads_three_simultaneous_hits():
    keyboard = Keyboard()
    events = [
        _keydown(pygame.KSCAN_SPACE),
        _keydown(pygame.KSCAN_F),
        _keydown(pygame.KSCAN_W),
    ]
    assert sorted(keyboard.poll(events)) == sorted(["kick", "snare", "crash"])
