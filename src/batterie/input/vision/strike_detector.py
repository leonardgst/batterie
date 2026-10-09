"""Détecte un coup au franchissement d'un plan de frappe à vitesse descendante.

Cadrage §3 : « franchissement d'un plan de frappe à vitesse descendante suffisante,
avec anti-rebond ; déclenche avant le point bas, gagne une image de latence. »
Logique pure : fonctionne sur un flux d'échantillons (temps, position y en pixels),
qu'ils viennent d'une vraie caméra ou d'une trajectoire de test. L'axe image a son
origine en haut : y croît vers le bas, donc une vitesse positive = mouvement descendant.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_MIN_SPEED_PX_PER_S = 200.0
DEFAULT_REFRACTORY_S = 0.15


@dataclass
class StrikeDetector:
    """Détecte un coup quand le point suivi franchit ``strike_plane_y`` vers le bas.

    ``min_speed_px_per_s`` écarte les franchissements trop lents (geste qui traîne
    sans frapper) ; ``refractory_s`` est l'anti-rebond entre deux coups détectés.
    """

    strike_plane_y: float
    min_speed_px_per_s: float = DEFAULT_MIN_SPEED_PX_PER_S
    refractory_s: float = DEFAULT_REFRACTORY_S

    _last_sample: tuple[float, float] | None = field(default=None, init=False, repr=False)
    _last_hit_t: float | None = field(default=None, init=False, repr=False)

    def update(self, t_s: float, y: float) -> bool:
        """Transmet un échantillon (temps en secondes, position y en pixels).

        Renvoie ``True`` si ce point déclenche un coup.
        """
        hit = False
        if self._last_sample is not None:
            last_t, last_y = self._last_sample
            dt = t_s - last_t
            if dt > 0:
                speed = (y - last_y) / dt
                crossed_down = last_y < self.strike_plane_y <= y
                fast_enough = speed >= self.min_speed_px_per_s
                ready = self._last_hit_t is None or (t_s - self._last_hit_t) >= self.refractory_s
                if crossed_down and fast_enough and ready:
                    hit = True
                    self._last_hit_t = t_s

        self._last_sample = (t_s, y)
        return hit

    def reset(self) -> None:
        """Oublie l'échantillon précédent et l'anti-rebond (ex. après une coupure de suivi)."""
        self._last_sample = None
        self._last_hit_t = None
