"""Testeur de touches simultanées : repère les combinaisons que ton clavier ne gère pas.

Beaucoup de claviers ne peuvent pas reporter certaines combinaisons de touches
enfoncées en même temps (« ghosting », une limite du câblage du clavier, pas un
bug du programme). Ce testeur affiche les 10 touches du kit : une touche qui reste
grise alors que tu la maintiens enfoncée n'est pas reçue par Windows dans cette
combinaison précise.

Usage : ``uv run python tools/keytest.py``
"""

from __future__ import annotations

import pygame

from batterie.core.elements import ELEMENTS

WINDOW_TITLE = "Batterie — testeur de touches simultanées"
WINDOW_SIZE = (1150, 300)
TARGET_FPS = 60

BACKGROUND_COLOR = (18, 18, 22)
IDLE_COLOR = (55, 58, 70)
HELD_COLOR = (90, 220, 120)
OUTLINE_COLOR = (225, 225, 230)
TEXT_COLOR = (230, 230, 235)

BOX_SIZE = 95
BOX_GAP = 15
BOXES_TOP = 170

INSTRUCTIONS = [
    "Maintiens plusieurs touches du kit en même temps.",
    "Une touche qui reste grise malgré l'appui n'est pas reportée par ton clavier (ghosting).",
    "Essaie plusieurs combinaisons de 3 touches ou plus. Échap pour quitter.",
]


class PressTracker:
    """Suit les scancodes actuellement enfoncés à partir des événements clavier."""

    def __init__(self) -> None:
        self._held: set[int] = set()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._held.add(event.scancode)
        elif event.type == pygame.KEYUP:
            self._held.discard(event.scancode)

    def is_held(self, scancode: int) -> bool:
        return scancode in self._held

    def held_count(self) -> int:
        return len(self._held)


def _element_boxes() -> list[tuple[str, int, pygame.Rect]]:
    """(touche affichée, scancode, rectangle) pour chaque élément, en une rangée."""
    boxes = []
    for index, element in enumerate(ELEMENTS):
        scancode = getattr(pygame, f"KSCAN_{element.default_scancode_name}")
        x = BOX_GAP + index * (BOX_SIZE + BOX_GAP)
        boxes.append((element.key_label, scancode, pygame.Rect(x, BOXES_TOP, BOX_SIZE, BOX_SIZE)))
    return boxes


def run() -> None:
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption(WINDOW_TITLE)
    font = pygame.font.SysFont("consolas", 26, bold=True)
    small_font = pygame.font.SysFont("consolas", 18)

    tracker = PressTracker()
    boxes = _element_boxes()
    clock = pygame.time.Clock()

    running = True
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                else:
                    tracker.handle_event(event)

            screen.fill(BACKGROUND_COLOR)
            for i, line in enumerate(INSTRUCTIONS):
                text = small_font.render(line, True, TEXT_COLOR)
                screen.blit(text, (BOX_GAP, 20 + i * 24))

            count_label = f"Touches enfoncées : {tracker.held_count()}"
            count_text = font.render(count_label, True, TEXT_COLOR)
            screen.blit(count_text, (BOX_GAP, BOXES_TOP - 50))

            for label, scancode, rect in boxes:
                color = HELD_COLOR if tracker.is_held(scancode) else IDLE_COLOR
                pygame.draw.rect(screen, color, rect, border_radius=10)
                pygame.draw.rect(screen, OUTLINE_COLOR, rect, width=2, border_radius=10)
                label_surface = font.render(label, True, TEXT_COLOR)
                screen.blit(label_surface, label_surface.get_rect(center=rect.center))

            pygame.display.flip()
            clock.tick(TARGET_FPS)
    finally:
        pygame.quit()


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
