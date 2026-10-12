"""Séance de mesure guidée : coups détectés, attribution et latences (phases 03 et 04).

Logique pure, sans caméra, sans pygame ni OpenCV : ``tools/vision_measure.py`` joue
les clics et lit la caméra ou le clavier, ce module compte et résume. Une séance =
un coup par clic de métronome (50 coups à 80 BPM par défaut, critère de fin de la
phase 03). Chaque clic accepte au plus un coup, dans une fenêtre d'un demi-temps de
part et d'autre ; les détections en trop sont des faux coups.

Depuis la phase 04, une séance peut suivre un **motif** (``SessionPlan.pattern``) : chaque
clic a un élément attendu, et les coups reçus sont aussi comptés selon qu'ils sont attribués
au bon élément ou non. ``US7_PLAN`` est la séance du critère US7 (100 croches à 90 BPM,
motif de 8 croches sur 4 éléments, mains en alternance).

Tous les instants sont en secondes sur une même horloge (``time.perf_counter``, qui
est commune à tous les processus sous Windows depuis Python 3.10).
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import pairwise

from batterie.core.elements import ELEMENTS_BY_ID
from batterie.core.events import Source

# Critère de fin de la phase 03 : au moins 90 % des coups détectés.
DETECTION_TARGET = 0.90

# Critères US7 (phase 04, séance de 100 croches à 90 BPM sur 4 éléments, deux mains).
US7_DETECTION_TARGET = 0.95
US7_FALSE_HIT_MAX = 0.02  # faux coups, en part du nombre de clics
US7_ATTRIBUTION_TARGET = 0.95  # coups détectés attribués au bon élément
US7_LATENCY_MAX_MS = 60.0  # geste -> son
# Retard du moteur audio entre l'ordre de jouer et le son (ADR 0001), ajouté à la
# détection pour estimer la latence geste -> son : ce programme ne peut pas le mesurer.
AUDIO_ENGINE_DELAY_MS = 5.0


@dataclass(frozen=True)
class SessionPlan:
    """Déroulé d'une séance : tempo, nombre de coups mesurés, clics de décompte.

    ``clicks_per_beat`` vaut 2 pour des croches (deux clics par temps). ``pattern`` est la
    suite d'éléments attendus, répétée tant que la séance dure (vide : pas d'attribution à
    vérifier, comme en phase 03). ``detection_target`` est la part de coups à détecter.
    """

    bpm: float = 80.0
    hit_count: int = 50
    count_in_beats: int = 4
    clicks_per_beat: int = 1
    pattern: tuple[str, ...] = ()
    detection_target: float = DETECTION_TARGET

    @property
    def beat_interval_s(self) -> float:
        """Durée entre deux clics."""
        return 60.0 / (self.bpm * self.clicks_per_beat)

    def expected_element(self, index: int) -> str | None:
        """Élément à frapper sur le clic ``index`` ; ``None`` sans motif."""
        if not self.pattern:
            return None
        return self.pattern[index % len(self.pattern)]

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


# Motif de la séance US7 : 8 croches, deux mains en alternance (gauche sur les positions
# paires, droite sur les impaires), qui font sonner les 4 éléments côte à côte du kit.
US7_PATTERN = (
    "hihat_closed",  # gauche
    "snare",  # droite
    "snare",  # gauche
    "tom_mid",  # droite
    "hihat_closed",  # gauche
    "ride",  # droite
    "snare",  # gauche
    "tom_mid",  # droite
)
US7_PLAN = SessionPlan(
    bpm=90.0,
    hit_count=100,
    count_in_beats=8,  # une mesure de croches
    clicks_per_beat=2,
    pattern=US7_PATTERN,
    detection_target=US7_DETECTION_TARGET,
)


def hand_for_click(index: int) -> str:
    """Main qui joue le clic ``index`` du motif : ``"left"`` ou ``"right"`` en alternance."""
    return "left" if index % 2 == 0 else "right"


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


def _match(
    plan: SessionPlan, hits: Sequence[tuple[float, str | None]]
) -> tuple[dict[int, tuple[float, str | None]], int]:
    """Attribue chaque coup au clic le plus proche : ``{clic: (écart en s, élément)}``.

    Un clic ne garde qu'un coup, le plus proche de lui ; les autres comptent comme faux
    coups, ainsi que ceux qui tombent hors séance. ``hits`` : (instant, élément ou ``None``).
    """
    closest: dict[int, tuple[float, str | None]] = {}
    extra = 0
    for t_s, element_id in hits:
        index = math.floor(t_s / plan.beat_interval_s + 0.5)
        if not 0 <= index < plan.hit_count:
            extra += 1
            continue
        delta_s = t_s - plan.beat_time_s(index)
        if index in closest:
            extra += 1
            if abs(delta_s) < abs(closest[index][0]):
                closest[index] = (delta_s, element_id)
        else:
            closest[index] = (delta_s, element_id)
    return closest, extra


def match_hits(plan: SessionPlan, hit_times_s: Sequence[float]) -> tuple[list[float], int]:
    """Attribue chaque coup au clic le plus proche.

    ``hit_times_s`` est compté depuis le premier clic mesuré. Renvoie les écarts
    coup − clic en millisecondes (un par clic touché, positif = après le clic) et le
    nombre de faux coups (détection en trop sur un clic déjà touché, ou hors séance).
    """
    closest, extra = _match(plan, [(t_s, None) for t_s in hit_times_s])
    return [closest[index][0] * 1000 for index in sorted(closest)], extra


def count_attribution(
    plan: SessionPlan, hits: Sequence[tuple[float, str | None]]
) -> tuple[int, tuple[tuple[str, str, int], ...]]:
    """Coups attribués au bon élément, et les confusions (attendu, obtenu, nombre).

    Ne compte que les clics touchés par un coup dont l'élément est connu ; les confusions
    sont triées de la plus fréquente à la moins fréquente.
    """
    closest, _ = _match(plan, hits)
    correct = 0
    wrong: Counter[tuple[str, str]] = Counter()
    for index, (_, got) in closest.items():
        expected = plan.expected_element(index)
        if expected is None or got is None:
            continue
        if got == expected:
            correct += 1
        else:
            wrong[(expected, got)] += 1
    confusions = tuple(
        (expected, got, count)
        for (expected, got), count in sorted(wrong.items(), key=lambda item: (-item[1], item[0]))
    )
    return correct, confusions


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
    attributed: int | None = None  # coups sur le bon élément ; ``None`` sans motif ni caméra
    confusions: tuple[tuple[str, str, int], ...] = ()

    @property
    def missed(self) -> int:
        return self.plan.hit_count - self.detected

    @property
    def detection_rate(self) -> float:
        return self.detected / self.plan.hit_count

    @property
    def meets_target(self) -> bool:
        return self.detection_rate >= self.plan.detection_target

    @property
    def extra_rate(self) -> float:
        """Faux coups, en part du nombre de clics."""
        return self.extra / self.plan.hit_count

    @property
    def attribution_rate(self) -> float | None:
        """Part des coups détectés attribués au bon élément."""
        if self.attributed is None or self.detected == 0:
            return None
        return self.attributed / self.detected

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

    _hits_s: list[tuple[float, str | None]] = field(default_factory=list, init=False, repr=False)
    _frames: list[tuple[float, float, bool]] = field(default_factory=list, init=False, repr=False)

    def _in_session(self, t_s: float) -> bool:
        elapsed_s = t_s - self.first_beat_s
        return -self.plan.tolerance_s <= elapsed_s < self.plan.measured_duration_s

    def is_over(self, now_s: float) -> bool:
        return now_s - self.first_beat_s >= self.plan.measured_duration_s

    @property
    def hit_count(self) -> int:
        return len(self._hits_s)

    def add_hit(self, t_s: float, element_id: str | None = None) -> None:
        """Enregistre un coup ; ``element_id`` sert à vérifier l'attribution (séance à motif)."""
        if self._in_session(t_s):
            self._hits_s.append((t_s - self.first_beat_s, element_id))

    def add_frame(self, t_s: float, processing_ms: float, tracked: bool) -> None:
        """Enregistre une image traitée par le processus caméra."""
        if self._in_session(t_s):
            self._frames.append((t_s, processing_ms, tracked))

    def result(self) -> SessionResult:
        closest, extra = _match(self.plan, self._hits_s)
        offsets_ms = [closest[index][0] * 1000 for index in sorted(closest)]
        attributed, confusions = None, ()
        if self.plan.pattern and self.source is Source.VISION:
            attributed, confusions = count_attribution(self.plan, self._hits_s)
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
            attributed=attributed,
            confusions=confusions,
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


