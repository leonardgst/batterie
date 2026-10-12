"""Pourquoi un coup n'a pas été détecté : diagnostic d'une séance de mesure (phase 04).

Logique pure, sans caméra ni pygame. La séance de mesure sait *combien* de clics n'ont pas
été touchés ; ce module cherche *pourquoi*, en rejouant la trajectoire de l'embout (des
coordonnées, jamais d'images) autour de chaque clic manqué. Les causes possibles, dans
l'ordre où on les teste :

- ``NOT_SEEN`` : l'embout n'était pas vu (masqué, hors de l'image, perdu) ;
- ``PLANE_NOT_REACHED`` : la main n'est pas descendue jusqu'au plan de frappe (course trop
  courte : l'écart en pixels est donné) ;
- ``OUT_OF_ZONE`` : le plan a été franchi, mais hors du rectangle de l'élément attendu ;
- ``TOO_SLOW`` : franchi dans la zone, mais plus lentement que la vitesse minimale ;
- ``NOT_REARMED`` : franchi dans la zone, assez vite, mais la main n'était pas assez
  remontée depuis le coup précédent ;
- ``OTHER`` : tout semble en ordre (anti-rebond, écart de mesure) : à regarder à la main.

C'est un diagnostic *approché* (il refait le calcul du détecteur sur les positions reçues,
sans accès à son état interne) : il oriente le réglage, il ne le prouve pas.
"""

from __future__ import annotations

import statistics
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from batterie.input.vision.strike_detector import DEFAULT_MIN_SPEED_PX_PER_S
from batterie.input.vision.zones import Zone, ZoneMap

# (instant en s depuis le premier clic, x, y) ; x et y valent ``None`` quand l'embout n'est pas vu.
TrajectoryPoint = tuple[float, float | None, float | None]

LOOKBACK_S = 0.15  # on regarde aussi un peu avant la fenêtre du clic : le geste précède l'impact
NOT_SEEN_RATIO = 0.5  # plus de la moitié des images sans embout = « non vu »
REARM_LOOKBACK_S = 0.6  # pour mesurer la remontée avant le franchissement


class MissCause(Enum):
    NOT_SEEN = "embout non vu"
    PLANE_NOT_REACHED = "plan de frappe jamais atteint (course trop courte)"
    OUT_OF_ZONE = "plan franchi hors de la zone de l'élément"
    TOO_SLOW = "plan franchi trop lentement"
    NOT_REARMED = "main pas assez remontée depuis le coup précédent"
    OTHER = "rien d'anormal trouvé (anti-rebond ou écart de mesure)"


@dataclass(frozen=True)
class MissDiagnosis:
    """Un clic manqué : lequel, quelle cause, et la valeur qui la chiffre.

    ``value`` selon la cause : pixels qui manquaient pour atteindre le plan, pixels entre le
    franchissement et la zone, vitesse du franchissement (px/s), pixels de remontée.
    """

    index: int  # numéro du clic, à partir de 0
    cause: MissCause
    value: float | None = None


def _crossings(
    points: Sequence[tuple[float, float, float]], plane_y: float
) -> list[tuple[float, float, float]]:
    """Franchissements du plan vers le bas : (instant, x au franchissement, vitesse px/s)."""
    found = []
    for (t0, x0, y0), (t1, x1, y1) in zip(points, points[1:], strict=False):
        if t1 > t0 and y0 < plane_y <= y1:
            share = (plane_y - y0) / (y1 - y0)
            found.append((t0 + (t1 - t0) * share, x0 + (x1 - x0) * share, (y1 - y0) / (t1 - t0)))
    return found


def _distance_to_zone(zone: Zone, x: float) -> float:
    return max(zone.x_min - x, x - zone.x_max, 0.0)


def diagnose_click(
    index: int,
    zone: Zone,
    trajectory: Sequence[TrajectoryPoint],
    *,
    click_s: float,
    tolerance_s: float,
    min_speed_px_per_s: float = DEFAULT_MIN_SPEED_PX_PER_S,
) -> MissDiagnosis:
    """Cause probable du clic manqué ``index`` (``trajectory`` : la main qui devait frapper)."""
    start, end = click_s - tolerance_s - LOOKBACK_S, click_s + tolerance_s
    window = [point for point in trajectory if start <= point[0] <= end]
    seen = [(t, x, y) for t, x, y in window if x is not None and y is not None]
    if len(seen) < 2 or (len(window) - len(seen)) > NOT_SEEN_RATIO * len(window):
        return MissDiagnosis(index, MissCause.NOT_SEEN)

    plane = zone.strike_plane_y
    crossings = _crossings(seen, plane)
    if not crossings:
        deepest = max(y for _, _, y in seen)
        return MissDiagnosis(index, MissCause.PLANE_NOT_REACHED, plane - deepest)

    # Le franchissement qui correspond à ce clic est celui qui en est le plus proche.
    t_cross, x_cross, speed = min(crossings, key=lambda c: abs(c[0] - click_s))
    if not zone.contains_x(x_cross):
        return MissDiagnosis(index, MissCause.OUT_OF_ZONE, _distance_to_zone(zone, x_cross))
    if speed < min_speed_px_per_s:
        return MissDiagnosis(index, MissCause.TOO_SLOW, speed)

    before = [
        y
        for t, x, y in trajectory
        if t_cross - REARM_LOOKBACK_S <= t < t_cross and x is not None and y is not None
    ]
    if before:
        rise = plane - min(before)
        if rise < zone.rearm_margin_px:
            return MissDiagnosis(index, MissCause.NOT_REARMED, rise)
    return MissDiagnosis(index, MissCause.OTHER)


def diagnose_misses(
    missed: Sequence[int],
    *,
    zones: ZoneMap,
    trajectories: Mapping[str, Sequence[TrajectoryPoint]],
    expected_element: Callable[[int], str | None],
    hand_for_click: Callable[[int], str],
    click_time_s: Callable[[int], float],
    tolerance_s: float,
    min_speed_px_per_s: float = DEFAULT_MIN_SPEED_PX_PER_S,
) -> tuple[MissDiagnosis, ...]:
    """Diagnostic de chaque clic de ``missed`` (numéros à partir de 0), dans l'ordre."""
    diagnoses = []
    for index in missed:
        zone = zones.get(expected_element(index) or "")
        trajectory = trajectories.get(hand_for_click(index), ())
        if zone is None:
            diagnoses.append(MissDiagnosis(index, MissCause.OTHER))
            continue
        diagnoses.append(
            diagnose_click(
                index,
                zone,
                trajectory,
                click_s=click_time_s(index),
                tolerance_s=tolerance_s,
                min_speed_px_per_s=min_speed_px_per_s,
            )
        )
    return tuple(diagnoses)


def summarize_causes(
    diagnoses: Sequence[MissDiagnosis],
) -> list[tuple[MissCause, list[int], float | None]]:
    """Causes triées de la plus fréquente : (cause, clics concernés, valeur médiane)."""
    by_cause: dict[MissCause, list[MissDiagnosis]] = {}
    for diagnosis in diagnoses:
        by_cause.setdefault(diagnosis.cause, []).append(diagnosis)
    summary = []
    for cause, items in by_cause.items():
        values = [item.value for item in items if item.value is not None]
        median = statistics.median(values) if values else None
        summary.append((cause, [item.index for item in items], median))
    return sorted(summary, key=lambda entry: (-len(entry[1]), entry[0].name))
