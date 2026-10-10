"""Les deux embouts du jeu à deux mains (phase 04) : main gauche orange, main droite verte.

Une seule définition pour l'application et les outils (``tools/vision_debug.py`` en repart
et un test vérifie qu'ils ne divergent pas). Valeurs de départ non calibrées : mêmes seuils
que la baguette, qui ont suffi en phase 03.
"""

from __future__ import annotations

from batterie.input.vision.color_tracker import GREEN, ORANGE
from batterie.input.vision.process import MarkerSpec
from batterie.input.vision.zones import ZoneMap

# L'image est retournée en miroir : ta main gauche apparaît à gauche, comme sur le kit.
HANDS_MIRROR = True

LEFT_HAND_NAME = "left"
RIGHT_HAND_NAME = "right"

# Plan de frappe de repli, utilisé tant qu'aucune zone n'est calibrée (outil de débogage).
DEFAULT_STRIKE_PLANE_Y = 150.0


def hand_specs(zones: ZoneMap | None = None) -> list[MarkerSpec]:
    """Les deux embouts à suivre ; avec ``zones``, chaque coup est attribué à son élément."""
    return [
        MarkerSpec(
            name=LEFT_HAND_NAME,
            color_range=ORANGE,
            strike_plane_y=DEFAULT_STRIKE_PLANE_Y,
            element_id="snare",
            zones=zones,
        ),
        MarkerSpec(
            name=RIGHT_HAND_NAME,
            color_range=GREEN,
            strike_plane_y=DEFAULT_STRIKE_PLANE_Y,
            element_id="snare",
            zones=zones,
        ),
    ]
