"""Format de partition (grille façon tablature) et chargeur, cadrage §2.4.

Logique pure : aucun import de pygame. Une partition place ses notes en temps
musical (beats depuis le début du morceau) ; la conversion en secondes réelles,
selon le tempo, est le travail de ``core/transport.py`` (PR suivante), pas de ce
module.

Grille : une ligne par élément et par section, une case par symbole.
``-`` silence, ``x`` coup normal, ``X`` accent, ``g`` note fantôme (ghost).
Le swing (0.0 = croches droites, jusqu'à ~0.66 = ternaire/jazz) décale la
position du contretemps à l'intérieur de chaque paire de cases.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from batterie.core.elements import ELEMENTS_BY_ID

STYLES = ("rock", "jazz", "other", "solo")

# Symbole -> vélocité (0 à 1), ou None pour un silence.
SYMBOL_VELOCITY: dict[str, float | None] = {
    "-": None,
    "x": 0.8,
    "X": 1.0,
    "g": 0.3,
}


@dataclass(frozen=True)
class Note:
    """Un coup à jouer, en temps musical (beats depuis le début du morceau)."""

    beat: float
    element_id: str
    velocity: float


@dataclass(frozen=True)
class Score:
    """Une partition chargée : métadonnées et notes aplaties, triées par beat."""

    id: str
    title: str
    style: str
    bpm: float
    time_signature: tuple[int, int]
    grid: int
    swing: float
    difficulty: int
    author: str
    license: str
    notes: tuple[Note, ...]
    duration_beats: float

    @property
    def cell_duration_beats(self) -> float:
        """Durée d'une case de la grille, en beats."""
        return self.time_signature[0] / self.grid


def _off_beat_fraction(swing: float) -> float:
    """Position (0 à 1) du contretemps dans sa paire de cases. 0.5 = droit."""
    return 0.5 if swing == 0.0 else swing


def _parse_row(
    row: str,
    element_id: str,
    section_name: str,
    *,
    measure_start_beat: float,
    grid: int,
    cell_duration_beats: float,
    off_beat_fraction: float,
) -> list[Note]:
    if len(row) != grid:
        raise ValueError(
            f"Section {section_name!r} : la ligne de {element_id!r} a {len(row)} "
            f"case(s), {grid} attendue(s)"
        )

    notes: list[Note] = []
    for index, symbol in enumerate(row):
        if symbol not in SYMBOL_VELOCITY:
            raise ValueError(
                f"Section {section_name!r}, élément {element_id!r} : symbole "
                f"inconnu {symbol!r} (attendu : - x X g)"
            )

        velocity = SYMBOL_VELOCITY[symbol]
        if velocity is None:
            continue

        if index % 2 == 0:
            beat = measure_start_beat + index * cell_duration_beats
        else:
            on_beat = measure_start_beat + (index - 1) * cell_duration_beats
            beat = on_beat + 2 * cell_duration_beats * off_beat_fraction

        notes.append(Note(beat=beat, element_id=element_id, velocity=velocity))

    return notes


def _parse_sections(
    data: dict, *, time_signature: tuple[int, int], grid: int, swing: float
) -> tuple[list[Note], float]:
    cell_duration_beats = time_signature[0] / grid
    off_beat_fraction = _off_beat_fraction(swing)
    beats_per_measure = time_signature[0]

    notes: list[Note] = []
    measure_start_beat = 0.0

    for section in data.get("section", []):
        section_name = section.get("name", "?")
        repeat = int(section.get("repeat", 1))
        rows = {
            key: value
            for key, value in section.items()
            if key not in ("name", "repeat") and isinstance(value, str)
        }

        for element_id in rows:
            if element_id not in ELEMENTS_BY_ID:
                raise ValueError(f"Section {section_name!r} : élément inconnu {element_id!r}")

        for _ in range(repeat):
            for element_id, row in rows.items():
                notes.extend(
                    _parse_row(
                        row,
                        element_id,
                        section_name,
                        measure_start_beat=measure_start_beat,
                        grid=grid,
                        cell_duration_beats=cell_duration_beats,
                        off_beat_fraction=off_beat_fraction,
                    )
                )
            measure_start_beat += beats_per_measure

    notes.sort(key=lambda note: (note.beat, note.element_id))
    return notes, measure_start_beat


def load_score(path: Path) -> Score:
    """Charge une partition TOML. ``id`` est déduit du nom de fichier (sans extension)."""
    with path.open("rb") as handle:
        data = tomllib.load(handle)

    style = data["style"]
    if style not in STYLES:
        raise ValueError(f"Style inconnu {style!r} (attendu : {', '.join(STYLES)})")

    time_signature = tuple(data["time_signature"])
    grid = int(data["grid"])
    swing = float(data.get("swing", 0.0))

    notes, duration_beats = _parse_sections(
        data, time_signature=time_signature, grid=grid, swing=swing
    )

    return Score(
        id=path.stem,
        title=data["title"],
        style=style,
        bpm=float(data["bpm"]),
        time_signature=time_signature,
        grid=grid,
        swing=swing,
        difficulty=int(data.get("difficulty", 1)),
        author=data.get("author", ""),
        license=data.get("license", ""),
        notes=tuple(notes),
        duration_beats=duration_beats,
    )


def discover_scores(scores_dir: Path) -> list[Path]:
    """Liste les fichiers `.toml` sous ``scores_dir``, hors ``local/`` (non versionné)."""
    return sorted(
        path
        for path in scores_dir.rglob("*.toml")
        if "local" not in path.relative_to(scores_dir).parts
    )