def latency_to_sound_ms(vision: SessionResult, reference: SessionResult) -> float | None:
    """Latence geste -> son estimée : retard de la caméra sur le clavier + moteur audio."""
    offset_ms = offset_vs_reference_ms(vision, reference)
    if offset_ms is None:
        return None
    return offset_ms + AUDIO_ENGINE_DELAY_MS


@dataclass(frozen=True)
class Check:
    """Un critère de la définition de fin : ce qui est mesuré, ce qui est exigé, atteint ou non."""

    label: str
    value: str
    criterion: str
    met: bool | None  # ``None`` : pas évaluable (il manque la séance clavier de référence)


def us7_checks(result: SessionResult, reference: SessionResult | None = None) -> list[Check]:
    """Les quatre critères US7 d'une séance caméra à motif ; vide pour toute autre séance."""
    if not result.plan.pattern or result.source is not Source.VISION:
        return []
    checks = [
        Check(
            "Coups détectés",
            f"{_percent(result.detection_rate)} ({result.detected} / {result.plan.hit_count})",
            f"≥ {_percent(US7_DETECTION_TARGET)}",
            result.detection_rate >= US7_DETECTION_TARGET,
        ),
        Check(
            "Faux coups",
            f"{_percent(result.extra_rate)} ({result.extra})",
            f"≤ {_percent(US7_FALSE_HIT_MAX)}",
            result.extra_rate <= US7_FALSE_HIT_MAX,
        ),
    ]
    attribution = result.attribution_rate
    checks.append(
        Check(
            "Attribués au bon élément",
            "—"
            if attribution is None
            else f"{_percent(attribution)} ({result.attributed} / {result.detected})",
            f"≥ {_percent(US7_ATTRIBUTION_TARGET)}",
            None if attribution is None else attribution >= US7_ATTRIBUTION_TARGET,
        )
    )
    latency = latency_to_sound_ms(result, reference) if reference is not None else None
    checks.append(
        Check(
            "Latence geste → son",
            "— (fais la séance clavier de référence)" if latency is None else f"{latency:+.0f} ms",
            f"≤ {US7_LATENCY_MAX_MS:.0f} ms",
            None if latency is None else latency <= US7_LATENCY_MAX_MS,
        )
    )
    return checks


