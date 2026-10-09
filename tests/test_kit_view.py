"""Tests de la vue du kit : dessin et illumination au coup."""

import pygame
import pytest

from batterie.ui.kit_view import _LAYOUT, FLASH_COLOR, FLASH_DURATION_S, KitView, _transform


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


def test_lit_hihat_closed_is_drawn_above_unlit_hihat_open():
    # hihat_closed et hihat_open partagent la même position (même élément physique) :
    # celui allumé doit rester visible, peu importe l'ordre de dessin par défaut.
    view = KitView()
    view.flash("hihat_closed")
    screen = pygame.display.get_surface()
    view.draw(screen)

    center, _radius = _transform(
        _LAYOUT["hihat_closed"][:2], _LAYOUT["hihat_closed"][2], screen.get_rect()
    )
    assert screen.get_at(center)[:3] == FLASH_COLOR


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
