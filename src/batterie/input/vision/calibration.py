"""Calibration guidée des zones de frappe : à partir de tes propres coups (cadrage M11).

Logique pure (aucune caméra, aucun pygame) : elle reçoit des ``VisionSample`` et produit une
``ZoneMap``. Principe : pour chaque élément, l'écran te demande de le frapper quelques fois,
là où tu le placerais ; on repère chaque coup dans la trajectoire de l'embout, puis on en
déduit la zone (où tu frappes) et son plan de frappe (à quelle hauteur le coup se déclenche)
d'après la course réelle de ton geste, pas d'après une valeur fixée d'avance.

Trois étapes :

- ``StrokeSegmenter`` repère un coup dans le flux de points (descente puis remontée) ;
- ``zone_from_strokes`` / ``zones_from_strokes`` transforment les coups d'un élément en zone,
  et répartissent la frontière entre deux zones voisines qui se chevaucheraient ;
- ``CalibrationRun`` déroule l'ensemble, élément par élément, et dit où il en est.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from batterie.core.elements import ELEMENTS_BY_ID
from batterie.input.vision.process import WORKING_WIDTH, VisionSample
from batterie.input.vision.zones import Zone, ZoneMap

# Les quatre éléments de la phase 04, de gauche à droite comme sur l'écran du kit.
CALIBRATION_ELEMENTS: tuple[str, ...] = ("hihat_closed", "snare", "tom_mid", "ride")
STROKES_PER_ELEMENT = 3
# Après un élément terminé, on ignore les coups de cette durée : le temps de voir qu'on change,
# et d'arrêter le geste. Un coup de trop sur l'élément précédent fausserait la zone suivante.
SETTLE_S = 1.5

# Repérage d'un coup dans une trajectoire (pixels de l'image réduite, y vers le bas).
DESCENT_START_PX = 12.0  # descente minimale depuis le point haut pour y voir un début de coup
RISE_END_PX = 10.0  # remontée minimale depuis le point bas pour considérer le coup terminé
MIN_STROKE_AMPLITUDE_PX = 25.0  # un coup plus court n'est qu'un mouvement parasite
MIN_PEAK_SPEED_PX_PER_S = 150.0  # un coup plus lent est un geste qui traîne

# Calcul d'une zone.
MIN_ZONE_AMPLITUDE_PX = 20.0  # course minimale entre le coup le moins relevé et le moins profond
PLANE_FRACTION = 0.6  # plan à 60 % de la course : assez haut pour gagner du temps, sous les tops
X_MARGIN_PX = 20.0  # marge de part et d'autre des coups, pour couvrir ta dispersion habituelle
# Au-delà, les coups ne sont pas « au même endroit ». Volontairement serré : un coup resté sur
# l'élément précédent (à un écartement de zone d'ici, ~70 px) doit passer pour un écart, pas pour
# une zone large.
MAX_X_SPREAD_PX = 50.0


class CalibrationError(ValueError):
    """Calibration impossible avec ces coups (le message dit quoi corriger)."""


@dataclass(frozen=True)
class Stroke:
    """Un coup repéré : où il touche (x, y du point bas), d'où il part (y du point haut)."""

    t_s: float
    x: float  # position du point bas
    top_y: float  # point haut avant la descente
    bottom_y: float  # point bas
    peak_speed_px_per_s: float


class StrokeSegmenter:
    """Repère les coups dans un flux de points (temps, x, y) d'un seul embout.

    Un coup = une descente d'au moins ``min_amplitude_px`` depuis le point haut, à une
    vitesse de pointe d'au moins ``min_peak_speed_px_per_s``, suivie d'une remontée d'au
    moins ``rise_end_px``. Le coup est annoncé à la remontée (la calibration n'a pas besoin
    d'être instantanée, contrairement au jeu).
    """

    def __init__(
        self,
        descent_start_px: float = DESCENT_START_PX,
        rise_end_px: float = RISE_END_PX,
        min_amplitude_px: float = MIN_STROKE_AMPLITUDE_PX,
        min_peak_speed_px_per_s: float = MIN_PEAK_SPEED_PX_PER_S,
    ) -> None:
        self.descent_start_px = descent_start_px
        self.rise_end_px = rise_end_px
        self.min_amplitude_px = min_amplitude_px
        self.min_peak_speed_px_per_s = min_peak_speed_px_per_s
        self.reset()

    def reset(self) -> None:
        """Oublie la trajectoire en cours (embout perdu de vue, par exemple)."""
        self._last: tuple[float, float] | None = None  # (t, y)
        self._top: float | None = None
        self._descending = False
        self._bottom = 0.0
        self._bottom_x = 0.0
        self._peak_speed = 0.0

    def update(self, t_s: float, x: float, y: float) -> Stroke | None:
        """Transmet un point ; renvoie le coup terminé à ce point, s'il y en a un."""
        speed = 0.0
        if self._last is not None:
            dt = t_s - self._last[0]
            if dt > 0:
                speed = (y - self._last[1]) / dt
        self._last = (t_s, y)

        if not self._descending:
            self._top = y if self._top is None else min(self._top, y)
            if y - self._top >= self.descent_start_px:
                self._descending = True
                self._bottom, self._bottom_x = y, x
                self._peak_speed = max(speed, 0.0)
            return None

        if y >= self._bottom:
            self._bottom, self._bottom_x = y, x
        self._peak_speed = max(self._peak_speed, speed)
        if self._bottom - y < self.rise_end_px:
            return None

        top = self._top if self._top is not None else y
        stroke = None
        if (
            self._bottom - top >= self.min_amplitude_px
            and self._peak_speed >= self.min_peak_speed_px_per_s
        ):
            stroke = Stroke(t_s, self._bottom_x, top, self._bottom, self._peak_speed)
        self._descending = False
        self._top = y
        return stroke


