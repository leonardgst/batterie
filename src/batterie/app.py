"""Boucle principale de l'application : fenêtre vide, Échap ou fermeture pour quitter."""

from __future__ import annotations

import pygame

WINDOW_TITLE = "Batterie"
WINDOW_SIZE = (1280, 720)
BACKGROUND_COLOR = (20, 20, 20)
TARGET_FPS = 60


def create_window() -> pygame.Surface:
    """Initialise pygame (audio avant fenêtre) et ouvre la fenêtre principale."""
    pygame.mixer.pre_init(48000, -16, 2, 256)
    pygame.init()
    pygame.mixer.set_num_channels(32)
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption(WINDOW_TITLE)
    return screen


def handle_events() -> bool:
    """Traite les événements en attente ; renvoie False si l'application doit s'arrêter."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return False
    return True


def run() -> None:
    """Boucle jusqu'à la fermeture de la fenêtre ou l'appui sur Échap."""
    screen = create_window()
    clock = pygame.time.Clock()
    running = True
    try:
        while running:
            running = handle_events()
            screen.fill(BACKGROUND_COLOR)
            pygame.display.flip()
            clock.tick(TARGET_FPS)
    finally:
        pygame.quit()


def main() -> int:
    """Point d'entrée du script `batterie`."""
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