def _percent(ratio: float) -> str:
    return f"{ratio * 100:.0f} %"


def format_report(result: SessionResult, reference: SessionResult | None = None) -> list[str]:
    """Résumé lisible d'une séance, ligne par ligne (écran de fin et console).

    ``reference`` : séance clavier à laquelle comparer une séance caméra.
    """
    plan = result.plan
    name = "caméra" if result.source is Source.VISION else "clavier (référence)"
    verdict = "atteint" if result.meets_target else "non atteint"
    kind = " (croches)" if plan.clicks_per_beat == 2 else ""
    target = _percent(plan.detection_target)
    lines = [
        f"Séance {name} — {plan.hit_count} coups à {plan.bpm:.0f} BPM{kind}",
        f"Coups détectés : {result.detected} / {plan.hit_count} "
        f"({_percent(result.detection_rate)}) — critère ≥ {target} : {verdict}",
        f"Faux coups (détections en trop) : {result.extra}",
    ]
    if result.attributed is not None:
        lines.append(f"Coups sur le bon élément : {result.attributed} / {result.detected}")
        for expected, got, count in result.confusions:
            lines.append(
                f"  attendu {ELEMENTS_BY_ID[expected].label_fr}, "
                f"obtenu {ELEMENTS_BY_ID[got].label_fr} : {count}"
            )
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
    checks = us7_checks(result, reference)
    if checks:
        lines.append("Critères US7 :")
        for check in checks:
            mark = {True: "atteint", False: "NON ATTEINT", None: "à mesurer"}[check.met]
            lines.append(f"  {check.label} : {check.value} — critère {check.criterion} : {mark}")
    return lines
