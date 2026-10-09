"""Tests de la vue du kit : dessin et illumination au coup."""

import pygame
import pytest

from batterie.ui.kit_view import FLASH_DURATION_S, KitView


@pytest.fixture(autouse=True)
def _pygame_display():
    pygame.init()
    pygame.display.set_mode((100, 100))
    yield
    pygame.quit()


def test_draw_runs_without_error_for_every_element():
    view = KitView()
    screen = pygame.display.get_surface()
    for element_id in ("kick", "snare", "crash", "hihat_closed", "ride"):
        view.flash(element_id)
    view.draw(screen)  # ne doit pas lever d'exception


def test_flash_marks_element_as_lit_until_it_expires(monkeypatch):
    view = KitView()
    now = 1_000.0
    monkeypatch.setattr("batterie.ui.kit_view.time.perf_counter", lambda: now)

    view.flash("snare")
    assert view._flash_until["snare"] == pytest.approx(now + FLASH_DURATION_S)

    now += FLASH_DURATION_S + 0.01
    monkeypatch.setattr("batterie.ui.kit_view.time.perf_counter", lambda: now)
    screen = pygame.display.get_surface()
    view.draw(screen)  # ne lève pas et ne replanifie pas l'illumination
    assert view._flash_until["snare"] < now
