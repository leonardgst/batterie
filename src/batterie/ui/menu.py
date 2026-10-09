"""Liste de choix simple : navigation (testable sans pygame) et rendu."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

ITEM_COLOR = (200, 200, 210)
SELECTED_COLOR = (255, 205, 90)
TITLE_COLOR = (230, 230, 235)


@dataclass
class Menu[T]:
    """Sélection dans une liste d'éléments. Pas de rendu ici : testable sans pygame."""

    items: list[T]
    index: int = 0

    def move(self, delta: int) -> None:
        """Déplace la sélection de ``delta`` positions, en bouclant sur la liste."""
        if not self.items:
            return
        self.index = (self.index + delta) % len(self.items)

    @property
    def selected(self) -> T:
        return self.items[self.index]


def draw_menu(
    screen: pygame.Surface,
    area: pygame.Rect,
    title: str,
    labels: list[str],
    selected_index: int,
) -> None:
    """Dessine un titre et une liste verticale ; l'élément sélectionné est mis en avant."""
    title_font = pygame.font.SysFont("consolas", 36, bold=True)
    item_font = pygame.font.SysFont("consolas", 26)

    title_surface = title_font.render(title, True, TITLE_COLOR)
    screen.blit(title_surface, title_surface.get_rect(midtop=(area.centerx, area.top + 40)))

    start_y = area.top + 130
    for i, label in enumerate(labels):
        color = SELECTED_COLOR if i == selected_index else ITEM_COLOR
        prefix = "> " if i == selected_index else "  "
        surface = item_font.render(prefix + label, True, color)
        screen.blit(surface, surface.get_rect(midtop=(area.centerx, start_y + i * 38)))
