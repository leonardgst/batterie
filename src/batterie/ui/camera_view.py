"""Dessin de l'aperçu caméra : image, zones de frappe, embouts suivis.

Les coordonnées des zones et des points sont celles de l'image réduite du processus vision ;
``scale`` les agrandit à l'écran. Réutilisé par l'écran de calibration et, ensuite, par le jeu
à la caméra (phase 04, PR 4).
"""

from __future__ import annotations

import cv2
import numpy as np
import pygame

from batterie.core.elements import ELEMENTS_BY_ID
from batterie.input.vision.process import VisionSample
from batterie.input.vision.zones import Zone, ZoneMap

HAND_COLORS: dict[str, tuple[int, int, int]] = {
    "left": (255, 150, 40),  # orange
    "right": (90, 220, 120),  # vert
}
DEFAULT_MARKER_COLOR = (255, 205, 90)
ZONE_COLOR = (110, 170, 255)
ZONE_HIGHLIGHT_COLOR = (255, 255, 255)
PLANE_COLOR = (230, 90, 90)
CONTACT_COLOR = (255, 255, 255)
LABEL_COLOR = (230, 230, 235)


def frame_to_surface(frame_bgr: np.ndarray) -> pygame.Surface:
    """Convertit une image OpenCV (BGR, hauteur×largeur) en surface pygame."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return pygame.surfarray.make_surface(rgb.swapaxes(0, 1))


def scale_for(frame_bgr: np.ndarray, target_width: int) -> float:
    """Facteur d'agrandissement pour que l'image fasse ``target_width`` pixels de large."""
    return target_width / frame_bgr.shape[1]


def draw_frame(
    screen: pygame.Surface, origin: tuple[int, int], scale: float, frame_bgr: np.ndarray
) -> pygame.Rect:
    """Dessine l'image agrandie en ``origin`` ; renvoie le rectangle qu'elle occupe."""
    surface = frame_to_surface(frame_bgr)
    size = (round(surface.get_width() * scale), round(surface.get_height() * scale))
    scaled = pygame.transform.scale(surface, size)
    return screen.blit(scaled, origin)


def _to_screen(origin: tuple[int, int], scale: float, x: float, y: float) -> tuple[int, int]:
    return round(origin[0] + x * scale), round(origin[1] + y * scale)


def _wrap_to_width(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    """Coupe ``text`` aux espaces pour que chaque ligne tienne dans ``max_width`` pixels."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def draw_zone(
    screen: pygame.Surface,
    origin: tuple[int, int],
    scale: float,
    zone: Zone,
    font: pygame.font.Font,
    *,
    highlight: bool = False,
) -> None:
    """Dessine une zone : son rectangle, son plan de frappe (ligne rouge) et son nom."""
    color = ZONE_HIGHLIGHT_COLOR if highlight else ZONE_COLOR
    left, top = _to_screen(origin, scale, zone.x_min, zone.y_top)
    right, bottom = _to_screen(origin, scale, zone.x_max, zone.y_bottom)
    pygame.draw.rect(screen, color, pygame.Rect(left, top, right - left, bottom - top), width=2)
    plane_left, plane_y = _to_screen(origin, scale, zone.x_min, zone.strike_plane_y)
    plane_right, _ = _to_screen(origin, scale, zone.x_max, zone.strike_plane_y)
    pygame.draw.line(screen, PLANE_COLOR, (plane_left, plane_y), (plane_right, plane_y), 2)
    text_y = top + 2
    for line in _wrap_to_width(font, ELEMENTS_BY_ID[zone.element_id].label_fr, right - left - 8):
        screen.blit(font.render(line, True, color), (left + 4, text_y))
        text_y += font.get_linesize()


def draw_zones(
    screen: pygame.Surface,
    origin: tuple[int, int],
    scale: float,
    zones: ZoneMap,
    font: pygame.font.Font,
    *,
    highlight: str | None = None,
) -> None:
    for zone in zones:
        draw_zone(screen, origin, scale, zone, font, highlight=zone.element_id == highlight)


def draw_markers(
    screen: pygame.Surface, origin: tuple[int, int], scale: float, sample: VisionSample
) -> None:
    """Un cercle sur chaque embout vu, de la couleur de sa main ; blanc au moment d'un coup."""
    for name, marker in sample.markers.items():
        if marker.point is None:
            continue
        center = _to_screen(origin, scale, marker.point.x, marker.point.y)
        hit = marker.hit_event is not None
        color = CONTACT_COLOR if hit else HAND_COLORS.get(name, DEFAULT_MARKER_COLOR)
        pygame.draw.circle(screen, color, center, 12 if hit else 9, width=3)


def draw_contacts(
    screen: pygame.Surface,
    origin: tuple[int, int],
    scale: float,
    contacts: list[tuple[float, float]],
) -> None:
    """Un point plein à chaque endroit où l'embout a touché (coups déjà repérés)."""
    for x, y in contacts:
        pygame.draw.circle(screen, CONTACT_COLOR, _to_screen(origin, scale, x, y), 6)
