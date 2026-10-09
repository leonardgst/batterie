"""Horloge du morceau : convertit les beats d'une partition en secondes réelles.

Logique pure, sans pygame. Une seule horloge sert au défilement (PR 4) et au
jugement (PR 5) : cadrage §4.1, « une seule horloge pour les sons, le défilement
et le jugement ». Pour éviter toute dérive cumulée, la position courante se
recalcule à chaque appel depuis le temps total écoulé (``now_ns`` fourni par
l'appelant, typiquement ``time.perf_counter_ns()``) plutôt que d'additionner des
petits deltas d'image en image.

Conversion beat -> secondes (cadrage R6) : secondes = beat × 60 / (bpm × facteur
de tempo).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

MIN_TEMPO_FACTOR = 0.5
MAX_TEMPO_FACTOR = 1.2
TEMPO_FACTOR_STEP = 0.05

NS_PER_SECOND = 1_000_000_000


def clamp_tempo_factor(factor: float) -> float:
    """Borne le facteur de tempo à [50 %, 120 %] (US6). Le pas de 5 % est géré par l'UI."""
    return max(MIN_TEMPO_FACTOR, min(MAX_TEMPO_FACTOR, factor))


@dataclass
class Transport:
    """Horloge d'un morceau : position en beats, tempo réglable, pause, décompte."""

    bpm: float
    time_signature: tuple[int, int]
    tempo_factor: float = 1.0

    _start_ns: int | None = field(default=None, repr=False, compare=False)
    _elapsed_ns_at_pause: int = field(default=0, repr=False, compare=False)
    _paused: bool = field(default=True, repr=False, compare=False)
    _beat_offset: float = field(default=0.0, repr=False, compare=False)

    @property
    def beats_per_measure(self) -> float:
        return float(self.time_signature[0])

    def beats_per_second(self) -> float:
        return (self.bpm * self.tempo_factor) / 60.0

    def seconds_per_beat(self) -> float:
        return 60.0 / (self.bpm * self.tempo_factor)

    def set_tempo_factor(self, factor: float) -> None:
        """Change le facteur de tempo (borné à [50 %, 120 %]) sans affecter la pause en cours."""
        self.tempo_factor = clamp_tempo_factor(factor)

    def start(self, now_ns: int, *, count_in_beats: float = 0.0) -> None:
        """Démarre l'horloge. Avec un décompte, ``current_beat`` part de
        ``-count_in_beats`` et atteint 0 à la fin du décompte."""
        self._start_ns = now_ns
        self._elapsed_ns_at_pause = 0
        self._paused = False
        self._beat_offset = -count_in_beats

    def pause(self, now_ns: int) -> None:
        """Met en pause (Échap, US5) ; ``current_beat`` se fige jusqu'à ``resume``."""
        if self._start_ns is not None and not self._paused:
            self._elapsed_ns_at_pause += now_ns - self._start_ns
            self._paused = True

    def resume(self, now_ns: int) -> None:
        if self._start_ns is not None and self._paused:
            self._start_ns = now_ns
            self._paused = False

    @property
    def is_paused(self) -> bool:
        return self._paused

    def elapsed_seconds(self, now_ns: int) -> float:
        """Secondes écoulées depuis ``start``, hors temps passé en pause."""
        if self._start_ns is None:
            return 0.0
        elapsed_ns = self._elapsed_ns_at_pause
        if not self._paused:
            elapsed_ns += now_ns - self._start_ns
        return elapsed_ns / NS_PER_SECOND

    def current_beat(self, now_ns: int) -> float:
        """Position actuelle dans le morceau, en beats (négative pendant le décompte)."""
        return self.elapsed_seconds(now_ns) * self.beats_per_second() + self._beat_offset

    def beat_to_elapsed_seconds(self, beat: float) -> float:
        """Secondes depuis ``start`` (hors pauses) où ``beat`` doit sonner."""
        return (beat - self._beat_offset) * self.seconds_per_beat()

    def metronome_ticks(self, *, from_beat: float, to_beat: float) -> list[float]:
        """Positions (en beats entiers) des clics de métronome dans ``[from_beat, to_beat]``."""
        if to_beat < from_beat:
            return []
        first_tick = math.ceil(from_beat)
        ticks = []
        beat = float(first_tick)
        while beat <= to_beat:
            ticks.append(beat)
            beat += 1.0
        return ticks
