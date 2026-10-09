"""Lecture du clavier par position physique (scancode) : AZERTY et QWERTY sans distinction.

Pas de ``pygame.key.set_repeat`` : SDL ne génère alors qu'un seul ``KEYDOWN`` par
appui, donc une touche maintenue ne déclenche qu'un seul coup (R3 du cadrage).
"""

from __future__ import annotations

import pygame

from batterie.core.elements import ELEMENTS

SCANCODE_TO_ELEMENT: dict[int, str] = {
    getattr(pygame, f"KSCAN_{element.default_scancode_name}"): element.id for element in ELEMENTS
}


class Keyboard:
    """Traduit des événements clavier pygame en identifiants d'élément frappé."""

    def __init__(self, scancode_map: dict[int, str] | None = None) -> None:
        self._scancode_map = scancode_map if scancode_map is not None else SCANCODE_TO_ELEMENT

    def poll(self, events: list[pygame.event.Event]) -> list[str]:
        """Renvoie les ids d'élément frappés (``KEYDOWN``) parmi ``events``."""
        hits = []
        for event in events:
            if event.type != pygame.KEYDOWN or getattr(event, "repeat", False):
                continue
            element_id = self._scancode_map.get(event.scancode)
            if element_id is not None:
                hits.append(element_id)
        return hits