def _label(element_id: str) -> str:
    return ELEMENTS_BY_ID[element_id].label_fr


def zone_from_strokes(
    element_id: str,
    strokes: Sequence[Stroke],
    *,
    working_width: int = WORKING_WIDTH,
    min_strokes: int = STROKES_PER_ELEMENT,
) -> Zone:
    """Zone d'un élément, d'après les coups que tu lui as donnés.

    - largeur : de ton coup le plus à gauche au plus à droite, plus une marge ;
    - plan de frappe : à 60 % de la course entre le point haut du coup le moins relevé et le
      point bas du coup le moins profond, donc sous le haut et au-dessus du bas de *chacun* de
      tes coups : tous franchissent le plan.
    """
    name = _label(element_id)
    if len(strokes) < min_strokes:
        raise CalibrationError(f"{name} : il faut {min_strokes} coups, {len(strokes)} reçus")

    xs = [stroke.x for stroke in strokes]
    spread = max(xs) - min(xs)
    if spread > MAX_X_SPREAD_PX:
        raise CalibrationError(
            f"{name} : tes coups sont trop éloignés les uns des autres ({spread:.0f} px) : "
            "frappe toujours au même endroit"
        )

    top_ref = max(stroke.top_y for stroke in strokes)  # le coup le moins relevé
    bottom_ref = min(stroke.bottom_y for stroke in strokes)  # le coup le moins profond
    if bottom_ref - top_ref < MIN_ZONE_AMPLITUDE_PX:
        raise CalibrationError(
            f"{name} : gestes trop petits ou trop irréguliers : lève davantage l'embout "
            "entre deux coups, et frappe franchement"
        )

    return Zone(
        element_id=element_id,
        x_min=max(0.0, min(xs) - X_MARGIN_PX),
        x_max=min(float(working_width), max(xs) + X_MARGIN_PX),
        y_top=top_ref,
        strike_plane_y=top_ref + PLANE_FRACTION * (bottom_ref - top_ref),
        y_bottom=max(stroke.bottom_y for stroke in strokes),
    )


def zones_from_strokes(
    strokes_by_element: Mapping[str, Sequence[Stroke]],
    *,
    working_width: int = WORKING_WIDTH,
    min_strokes: int = STROKES_PER_ELEMENT,
) -> ZoneMap:
    """Zones de plusieurs éléments ; deux zones voisines qui se chevauchent sont séparées.

    La frontière se place à mi-chemin entre le coup le plus à droite de l'élément de gauche et
    le coup le plus à gauche de celui de droite. Si ces coups se croisent, il n'y a pas de
    frontière possible : erreur, il faut écarter les deux éléments.
    """
    raw = {
        element_id: zone_from_strokes(
            element_id, strokes, working_width=working_width, min_strokes=min_strokes
        )
        for element_id, strokes in strokes_by_element.items()
    }
    ordered = sorted(raw, key=lambda element_id: min(s.x for s in strokes_by_element[element_id]))
    bounds = {element_id: [raw[element_id].x_min, raw[element_id].x_max] for element_id in raw}

    for left, right in zip(ordered, ordered[1:], strict=False):
        if bounds[left][1] <= bounds[right][0]:
            continue
        left_edge = max(stroke.x for stroke in strokes_by_element[left])
        right_edge = min(stroke.x for stroke in strokes_by_element[right])
        if left_edge >= right_edge:
            raise CalibrationError(
                f"{_label(left)} et {_label(right)} : tes coups se mélangent. "
                "Écarte ces deux éléments l'un de l'autre"
            )
        boundary = (left_edge + right_edge) / 2
        bounds[left][1] = boundary
        bounds[right][0] = boundary

    zones = []
    for element_id in strokes_by_element:
        zone = raw[element_id]
        zones.append(
            Zone(
                element_id=element_id,
                x_min=bounds[element_id][0],
                x_max=bounds[element_id][1],
                y_top=zone.y_top,
                strike_plane_y=zone.strike_plane_y,
                y_bottom=zone.y_bottom,
            )
        )
    try:
        return ZoneMap(tuple(zones))
    except ValueError as error:  # chevauchement résiduel entre zones non voisines
        raise CalibrationError(str(error)) from error


