"""Les dix éléments du kit et leur correspondance clavier par défaut (cadrage §2.4).

Logique pure : aucun import de pygame, testable sans fenêtre ni son.
``default_scancode_name`` correspond à la constante ``pygame.KSCAN_<nom>`` (position
physique de la touche) ; c'est ``input/keyboard.py`` qui fait cette traduction.
``key_label`` est le texte affiché sur le kit (lettre AZERTY du cadrage §2.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Limb(Enum):
    """Membre qui actionne l'élément."""

    HAND = "hand"
    FOOT = "foot"


@dataclass(frozen=True)
class Element:
    """Un élément du kit de batterie."""

    id: str
    label_fr: str
    limb: Limb
    gm_notes: tuple[int, ...]
    choke_group: str | None
    default_scancode_name: str
    key_label: str


ELEMENTS: tuple[Element, ...] = (
    Element("kick", "Grosse caisse", Limb.FOOT, (35, 36), None, "SPACE", "Espace"),
    Element("hihat_pedal", "Charleston (pédale)", Limb.FOOT, (44,), "hihat", "C", "C"),
    Element("hihat_closed", "Charleston fermée", Limb.HAND, (42,), "hihat", "D", "D"),
    Element("hihat_open", "Charleston ouverte", Limb.HAND, (46,), "hihat", "E", "E"),
    Element("snare", "Caisse claire", Limb.HAND, (37, 38, 40), None, "F", "F"),
    Element("tom_high", "Tom aigu", Limb.HAND, (48, 50), None, "J", "J"),
    Element("tom_mid", "Tom médium", Limb.HAND, (45, 47), None, "K", "K"),
    Element("tom_floor", "Tom basse", Limb.HAND, (41, 43), None, "L", "L"),
    # Touche AZERTY « Z » : même position physique que la touche QWERTY « W ».
    Element("crash", "Crash", Limb.HAND, (49, 57), None, "W", "Z"),
    Element("ride", "Ride", Limb.HAND, (51, 53, 59), None, "I", "I"),
)

ELEMENTS_BY_ID: dict[str, Element] = {element.id: element for element in ELEMENTS}
