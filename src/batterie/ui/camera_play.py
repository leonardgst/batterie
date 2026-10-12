"""Écran « Jeu caméra » : tu joues dans le vide, le kit sonne au rythme de tes coups.

Le processus vision (``VisionFeed``) détecte les coups et les attribue à un élément d'après
tes zones calibrées ; ici, chaque coup reçu fait sonner l'élément **dès la lecture de
l'événement** (jamais depuis le rendu, CLAUDE.md §9) puis l'illumine. L'aperçu de la caméra,
avec les zones et les embouts, reste affiché pour voir si tu as bougé depuis la calibration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Protocol

import pygame

from batterie.config.settings import CameraSettings, VelocitySettings
from batterie.config.zones import ZonesError, load_zones, zones_path
from batterie.core.elements import ELEMENTS_BY_ID
from batterie.input.vision.hands import HANDS_MIRROR, hand_specs
from batterie.input.vision.process import WORKING_WIDTH, CameraInfo
from batterie.input.vision.source import VisionFeed
from batterie.input.vision.velocity import curve_from_settings
from batterie.input.vision.zones import ZoneMap
from batterie.ui.calibration import CAMERA_LOST_MESSAGE, wrap_text
from batterie.ui.camera_view import draw_frame, draw_markers, draw_zones, scale_for
from batterie.ui.kit_view import KitView

PREVIEW_WIDTH = 400
PREVIEW_ORIGIN = (20, 60)
PANEL_X = PREVIEW_ORIGIN[0] + PREVIEW_WIDTH + 30
KIT_TOP = 380  # le kit occupe le bas de la fenêtre, sous l'aperçu

TITLE_COLOR = (230, 230, 235)
TEXT_COLOR = (230, 230, 235)
DIM_COLOR = (150, 150, 160)
ACCENT_COLOR = (255, 205, 90)
ERROR_COLOR = (240, 120, 110)

NO_ZONES_MESSAGE = (
    "Aucune zone n'est calibrée. Va dans « Calibrer la caméra » à l'accueil, "
    "frappe tes quatre éléments, puis reviens ici."
)


class Player(Protocol):
    """Ce dont l'écran a besoin du moteur audio."""

    def play(self, element_id: str, velocity: float = 1.0) -> None: ...


@dataclass(frozen=True)
class LastHit:
    """Le dernier coup joué : pour régler la nuance en voyant vitesse et volume."""

    element_id: str
    speed_px_per_s: float | None
    velocity: float


class Phase(Enum):
    STARTING = auto()  # la caméra s'ouvre
    PLAYING = auto()
    NO_ZONES = auto()
    ERROR = auto()


