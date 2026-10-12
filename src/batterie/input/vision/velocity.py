"""Nuance : la vitesse du geste règle le volume du coup (phase 04, S7).

Logique pure, sans caméra ni pygame. Deux morceaux :

- ``SpeedWindow`` mesure la vitesse de descente de l'embout juste avant le coup : le pic
  sur les ~0,12 s qui précèdent (trois ou quatre images à 30 images/s), plus fiable que la
  vitesse entre deux images seulement, qui bouge d'une image à l'autre ;
- ``VelocityCurve`` transforme cette vitesse (pixels par seconde, dans l'image réduite du
  processus vision) en vélocité de 0 à 1, que le moteur audio applique comme volume.

Les vitesses dépendent de ta distance à la caméra et de ta taille dans l'image : les valeurs
par défaut sont des points de départ, à régler avec l'écran « Jeu caméra » qui affiche la
vitesse et le volume de ton dernier coup (section ``[velocity]`` de ``settings.toml``).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from batterie.config.settings import VelocitySettings

PEAK_WINDOW_S = 0.12


@dataclass(frozen=True)
class VelocityCurve:
    """Vitesse du geste -> vélocité (0 à 1).

    En dessous de ``soft_speed_px_per_s`` (le coup le plus doux qu'on détecte), la vélocité
    vaut ``floor`` ; au-dessus de ``hard_speed_px_per_s`` (le coup le plus fort), 1.0 ; entre
    les deux, elle monte de ``floor`` à 1.0 selon ``gamma`` (1 : régulier ; au-dessus de 1 :
    les coups moyens restent doux ; entre 0 et 1 : les coups moyens sonnent déjà fort).
    """

    soft_speed_px_per_s: float = 200.0
    hard_speed_px_per_s: float = 900.0
    floor: float = 0.3
    gamma: float = 1.0

    def __post_init__(self) -> None:
        if not 0 <= self.soft_speed_px_per_s < self.hard_speed_px_per_s:
            raise ValueError(
                f"Courbe de vélocité : il faut 0 <= soft ({self.soft_speed_px_per_s}) "
                f"< hard ({self.hard_speed_px_per_s})"
            )
        if not 0.0 <= self.floor <= 1.0:
            raise ValueError(f"Courbe de vélocité : floor ({self.floor}) doit être entre 0 et 1")
        if self.gamma <= 0:
            raise ValueError(f"Courbe de vélocité : gamma ({self.gamma}) doit être positif")

    def velocity(self, speed_px_per_s: float) -> float:
        """Vélocité (``floor`` à 1.0) d'un coup donné par une descente à cette vitesse."""
        span = self.hard_speed_px_per_s - self.soft_speed_px_per_s
        position = (speed_px_per_s - self.soft_speed_px_per_s) / span
        position = min(1.0, max(0.0, position))
        return self.floor + (1.0 - self.floor) * position**self.gamma


def curve_from_settings(settings: VelocitySettings) -> VelocityCurve | None:
    """La courbe des réglages ; ``None`` si la nuance est désactivée (tous les coups à 1.0)."""
    if not settings.enabled:
        return None
    return VelocityCurve(
        soft_speed_px_per_s=settings.soft_speed,
        hard_speed_px_per_s=settings.hard_speed,
        floor=settings.floor,
        gamma=settings.gamma,
    )


class SpeedWindow:
    """Les derniers points de l'embout, pour en tirer la vitesse de descente maximale."""

    def __init__(self, window_s: float = PEAK_WINDOW_S) -> None:
        self.window_s = window_s
        self._points: deque[tuple[float, float]] = deque()  # (t en s, y en pixels)

    def add(self, t_s: float, y: float) -> None:
        """Ajoute un point (temps en secondes, y vers le bas) et oublie les plus anciens."""
        self._points.append((t_s, y))
        while self._points and self._points[0][0] < t_s - self.window_s:
            self._points.popleft()

    def peak_downward_speed(self) -> float:
        """Plus grande vitesse de descente entre deux points consécutifs (0 s'il n'y en a pas)."""
        peak = 0.0
        points = list(self._points)
        for (t_before, y_before), (t_after, y_after) in zip(points, points[1:], strict=False):
            dt = t_after - t_before
            if dt > 0 and y_after > y_before:
                peak = max(peak, (y_after - y_before) / dt)
        return peak

    def reset(self) -> None:
        self._points.clear()
