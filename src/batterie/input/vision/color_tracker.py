"""Suit un embout de couleur dans une image (HSV), cadrage §3 et §6.4.

Testable sur des images synthétiques (``numpy.ndarray``) : ce module ne touche jamais
à une caméra, seulement à des tableaux déjà en mémoire.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# Pixels² minimum pour qu'une tache compte (ignore le bruit de capteur).
MIN_BLOB_AREA = 30.0


@dataclass(frozen=True)
class ColorRange:
    """Plage de couleur HSV à suivre (OpenCV : H 0-179, S et V 0-255)."""

    lower: tuple[int, int, int]
    upper: tuple[int, int, int]


@dataclass(frozen=True)
class TrackedPoint:
    """Centre (pixels) et aire (pixels²) de la plus grande tache détectée."""

    x: float
    y: float
    area: float


# Préréglages pour les couleurs suggérées par le cadrage (embout vert / magenta,
# cadrage §3 « Baguettes artificielles ») ; à recalibrer selon ta lumière réelle.
GREEN = ColorRange(lower=(40, 80, 60), upper=(85, 255, 255))
# Orange vif (main gauche, phase 04) : teinte 5 à 22 (l'orange pur est vers 15), mais surtout
# une saturation élevée (≥ 160). Une peau a la même teinte qu'un orange, avec une saturation
# bien plus basse (typiquement sous 150) : c'est la saturation qui sépare l'embout de la main.
# Conséquence voulue : un orange pâle n'est pas suivi, il faut un ruban ou un embout orange
# fluo. NON CALIBRÉ : à régler sur ton embout et ta lumière avec ``vision_debug.py --target hands``.
ORANGE = ColorRange(lower=(5, 160, 120), upper=(22, 255, 255))
MAGENTA = ColorRange(lower=(140, 80, 60), upper=(170, 255, 255))


def find_marker(frame_bgr: np.ndarray, color_range: ColorRange) -> TrackedPoint | None:
    """Cherche la plus grande tache de ``color_range`` dans ``frame_bgr``.

    Renvoie ``None`` si aucune tache d'au moins ``MIN_BLOB_AREA`` n'est trouvée.
    """
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(color_range.lower), np.array(color_range.upper))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    if area < MIN_BLOB_AREA:
        return None

    moments = cv2.moments(largest)
    if moments["m00"] == 0:
        return None

    x = moments["m10"] / moments["m00"]
    y = moments["m01"] / moments["m00"]
    return TrackedPoint(x=x, y=y, area=area)
