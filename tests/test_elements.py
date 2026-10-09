"""Tests de la table des éléments (logique pure, sans pygame, sans fenêtre ni son)."""

from batterie.core.elements import ELEMENTS, ELEMENTS_BY_ID, Limb

EXPECTED_IDS = {
    "kick",
    "hihat_pedal",
    "hihat_closed",
    "hihat_open",
    "snare",
    "tom_high",
    "tom_mid",
    "tom_floor",
    "crash",
    "ride",
}

HIHAT_IDS = {"hihat_pedal", "hihat_closed", "hihat_open"}


def test_ten_elements_defined():
    assert len(ELEMENTS) == 10
    assert {element.id for element in ELEMENTS} == EXPECTED_IDS


def test_elements_by_id_matches_elements():
    assert set(ELEMENTS_BY_ID) == EXPECTED_IDS
    for element in ELEMENTS:
        assert ELEMENTS_BY_ID[element.id] is element


def test_hihat_elements_share_the_choke_group():
    for element_id in HIHAT_IDS:
        assert ELEMENTS_BY_ID[element_id].choke_group == "hihat"


def test_non_hihat_elements_have_no_choke_group():
    for element in ELEMENTS:
        if element.id not in HIHAT_IDS:
            assert element.choke_group is None


def test_feet_elements_are_kick_and_hihat_pedal():
    foot_ids = {element.id for element in ELEMENTS if element.limb is Limb.FOOT}
    assert foot_ids == {"kick", "hihat_pedal"}


def test_default_scancode_names_are_unique():
    names = [element.default_scancode_name for element in ELEMENTS]
    assert len(names) == len(set(names))
