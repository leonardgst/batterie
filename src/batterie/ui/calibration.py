"""Écran « Calibrer la caméra » : te guide pour frapper chaque élément, puis enregistre les zones.

Tout le calcul est dans ``input/vision/calibration.py`` (testé sans écran) ; ici, la caméra
(``VisionFeed``), les touches et le dessin. Rien n'est écrit tant que tu n'as pas validé :
Échap abandonne et laisse ton ``zones.toml`` actuel intact.
"""

from __future__ import annotations

from enum import Enum, auto
from pathlib import Path

import pygame

from batterie.config.zones import save_zones
from batterie.core.elements import ELEMENTS_BY_ID
from batterie.input.vision.calibration import CalibrationRun
from batterie.input.vision.hands import HANDS_MIRROR, hand_specs
from batterie.input.vision.source import VisionFeed
from batterie.ui.camera_view import (
    draw_contacts,
    draw_frame,
    draw_markers,
    draw_zones,
    scale_for,
)

PREVIEW_WIDTH = 640
PREVIEW_ORIGIN = (20, 70)
PANEL_X = PREVIEW_ORIGIN[0] + PREVIEW_WIDTH + 30

TITLE_COLOR = (230, 230, 235)
TEXT_COLOR = (230, 230, 235)
DIM_COLOR = (150, 150, 160)
ACCENT_COLOR = (255, 205, 90)
ERROR_COLOR = (240, 120, 110)
DONE_COLOR = (120, 220, 140)

CAMERA_LOST_MESSAGE = (
    "Caméra introuvable ou déconnectée. Ferme les autres applications qui l'utilisent, "
    "puis réessaie."
)


class Phase(Enum):
    STARTING = auto()  # la caméra s'ouvre
    CALIBRATING = auto()
    REVIEW = auto()  # tous les éléments sont faits, en attente de validation
    SAVED = auto()
    ERROR = auto()