class CalibrationRun:
    """Déroulé de la calibration : un élément après l'autre, quelques coups chacun.

    On lui transmet les images traitées (``handle_sample``) ; il repère les coups de n'importe
    quelle main, les attribue à l'élément demandé, et passe au suivant quand il en a assez.
    Si les coups d'un élément ne donnent pas de zone correcte, ``message`` dit pourquoi et
    l'élément est à refaire (rien d'autre n'est perdu).
    """

    def __init__(
        self,
        elements: Sequence[str] = CALIBRATION_ELEMENTS,
        strokes_per_element: int = STROKES_PER_ELEMENT,
        working_width: int = WORKING_WIDTH,
    ) -> None:
        if not elements:
            raise ValueError("la calibration a besoin d'au moins un élément")
        self.elements = tuple(elements)
        self.strokes_needed = strokes_per_element
        self.working_width = working_width
        self.message = ""
        self._strokes: dict[str, list[Stroke]] = {element_id: [] for element_id in self.elements}
        self._segmenters: dict[str, StrokeSegmenter] = {}
        self._index = 0
        self._zones = ZoneMap()
        self._ignore_until_s = 0.0

    @property
    def finished(self) -> bool:
        return self._index >= len(self.elements)

    @property
    def current_element(self) -> str | None:
        return None if self.finished else self.elements[self._index]

    @property
    def completed_elements(self) -> tuple[str, ...]:
        return self.elements[: self._index]

    @property
    def strokes_done(self) -> int:
        element_id = self.current_element
        return 0 if element_id is None else len(self._strokes[element_id])

    @property
    def contacts(self) -> list[tuple[float, float]]:
        """Points de contact (x, y bas) des coups déjà donnés à l'élément en cours."""
        element_id = self.current_element
        if element_id is None:
            return []
        return [(stroke.x, stroke.bottom_y) for stroke in self._strokes[element_id]]

    @property
    def zones(self) -> ZoneMap:
        """Zones des éléments déjà calibrés (toutes, une fois terminé)."""
        return self._zones

    def result(self) -> ZoneMap:
        if not self.finished:
            raise CalibrationError("la calibration n'est pas terminée")
        return self._zones

    def restart_current(self) -> None:
        """Efface les coups de l'élément en cours (tu t'es trompé), sans toucher aux autres."""
        element_id = self.current_element
        if element_id is not None:
            self._strokes[element_id].clear()
        self.message = ""
        for segmenter in self._segmenters.values():
            segmenter.reset()

    def handle_sample(self, sample: VisionSample) -> None:
        """Traite une image : repère les coups de chaque main, et avance si possible."""
        t_s = sample.t_ns / 1_000_000_000
        for name, marker in sample.markers.items():
            segmenter = self._segmenters.setdefault(name, StrokeSegmenter())
            if marker.point is None:
                segmenter.reset()
                continue
            stroke = segmenter.update(t_s, marker.point.x, marker.point.y)
            if stroke is not None:
                self._add_stroke(stroke)

    def _add_stroke(self, stroke: Stroke) -> None:
        element_id = self.current_element
        if element_id is None or stroke.t_s < self._ignore_until_s:
            return
        self.message = ""
        self._strokes[element_id].append(stroke)
        if len(self._strokes[element_id]) < self.strokes_needed:
            return

        attempt = {e: self._strokes[e] for e in (*self.completed_elements, element_id)}
        try:
            self._zones = zones_from_strokes(
                attempt, working_width=self.working_width, min_strokes=self.strokes_needed
            )
        except CalibrationError as error:
            self.message = f"{error}. On recommence cet élément."
            self._strokes[element_id].clear()
            return
        self._index += 1
        self._ignore_until_s = stroke.t_s + SETTLE_S
