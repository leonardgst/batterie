"""Événement de coup, unifié quelle que soit la source (cadrage §4.2).

Logique pure, sans pygame. Clavier, MIDI (Could) et vision (V3) produisent tous des
``HitEvent`` ; le reste du programme (son, jugement, défilement) ne connaît que ça.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Source(Enum):
    """Origine d'un coup."""

    KEYBOARD = "keyboard"
    MIDI = "midi"
    VISION = "vision"


@dataclass(frozen=True)
class HitEvent:
    """Un coup joué : élément touché, vélocité (0 à 1), horodatage (ns), source."""

    element_id: str
    velocity: float
    t_ns: int
    source: Source
