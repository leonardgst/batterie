"""Jugement des coups : écart entre le coup joué et la note attendue (cadrage R7).

Logique pure, sans pygame. Les temps se comparent en beats (le transport convertit
en secondes au besoin) ; ``seconds_per_beat`` sert uniquement à exprimer l'écart en
millisecondes pour le classer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PERFECT_WINDOW_MS = 35.0
GOOD_WINDOW_MS = 90.0
# Au-delà de ce délai après l'instant prévu, une note non jouée est comptée ratée.
MISS_GRACE_MS = GOOD_WINDOW_MS

Rating = str  # "perfect" | "good" | "miss"


def classify(error_ms: float) -> Rating:
    """Classe un écart (positif ou négatif), en millisecondes, selon cadrage R7."""
    abs_error = abs(error_ms)
    if abs_error <= PERFECT_WINDOW_MS:
        return "perfect"
    if abs_error <= GOOD_WINDOW_MS:
        return "good"
    return "miss"


@dataclass(frozen=True)
class Judgement:
    """Résultat du jugement d'un coup joué."""

    rating: Rating
    error_ms: float


@dataclass
class Judge:
    """Associe les coups joués aux notes attendues d'un score, par élément, et compte le score."""

    notes_by_element: dict[str, list[float]]
    seconds_per_beat: float
    _consumed: dict[str, list[bool]] = field(init=False)
    counts: dict[Rating, int] = field(init=False)

    def __post_init__(self) -> None:
        self._consumed = {
            element_id: [False] * len(beats) for element_id, beats in self.notes_by_element.items()
        }
        self.counts = {"perfect": 0, "good": 0, "miss": 0}

    def register_hit(self, element_id: str, hit_beat: float) -> Judgement | None:
        """Associe un coup à la note non consommée la plus proche de ``element_id``.

        Renvoie ``None`` s'il n'y a plus de note disponible pour cet élément.
        """
        beats = self.notes_by_element.get(element_id)
        if not beats:
            return None
        consumed = self._consumed[element_id]

        best_index: int | None = None
        best_distance: float | None = None
        for i, beat in enumerate(beats):
            if consumed[i]:
                continue
            distance = abs(beat - hit_beat)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_index = i

        if best_index is None:
            return None

        consumed[best_index] = True
        error_ms = (hit_beat - beats[best_index]) * self.seconds_per_beat * 1000.0
        judgement = Judgement(rating=classify(error_ms), error_ms=error_ms)
        self.counts[judgement.rating] += 1
        return judgement

    def expire_missed_notes(self, current_beat: float) -> int:
        """Compte « raté » les notes dont la fenêtre est dépassée sans avoir été jouées.

        Renvoie le nombre de notes ratées lors de cet appel (0 la plupart du temps).
        """
        grace_beats = (MISS_GRACE_MS / 1000.0) / self.seconds_per_beat
        missed = 0
        for element_id, beats in self.notes_by_element.items():
            consumed = self._consumed[element_id]
            for i, beat in enumerate(beats):
                if not consumed[i] and current_beat - beat > grace_beats:
                    consumed[i] = True
                    missed += 1
        if missed:
            self.counts["miss"] += missed
        return missed

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    @property
    def accuracy(self) -> float:
        """Fraction de coups « parfait » ou « bien » parmi les coups jugés, 0.0 si aucun."""
        if self.total == 0:
            return 0.0
        return (self.counts["perfect"] + self.counts["good"]) / self.total
