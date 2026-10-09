"""Boucle principale : fenêtre, kit dessiné, clavier, son et illumination du coup.

Le clavier est lu à chaque tour de boucle (≥ 500 Hz) ; le rendu est limité à
60 images/s. Une touche n'attend jamais l'image suivante pour sonner.
"""

from __future__ import annotations

import time
from pathlib import Path

import pygame

from batterie.audio.engine import AudioEngine, init_mixer, load_kit
from batterie.config.settings import load_settings
from batterie.input.keyboard import Keyboard, scancode_map_from_key_map
from batterie.ui.kit_view import KitView

WINDOW_TITLE = "Batterie"
WINDOW_SIZE = (1280, 720)
TARGET_FPS = 60
INPUT_POLL_HZ = 500

DEFAULT_KIT_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "kits" / "default"


def create_window() -> pygame.Surface:
    """Initialise pygame (audio avant fenêtre) et ouvre la fenêtre principale."""
    init_mixer()
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption(WINDOW_TITLE)
    return screen


def handle_events(events: list[pygame.event.Event]) -> bool:
    """Renvoie False si l'application doit s'arrêter (fermeture de fenêtre ou Échap)."""
    for event in events:
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return False
    return True


def run() -> None:
    """Boucle jusqu'à la fermeture de la fenêtre ou l'appui sur Échap."""
    screen = create_window()
    settings = load_settings()
    engine = AudioEngine(load_kit(DEFAULT_KIT_DIR), master_volume=settings.volume)
    keyboard = Keyboard(scancode_map_from_key_map(settings.key_map))
    kit_view = KitView()

    poll_clock = pygame.time.Clock()
    render_interval_s = 1.0 / TARGET_FPS
    next_render = time.perf_counter()

    running = True
    try:
        while running:
            events = pygame.event.get()
            running = handle_events(events)

            for element_id in keyboard.poll(events):
                engine.play(element_id)
                kit_view.flash(element_id)

            now = time.perf_counter()
            if now >= next_render:
                kit_view.draw(screen)
                pygame.display.flip()
                next_render = now + render_interval_s

            poll_clock.tick(INPUT_POLL_HZ)
    finally:
        pygame.quit()


def main() -> int:
    """Point d'entrée du script `batterie`."""
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
