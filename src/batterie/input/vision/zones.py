"""Zones de frappe : à quel élément appartient un coup, et comment ne pas le compter deux fois.

Logique pure (ni caméra, ni OpenCV, ni pygame), testable sur des trajectoires de test.
Les coordonnées sont celles de l'image réduite du processus vision (``WORKING_WIDTH``,
voir ``input/vision/process.py``), après le miroir : x croît vers la droite, y vers le bas.

Une ``Zone`` est un rectangle de l'image, associé à un élément, avec son plan de frappe
(une ligne horizontale). Un coup = le point suivi franchit le plan vers le bas, à une
position x comprise dans la zone, assez vite. Le détecteur (``ZoneStrikeDetector``, un par
main) attribue ce coup à l'élément de la zone traversée.

**Contrainte de cette phase : les zones ne se chevauchent pas en largeur.** Une frappe
vers le bas sur un élément situé sous un autre traverserait d'abord le plan de celui du
dessus ; avec des zones côte à côte, ce cas n'existe pas (voir la phase 04, « Risques »).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from batterie.core.elements import ELEMENTS_BY_ID
from batterie.input.vision.strike_detector import (
    DEFAULT_MIN_SPEED_PX_PER_S,
    DEFAULT_REFRACTORY_S,
)

# Ré-armement après un coup : le point doit remonter au-dessus du plan d'au moins cette
# part de la hauteur de la zone (plan − haut), et jamais moins que ce minimum en pixels.
DEFAULT_REARM_FRACTION = 0.25
MIN_REARM_PX = 4.0


@dataclass(frozen=True)
class Zone:
    """Rectangle de l'image où l'on frappe un élément, et son plan de frappe.

    ``y_top`` est le plus haut où monte l'embout avant de frapper, ``y_bottom`` le plus
    bas où il descend, ``strike_plane_y`` la ligne dont le franchissement vers le bas
    déclenche le coup (entre les deux).
    """

    element_id: str
    x_min: float
    x_max: float
    y_top: float
    strike_plane_y: float
    y_bottom: float

    def __post_init__(self) -> None:
        if self.element_id not in ELEMENTS_BY_ID:
            raise ValueError(f"Zone : élément inconnu {self.element_id!r}")
        if not self.x_min < self.x_max:
            raise ValueError(
                f"Zone {self.element_id!r} : x_min ({self.x_min}) doit être inférieur à "
                f"x_max ({self.x_max})"
            )
        if not self.y_top < self.strike_plane_y <= self.y_bottom:
            raise ValueError(
                f"Zone {self.element_id!r} : il faut y_top ({self.y_top}) < strike_plane_y "
                f"({self.strike_plane_y}) <= y_bottom ({self.y_bottom})"
            )

    @property
    def rearm_margin_px(self) -> float:
        """Remontée minimale au-dessus du plan pour que le coup suivant soit possible."""
        return max(MIN_REARM_PX, DEFAULT_REARM_FRACTION * (self.strike_plane_y - self.y_top))

    def contains_x(self, x: float) -> bool:
        return self.x_min <= x <= self.x_max


@dataclass(frozen=True)
class ZoneMap:
    """L'ensemble des zones calibrées. Vide tant que rien n'a été calibré."""

    zones: tuple[Zone, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for zone in self.zones:
            if zone.element_id in seen:
                raise ValueError(f"Élément {zone.element_id!r} présent dans deux zones")
            seen.add(zone.element_id)
        ordered = sorted(self.zones, key=lambda zone: zone.x_min)
        for left, right in zip(ordered, ordered[1:], strict=False):
            if right.x_min < left.x_max:
                raise ValueError(
                    f"Les zones {left.element_id!r} et {right.element_id!r} se chevauchent en "
                    f"largeur (de {right.x_min} à {left.x_max}) : écarte-les ou recalibre"
                )

    def __iter__(self) -> Iterator[Zone]:
        return iter(self.zones)

    def __len__(self) -> int:
        return len(self.zones)

    def get(self, element_id: str) -> Zone | None:
        for zone in self.zones:
            if zone.element_id == element_id:
                return zone
        return None


class ZoneStrikeDetector:
    """Détecte les coups d'une main sur un ensemble de zones. Un détecteur par main.

    Un coup se déclenche quand le point suivi franchit vers le bas le plan d'une zone, à
    une position x (interpolée au moment du franchissement, donc juste même pour une
    frappe en diagonale) comprise dans la zone, à une vitesse d'au moins
    ``min_speed_px_per_s``. Deux protections contre le double coup :

    - **ré-armement** : après un coup, plus aucun coup tant que le point n'est pas remonté
      au-dessus du plan de la marge de la zone (``Zone.rearm_margin_px``). Un point qui
      tremble autour du plan, ou une frappe qui traverse deux plans, ne compte qu'une fois ;
    - **anti-rebond** : au moins ``refractory_s`` entre deux coups de la même main.
    """

    def __init__(
        self,
        zones: ZoneMap,
        min_speed_px_per_s: float = DEFAULT_MIN_SPEED_PX_PER_S,
        refractory_s: float = DEFAULT_REFRACTORY_S,
    ) -> None:
        self.zones = zones
        self.min_speed_px_per_s = min_speed_px_per_s
        self.refractory_s = refractory_s
        self._last_sample: tuple[float, float, float] | None = None  # (t, x, y)
        self._last_hit_t: float | None = None
        self._rearm_y: float | None = None  # None = armé ; sinon y à atteindre en remontant

    def update(self, t_s: float, x: float, y: float) -> Zone | None:
        """Transmet un échantillon (temps en secondes, x et y en pixels).

        Renvoie la zone frappée si cet échantillon déclenche un coup, sinon ``None``.
        """
        hit: Zone | None = None
        if self._rearm_y is not None and y <= self._rearm_y:
            self._rearm_y = None

        if self._last_sample is not None and self._rearm_y is None:
            last_t, last_x, last_y = self._last_sample
            dt = t_s - last_t
            ready = self._last_hit_t is None or (t_s - self._last_hit_t) >= self.refractory_s
            if dt > 0 and y > last_y and ready and (y - last_y) / dt >= self.min_speed_px_per_s:
                hit = self._struck_zone(last_x, last_y, x, y)

        if hit is not None:
            self._last_hit_t = t_s
            self._rearm_y = hit.strike_plane_y - hit.rearm_margin_px

        self._last_sample = (t_s, x, y)
        return hit

    def _struck_zone(self, last_x: float, last_y: float, x: float, y: float) -> Zone | None:
        """Zone dont le plan est franchi entre les deux points, la plus haute d'abord."""
        for zone in sorted(self.zones, key=lambda candidate: candidate.strike_plane_y):
            plane = zone.strike_plane_y
            if not last_y < plane <= y:
                continue
            crossing_x = last_x + (x - last_x) * (plane - last_y) / (y - last_y)
            if zone.contains_x(crossing_x):
                return zone
        return None

    def reset(self) -> None:
        """Oublie l'échantillon précédent, l'anti-rebond et le ré-armement."""
        self._last_sample = None
        self._last_hit_t = None
        self._rearm_y = None
