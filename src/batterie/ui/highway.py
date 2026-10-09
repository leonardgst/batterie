"""Couloirs de coups qui défilent vers une ligne de frappe (cadrage US5).

La sélection des notes visibles (``visible_notes``) est pure logique, testable
sans pygame ; seul ``HighwayView.draw`` dépend de pygame pour le rendu.
"""

from __future__ import annotations

import time

import pygame

from batterie.core.elements import ELEMENTS
from batterie.core.score import Note, Score

PIXELS_PER_BEAT = 90
LOOKAHEAD_BEATS = 4.0
TRAIL_BEATS = 0.3
LABEL_MARGIN = 40
JUDGEMENT_DURATION_S = 0.4

LANE_BORDER_COLOR = (70, 70, 80)
NOTE_COLOR = (90, 200, 255)
ACCENT_NOTE_COLOR = (255, 205, 90)
GHOST_NOTE_COLOR = (90, 110, 130)
STRIKE_LINE_COLOR = (230, 230, 235)
LABEL_COLOR = (230, 230, 235)

JUDGEMENT_LABELS = {"perfect": "PARFAIT", "good": "BIEN", "miss": "RATÉ"}
JUDGEMENT_COLORS = {
    "perfect": (120, 220, 140),
    "good": (255, 205, 90),
    "miss": (220, 90, 90),
}


def visible_notes(score: Score, current_beat: float) -> list[tuple[Note, float]]:
    """Notes à afficher et leur décalage en beats par rapport à ``current_beat``.

    Un décalage positif = pas encore jouée (au-dessus de la ligne de frappe) ;
    0 = à jouer maintenant ; négatif = vient de passer.
    """
    visible = []
    for note in score.notes:
        offset = note.beat - current_beat
        if -TRAIL_BEATS <= offset <= LOOKAHEAD_BEATS:
            visible.append((note, offset))
    return visible


def _note_color(note: Note) -> tuple[int, int, int]:
    if note.velocity >= 1.0:
        return ACCENT_NOTE_COLOR
    if note.velocity < 0.5:
        return GHOST_NOTE_COLOR
    return NOTE_COLOR


class HighwayView:
    """Dessine les couloirs de coups pour un score, dans une zone de l'écran donnée."""

    def __init__(self) -> None:
        self._font = pygame.font.SysFont("consolas", 20, bold=True)
        self._judgement_font = pygame.font.SysFont("consolas", 32, bold=True)
        self._lane_elements = list(ELEMENTS)
        self._lane_index = {element.id: i for i, element in enumerate(self._lane_elements)}
        self._judgement: str | None = None
        self._judgement_until = 0.0

    def show_judgement(self, rating: str) -> None:
        """Affiche brièvement le résultat du dernier coup jugé (parfait/bien/raté)."""
        self._judgement = rating
        self._judgement_until = time.perf_counter() + JUDGEMENT_DURATION_S

    def draw(
        self, screen: pygame.Surface, area: pygame.Rect, score: Score, current_beat: float
    ) -> None:
        lane_count = len(self._lane_elements)
        lane_width = area.width / lane_count
        strike_y = area.bottom - LABEL_MARGIN

        for i, element in enumerate(self._lane_elements):
            lane_x = area.left + i * lane_width
            top, bottom = (lane_x, area.top), (lane_x, area.bottom)
            pygame.draw.line(screen, LANE_BORDER_COLOR, top, bottom, 1)
            label = self._font.render(element.key_label, True, LABEL_COLOR)
            screen.blit(label, label.get_rect(center=(lane_x + lane_width / 2, strike_y + 20)))

        strike_start, strike_end = (area.left, strike_y), (area.right, strike_y)
        pygame.draw.line(screen, STRIKE_LINE_COLOR, strike_start, strike_end, 3)

        radius = max(4, int(lane_width * 0.28))
        for note, offset in visible_notes(score, current_beat):
            lane_i = self._lane_index.get(note.element_id)
            if lane_i is None:
                continue
            x = area.left + lane_i * lane_width + lane_width / 2
            y = strike_y - offset * PIXELS_PER_BEAT
            pygame.draw.circle(screen, _note_color(note), (int(x), int(y)), radius)

        if self._judgement is not None and time.perf_counter() < self._judgement_until:
            label = JUDGEMENT_LABELS[self._judgement]
            color = JUDGEMENT_COLORS[self._judgement]
            surface = self._judgement_font.render(label, True, color)
            screen.blit(surface, surface.get_rect(center=(area.centerx, strike_y - 60)))
