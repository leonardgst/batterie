"""Vue du kit : vu de dessus légèrement de face, touche sur chaque élément, illumination au coup."""

from __future__ import annotations

import time
from dataclasses import dataclass

import pygame

from batterie.core.elements import ELEMENTS, Element

FLASH_DURATION_S = 0.15
BACKGROUND_COLOR = (18, 18, 22)
BASE_COLOR = (55, 58, 70)

# Taille de canevas pour laquelle `_LAYOUT` est pensé ; `draw` adapte à toute zone.
DESIGN_SIZE = (1280, 720)
FLASH_COLOR = (255, 205, 90)
OUTLINE_COLOR = (225, 225, 230)
LABEL_COLOR = (230, 230, 235)

# Disposition approximative (x, y, rayon) sur la fenêtre, vue de dessus légèrement de face.
# Charleston fermée et ouverte partagent la même position : c'est le même élément physique.
_LAYOUT: dict[str, tuple[int, int, int]] = {
    "crash": (300, 190, 70),
    "tom_high": (560, 240, 55),
    "tom_mid": (720, 240, 55),
    "ride": (900, 200, 75),
    "hihat_closed": (240, 380, 55),
    "hihat_open": (240, 380, 55),
    "snare": (520, 420, 65),
    "tom_floor": (900, 440, 70),
    "hihat_pedal": (210, 580, 45),
    "kick": (640, 600, 90),
}


@dataclass(frozen=True)
class _Shape:
    element: Element
    center: tuple[int, int]
    radius: int


def _transform(
    point: tuple[int, int], radius: int, area: pygame.Rect
) -> tuple[tuple[int, int], int]:
    """Convertit une position/un rayon dessinés pour `DESIGN_SIZE` vers `area`."""
    scale = min(area.width / DESIGN_SIZE[0], area.height / DESIGN_SIZE[1])
    offset_x = area.x + (area.width - DESIGN_SIZE[0] * scale) / 2
    offset_y = area.y + (area.height - DESIGN_SIZE[1] * scale) / 2
    x = offset_x + point[0] * scale
    y = offset_y + point[1] * scale
    return (int(x), int(y)), max(1, int(radius * scale))


class KitView:
    """Dessine le kit et illumine l'élément qui vient d'être frappé."""

    def __init__(self) -> None:
        self._font = pygame.font.SysFont("consolas", 26, bold=True)
        self._flash_until: dict[str, float] = {}
        self._shapes = [
            _Shape(element, _LAYOUT[element.id][:2], _LAYOUT[element.id][2])
            for element in ELEMENTS
            if element.id in _LAYOUT
        ]

    def flash(self, element_id: str) -> None:
        """Marque ``element_id`` comme frappé : illuminé pendant ``FLASH_DURATION_S``."""
        self._flash_until[element_id] = time.perf_counter() + FLASH_DURATION_S

    def draw(self, screen: pygame.Surface, area: pygame.Rect | None = None) -> None:
        """Dessine le kit dans ``area`` (par défaut tout l'écran). N'efface pas le fond :
        l'appelant est responsable de ``screen.fill`` et de ``pygame.display.flip``."""
        if area is None:
            area = screen.get_rect()
        now = time.perf_counter()

        # Les shapes allumées sont dessinées en dernier : la charleston fermée et
        # ouverte partagent la même position, sinon l'une masquerait le flash de l'autre.
        def is_lit(shape: _Shape) -> bool:
            return self._flash_until.get(shape.element.id, 0.0) > now

        for shape in sorted(self._shapes, key=is_lit):
            center, radius = _transform(shape.center, shape.radius, area)
            color = FLASH_COLOR if is_lit(shape) else BASE_COLOR
            pygame.draw.circle(screen, color, center, radius)
            pygame.draw.circle(screen, OUTLINE_COLOR, center, radius, width=2)
            label = self._font.render(shape.element.key_label, True, LABEL_COLOR)
            screen.blit(label, label.get_rect(center=center))