class CameraPlayScreen:
    """Jeu à la caméra : un flux d'échantillons, des zones, un moteur audio, un kit à allumer."""

    def __init__(
        self,
        feed: VisionFeed | None,
        zones: ZoneMap,
        engine: Player,
        kit_view: KitView,
        *,
        error: str = "",
    ) -> None:
        self.feed = feed
        self.zones = zones
        self.engine = engine
        self.kit_view = kit_view
        self.error = error
        self.hits = 0
        self.last_hit: LastHit | None = None
        self.nuance = False  # vrai quand la vitesse du geste règle le volume
        self.camera: CameraInfo | None = None
        if feed is None:
            self.phase = Phase.ERROR if error else Phase.NO_ZONES
        else:
            self.phase = Phase.STARTING
        pygame.font.init()
        self._title_font = pygame.font.SysFont("consolas", 32, bold=True)
        self._big_font = pygame.font.SysFont("consolas", 26, bold=True)
        self._font = pygame.font.SysFont("consolas", 20)
        self._small_font = pygame.font.SysFont("consolas", 16)

    @classmethod
    def open(
        cls,
        engine: Player,
        kit_view: KitView,
        camera: CameraSettings,
        *,
        velocity: VelocitySettings | None = None,
        zones_file: Path | None = None,
    ) -> CameraPlayScreen:
        """Charge tes zones puis ouvre la caméra ; sans zones valides, la caméra reste fermée."""
        try:
            zones = load_zones(zones_file, working_width=WORKING_WIDTH)
        except ZonesError as error:
            message = f"{error}. Recalibre depuis « Calibrer la caméra »."
            return cls(None, ZoneMap(), engine, kit_view, error=message)
        if not len(zones):
            return cls(None, zones, engine, kit_view)
        curve = curve_from_settings(velocity) if velocity is not None else None
        feed = VisionFeed.start(
            hand_specs(zones, curve), mirror=HANDS_MIRROR, send_frames=True, camera=camera
        )
        screen = cls(feed, zones, engine, kit_view)
        screen.nuance = curve is not None
        return screen

    # --- Logique ----------------------------------------------------------

    def update(self, events: list[pygame.event.Event]) -> bool:
        """Avance d'un tour de boucle. Renvoie ``False`` quand l'écran doit se fermer."""
        if self.feed is not None and self.phase in (Phase.STARTING, Phase.PLAYING):
            samples = self.feed.poll()
            # Le son d'abord, sur tous les coups arrivés : rien ne passe avant lui.
            for sample in samples:
                for marker in sample.markers.values():
                    hit = marker.hit_event
                    if hit is None:
                        continue
                    self.engine.play(hit.element_id, hit.velocity)
                    self.kit_view.flash(hit.element_id)
                    self.hits += 1
                    self.last_hit = LastHit(hit.element_id, marker.hit_speed_px_per_s, hit.velocity)
                if sample.camera is not None:
                    self.camera = sample.camera
            if samples and self.phase is Phase.STARTING:
                self.phase = Phase.PLAYING
            if not self.feed.is_alive():
                self.error = CAMERA_LOST_MESSAGE
                self.phase = Phase.ERROR

        closing_keys = (
            (pygame.K_ESCAPE, pygame.K_RETURN)
            if self.phase in (Phase.NO_ZONES, Phase.ERROR)
            else (pygame.K_ESCAPE,)
        )
        return not any(
            event.type == pygame.KEYDOWN and event.key in closing_keys for event in events
        )

    def close(self) -> None:
        if self.feed is not None:
            self.feed.close()

    # --- Dessin -----------------------------------------------------------

    def draw(self, screen: pygame.Surface, area: pygame.Rect) -> None:
        title = self._title_font.render("Jeu caméra", True, TITLE_COLOR)
        screen.blit(title, (PREVIEW_ORIGIN[0], 14))

        if self.phase in (Phase.NO_ZONES, Phase.ERROR):
            self._draw_message(screen)
            return

        self._draw_preview(screen)
        self._draw_status(screen)
        kit_area = pygame.Rect(0, KIT_TOP, area.width, area.height - KIT_TOP)
        self.kit_view.draw(screen, kit_area)

    def _draw_message(self, screen: pygame.Surface) -> None:
        x, y = PREVIEW_ORIGIN[0], PREVIEW_ORIGIN[1] + 20
        text = NO_ZONES_MESSAGE if self.phase is Phase.NO_ZONES else self.error
        for line in wrap_text(text, 70):
            screen.blit(self._font.render(line, True, ERROR_COLOR), (x, y))
            y += self._font.get_linesize() + 6
        if self.phase is Phase.NO_ZONES:
            where = self._small_font.render(f"Zones lues dans : {zones_path()}", True, DIM_COLOR)
            screen.blit(where, (x, y + 10))
            y += 36
        hint = self._small_font.render("Entrée ou Échap : retour", True, DIM_COLOR)
        screen.blit(hint, (x, y + 20))

    def _draw_preview(self, screen: pygame.Surface) -> None:
        sample = self.feed.latest if self.feed is not None else None
        if sample is None or sample.frame_preview is None:
            waiting = self._font.render("Ouverture de la caméra…", True, DIM_COLOR)
            screen.blit(waiting, (PREVIEW_ORIGIN[0], PREVIEW_ORIGIN[1] + 20))
            return
        scale = scale_for(sample.frame_preview, PREVIEW_WIDTH)
        draw_frame(screen, PREVIEW_ORIGIN, scale, sample.frame_preview)
        draw_zones(screen, PREVIEW_ORIGIN, scale, self.zones, self._small_font)
        draw_markers(screen, PREVIEW_ORIGIN, scale, sample)

    def _nuance_lines(self) -> list[str]:
        """Vitesse et volume du dernier coup : de quoi régler ``[velocity]`` en jouant."""
        if not self.nuance:
            return ["nuance : désactivée (tous les coups à fond)"]
        if self.last_hit is None:
            return ["nuance : joue un coup pour voir sa vitesse"]
        hit = self.last_hit
        speed = "?" if hit.speed_px_per_s is None else f"{hit.speed_px_per_s:.0f} px/s"
        label = ELEMENTS_BY_ID[hit.element_id].label_fr
        return [
            f"dernier coup : {label}",
            f"  vitesse {speed} -> volume {hit.velocity * 100:.0f} %",
        ]

    def _draw_status(self, screen: pygame.Surface) -> None:
        x, y = PANEL_X, PREVIEW_ORIGIN[1]

        def write(text: str, font: pygame.font.Font, color: tuple[int, int, int]) -> None:
            nonlocal y
            screen.blit(font.render(text, True, color), (x, y))
            y += font.get_linesize() + 4

        sample = self.feed.latest if self.feed is not None else None
        if sample is None:
            write("Ouverture de la caméra…", self._font, DIM_COLOR)
        else:
            write(f"{sample.fps:.1f} images/s", self._big_font, ACCENT_COLOR)
            write(f"traitement {sample.processing_ms:.1f} ms par image", self._font, TEXT_COLOR)
            if self.camera is not None:
                write(f"caméra : {self.camera.describe()}", self._font, TEXT_COLOR)
            write(f"coups : {self.hits}", self._font, TEXT_COLOR)
            for line in self._nuance_lines():
                write(line, self._font, TEXT_COLOR)
            for name, label in (("left", "gauche (bleue)"), ("right", "droite (verte)")):
                if name in sample.markers and sample.markers[name].point is None:
                    write(f"main {label} : non vue", self._small_font, ERROR_COLOR)
        y += 10
        zone_labels = ", ".join(ELEMENTS_BY_ID[zone.element_id].label_fr for zone in self.zones)
        for line in wrap_text(f"Zones : {zone_labels}", 52):
            write(line, self._small_font, DIM_COLOR)
        write("Si tu as bougé, recalibre depuis l'accueil.", self._small_font, DIM_COLOR)
        write("Échap : retour à l'accueil", self._small_font, DIM_COLOR)