class CalibrationScreen:
    """Écran de calibration guidée : une caméra, un déroulé, un enregistrement."""

    def __init__(
        self,
        feed: VisionFeed,
        *,
        zones_file: Path | None = None,
        run: CalibrationRun | None = None,
    ) -> None:
        self.feed = feed
        self.zones_file = zones_file
        self.run = run or CalibrationRun()
        self.phase = Phase.STARTING
        self.error = ""
        pygame.font.init()
        self._title_font = pygame.font.SysFont("consolas", 32, bold=True)
        self._big_font = pygame.font.SysFont("consolas", 30, bold=True)
        self._font = pygame.font.SysFont("consolas", 20)
        self._small_font = pygame.font.SysFont("consolas", 16)

    @classmethod
    def open(cls, *, zones_file: Path | None = None) -> CalibrationScreen:
        """Ouvre l'écran avec la vraie caméra (les deux mains, image en miroir)."""
        feed = VisionFeed.start(hand_specs(), mirror=HANDS_MIRROR, send_frames=True)
        return cls(feed, zones_file=zones_file)

    # --- Logique ----------------------------------------------------------

    def update(self, events: list[pygame.event.Event]) -> bool:
        """Avance d'un tour de boucle. Renvoie ``False`` quand l'écran doit se fermer."""
        samples = self.feed.poll()
        if samples and self.phase is Phase.STARTING:
            self.phase = Phase.CALIBRATING
        if self.phase is Phase.CALIBRATING:
            for sample in samples:
                self.run.handle_sample(sample)
            if self.run.finished:
                self.phase = Phase.REVIEW

        if self.phase in (Phase.STARTING, Phase.CALIBRATING) and not self.feed.is_alive():
            self._fail(CAMERA_LOST_MESSAGE)

        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key == pygame.K_RETURN:
                if self.phase is Phase.REVIEW:
                    self._save()
                elif self.phase in (Phase.SAVED, Phase.ERROR):
                    return False
            elif event.key == pygame.K_r and self.phase is Phase.CALIBRATING:
                self.run.restart_current()
        return True

    def _save(self) -> None:
        try:
            save_zones(self.run.result(), self.zones_file, working_width=self.run.working_width)
        except OSError as error:
            self._fail(f"Impossible d'enregistrer les zones : {error}")
            return
        self.phase = Phase.SAVED

    def _fail(self, message: str) -> None:
        self.error = message
        self.phase = Phase.ERROR

    def close(self) -> None:
        self.feed.close()

    # --- Dessin -----------------------------------------------------------

    def draw(self, screen: pygame.Surface, area: pygame.Rect) -> None:
        title = self._title_font.render("Calibrer la caméra", True, TITLE_COLOR)
        screen.blit(title, (PREVIEW_ORIGIN[0], 20))

        self._draw_preview(screen)
        self._draw_panel(screen)

    def _draw_preview(self, screen: pygame.Surface) -> None:
        sample = self.feed.latest
        if sample is None or sample.frame_preview is None:
            waiting = self._font.render("Ouverture de la caméra…", True, DIM_COLOR)
            screen.blit(waiting, (PREVIEW_ORIGIN[0], PREVIEW_ORIGIN[1] + 20))
            return

        scale = scale_for(sample.frame_preview, PREVIEW_WIDTH)
        draw_frame(screen, PREVIEW_ORIGIN, scale, sample.frame_preview)
        highlight = self.run.current_element if self.phase is Phase.CALIBRATING else None
        draw_zones(
            screen, PREVIEW_ORIGIN, scale, self.run.zones, self._small_font, highlight=highlight
        )
        if self.phase is Phase.CALIBRATING:
            draw_contacts(screen, PREVIEW_ORIGIN, scale, self.run.contacts)
        draw_markers(screen, PREVIEW_ORIGIN, scale, sample)

    def _draw_panel(self, screen: pygame.Surface) -> None:
        x, y = PANEL_X, PREVIEW_ORIGIN[1]

        def write(text: str, font: pygame.font.Font, color: tuple[int, int, int]) -> None:
            nonlocal y
            screen.blit(font.render(text, True, color), (x, y))
            y += font.get_linesize() + 6

        if self.phase is Phase.STARTING:
            write("Ouverture de la caméra…", self._font, DIM_COLOR)
            write("", self._font, DIM_COLOR)
            write("Échap : annuler", self._small_font, DIM_COLOR)
            return

        if self.phase is Phase.ERROR:
            for line in _wrap(self.error, 38):
                write(line, self._font, ERROR_COLOR)
            write("", self._font, DIM_COLOR)
            write("Entrée ou Échap : retour", self._small_font, DIM_COLOR)
            return

        if self.phase is Phase.CALIBRATING:
            element = ELEMENTS_BY_ID[self.run.current_element or ""]
            write(f"Frappe : {element.label_fr}", self._big_font, ACCENT_COLOR)
            write(
                f"coup {self.run.strokes_done + 1} / {self.run.strokes_needed}",
                self._font,
                TEXT_COLOR,
            )
            write("", self._font, DIM_COLOR)
            write("Frappe toujours au même endroit,", self._small_font, TEXT_COLOR)
            write("comme si tu jouais cet élément.", self._small_font, TEXT_COLOR)
            for line in _wrap(self.run.message, 44):
                write(line, self._small_font, ERROR_COLOR)
        elif self.phase is Phase.REVIEW:
            write("Zones calibrées", self._big_font, DONE_COLOR)
            write("", self._font, DIM_COLOR)
            write("Les rectangles montrent où tu frappes,", self._small_font, TEXT_COLOR)
            write("la ligne rouge où le coup se déclenche.", self._small_font, TEXT_COLOR)
        elif self.phase is Phase.SAVED:
            write("Zones enregistrées", self._big_font, DONE_COLOR)
            write("", self._font, DIM_COLOR)
            write("Elles sont utilisées dès", self._small_font, TEXT_COLOR)
            write("le prochain jeu à la caméra.", self._small_font, TEXT_COLOR)

        write("", self._font, DIM_COLOR)
        self._draw_checklist(write)
        write("", self._font, DIM_COLOR)
        for hint in self._hints():
            write(hint, self._small_font, DIM_COLOR)

    def _draw_checklist(self, write) -> None:
        done = set(self.run.completed_elements)
        for element_id in self.run.elements:
            label = ELEMENTS_BY_ID[element_id].label_fr
            if element_id in done:
                write(f"[x] {label}", self._font, DONE_COLOR)
            elif element_id == self.run.current_element:
                write(f"[>] {label}", self._font, ACCENT_COLOR)
            else:
                write(f"[ ] {label}", self._font, DIM_COLOR)

    def _hints(self) -> list[str]:
        if self.phase is Phase.CALIBRATING:
            return ["R : recommencer cet élément", "Échap : annuler (rien n'est enregistré)"]
        if self.phase is Phase.REVIEW:
            return ["Entrée : enregistrer", "Échap : annuler (rien n'est enregistré)"]
        return ["Entrée ou Échap : retour"]


def _wrap(text: str, width: int) -> list[str]:
    """Coupe ``text`` en lignes d'au plus ``width`` caractères, aux espaces."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines
