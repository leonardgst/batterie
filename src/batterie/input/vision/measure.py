"""Séance de mesure guidée : coups détectés et latences, pour le go/no-go (phase 03).

Logique pure, sans caméra, sans pygame ni OpenCV : ``tools/vision_measure.py`` joue
les clics et lit la caméra ou le clavier, ce module compte et résume. Une séance =
un coup par clic de métronome (50 coups à 80 BPM par défaut, critère de fin de la
phase 03). Chaque clic accepte au plus un coup, dans une fenêtre d'un demi-temps de
part et d'autre ; les détections en trop sont des faux coups.

Tous les instants sont en secondes sur une même horloge (``time.perf_counter``, qui
est commune à tous les processus sous Windows depuis Python 3.10).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import pairwise

from batterie.core.events import Source

# Critère de fin de la phase 03 : au moins 90 % des coups détectés.
DETECTION_TARGET = 0.90


@dataclass(frozen=True)
class SessionPlan:
    """Déroulé d'une séance : tempo, nombre de coups mesurés, clics de décompte."""

    bpm: float = 80.0
    hit_count: int = 50
    count_in_beats: int = 4

    @property
    def beat_interval_s(self) -> float:
        return 60.0 / self.bpm

    @property
    def tolerance_s(self) -> float:
        """Demi-fenêtre autour d'un clic dans laquelle un coup lui est attribué."""
        return self.beat_interval_s / 2

    @property
    def measured_duration_s(self) -> float:
        """Du premier clic mesuré à la fermeture de la fenêtre du dernier."""
        return (self.hit_count - 1) * self.beat_interval_s + self.tolerance_s

    def beat_time_s(self, index: int) -> float:
        """Instant du clic ``index`` après le premier clic mesuré (négatif = décompte)."""
        return index * self.beat_interval_s


@dataclass(frozen=True)
class Summary:
    """Résumé statistique d'une série de valeurs (toutes dans la même unité)."""

    count: int
    mean: float
    median: float
    p95: float
    maximum: float
    stdev: float


def summarize(values: Sequence[float]) -> Summary | None:
    """Résume ``values`` ; ``None`` si la série est vide."""
    if not values:
        return None
    ordered = sorted(values)
    p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return Summary(
        count=len(ordered),
        mean=statistics.fmean(ordered),
        median=statistics.median(ordered),
        p95=ordered[p95_index],
        maximum=ordered[-1],
        stdev=statistics.pstdev(ordered),
    )


def match_hits(plan: SessionPlan, hit_times_s: Sequence[float]) -> tuple[list[float], int]:
    """Attribue chaque coup au clic le plus proche.

    ``hit_times_s`` est compté depuis le premier clic mesuré. Renvoie les écarts
    coup − clic en millisecondes (un par clic touché, positif = après le clic) et le
    nombre de faux coups (détection en trop sur un clic déjà touché, ou hors séance).
    """
    closest: dict[int, float] = {}
    extra = 0
    for t_s in hit_times_s:
        index = math.floor(t_s / plan.beat_interval_s + 0.5)
        if not 0 <= index < plan.hit_count:
            extra += 1
            continue
        delta_s = t_s - plan.beat_time_s(index)
        if index in closest:
            extra += 1
            if abs(delta_s) < abs(closest[index]):
                closest[index] = delta_s
        else:
            closest[index] = delta_s
    return [closest[index] * 1000 for index in sorted(closest)], extra


@dataclass(frozen=True)
class SessionResult:
    """Résultat d'une séance. Les champs caméra sont ``None`` pour une séance clavier."""

    source: Source
    plan: SessionPlan
    detected: int
    extra: int
    offset_ms: Summary | None
    processing_ms: Summary | None = None
    frame_interval_ms: Summary | None = None
    tracked_ratio: float | None = None

    @property
    def missed(self) -> int:
        return self.plan.hit_count - self.detected

    @property
    def detection_rate(self) -> float:
        return self.detected / self.plan.hit_count

    @property
    def meets_target(self) -> bool:
        return self.detection_rate >= DETECTION_TARGET

    @property
    def fps(self) -> float | None:
        """Images par seconde réellement traitées (d'après l'intervalle médian)."""
        if self.frame_interval_ms is None or self.frame_interval_ms.median <= 0:
            return None
        return 1000 / self.frame_interval_ms.median

    @property
    def software_delay_ms(self) -> float | None:
        """Retard mesurable par logiciel : attente moyenne de l'image suivante
        (un demi-intervalle) + traitement. N'inclut pas le retard interne de la
        caméra (exposition, transfert), invisible depuis le programme."""
        if self.frame_interval_ms is None or self.processing_ms is None:
            return None
        return self.frame_interval_ms.median / 2 + self.processing_ms.median


@dataclass
class SessionRecorder:
    """Accumule les coups et les images d'une séance, puis calcule son résultat.

    ``first_beat_s`` est l'instant du premier clic mesuré. Ce qui tombe avant la
    fenêtre du premier clic (gestes d'échauffement pendant le décompte) ou après
    celle du dernier est ignoré.
    """

    plan: SessionPlan
    source: Source
    first_beat_s: float

    _hits_s: list[float] = field(default_factory=list, init=False, repr=False)
    _frames: list[tuple[float, float, bool]] = field(default_factory=list, init=False, repr=False)

    def _in_session(self, t_s: float) -> bool:
        elapsed_s = t_s - self.first_beat_s
        return -self.plan.tolerance_s <= elapsed_s < self.plan.measured_duration_s

    def is_over(self, now_s: float) -> bool:
        return now_s - self.first_beat_s >= self.plan.measured_duration_s

    @property
    def hit_count(self) -> int:
        return len(self._hits_s)

    def add_hit(self, t_s: float) -> None:
        if self._in_session(t_s):
            self._hits_s.append(t_s - self.first_beat_s)

    def add_frame(self, t_s: float, processing_ms: float, tracked: bool) -> None:
        """Enregistre une image traitée par le processus caméra."""
        if self._in_session(t_s):
            self._frames.append((t_s, processing_ms, tracked))

    def result(self) -> SessionResult:
        offsets_ms, extra = match_hits(self.plan, self._hits_s)
        frame_times_s = [t_s for t_s, _, _ in self._frames]
        intervals_ms = [(later - earlier) * 1000 for earlier, later in pairwise(frame_times_s)]
        tracked_ratio = None
        if self._frames:
            tracked_ratio = sum(tracked for _, _, tracked in self._frames) / len(self._frames)
        return SessionResult(
            source=self.source,
            plan=self.plan,
            detected=len(offsets_ms),
            extra=extra,
            offset_ms=summarize(offsets_ms),
            processing_ms=summarize([processing_ms for _, processing_ms, _ in self._frames]),
            frame_interval_ms=summarize(intervals_ms),
            tracked_ratio=tracked_ratio,
        )


def offset_vs_reference_ms(vision: SessionResult, reference: SessionResult) -> float | None:
    """Retard de la caméra par rapport au clavier, même joueur, même métronome.

    Différence des écarts médians coup − clic : ce que tu fais par rapport au clic
    (anticipation naturelle, retard de la sortie audio) est présent dans les deux
    séances et s'annule ; reste le retard propre à la détection par caméra. Peut être
    négatif : le plan de frappe se franchit avant le point bas du geste.
    """
    if vision.offset_ms is None or reference.offset_ms is None:
        return None
    return vision.offset_ms.median - reference.offset_ms.median


def _percent(ratio: float) -> str:
    return f"{ratio * 100:.0f} %"


def format_report(result: SessionResult, reference: SessionResult | None = None) -> list[str]:
    """Résumé lisible d'une séance, ligne par ligne (écran de fin et console).

    ``reference`` : séance clavier à laquelle comparer une séance caméra.
    """
    plan = result.plan
    name = "caméra" if result.source is Source.VISION else "clavier (référence)"
    verdict = "atteint" if result.meets_target else "non atteint"
    lines = [
        f"Séance {name} — {plan.hit_count} coups à {plan.bpm:.0f} BPM",
        f"Coups détectés : {result.detected} / {plan.hit_count} "
        f"({_percent(result.detection_rate)}) — critère ≥ {_percent(DETECTION_TARGET)} : {verdict}",
        f"Faux coups (détections en trop) : {result.extra}",
    ]
    if result.offset_ms is not None:
        lines.append(
            f"Écart coup − clic : médiane {result.offset_ms.median:+.0f} ms, "
            f"écart-type {result.offset_ms.stdev:.0f} ms"
        )
    if result.tracked_ratio is not None:
        lines.append(f"Embout visible : {_percent(result.tracked_ratio)} des images")
    if result.frame_interval_ms is not None and result.fps is not None:
        lines.append(
            f"Images/s réelles : {result.fps:.1f} "
            f"(intervalle médian {result.frame_interval_ms.median:.1f} ms, "
            f"max {result.frame_interval_ms.maximum:.1f} ms)"
        )
    if result.processing_ms is not None:
        lines.append(
            f"Traitement par image : médiane {result.processing_ms.median:.2f} ms, "
            f"p95 {result.processing_ms.p95:.2f} ms, max {result.processing_ms.maximum:.2f} ms"
        )
    if result.software_delay_ms is not None:
        lines.append(
            f"Retard logiciel estimé (demi-intervalle + traitement) : "
            f"{result.software_delay_ms:.1f} ms, hors retard interne de la caméra"
        )
    if reference is not None:
        offset_ms = offset_vs_reference_ms(result, reference)
        if offset_ms is not None:
            lines.append(f"Retard par rapport au clavier : {offset_ms:+.0f} ms")
    return lines
