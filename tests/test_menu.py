"""Tests de la logique de sélection du menu (sans pygame)."""

from batterie.ui.menu import Menu


def test_selected_starts_at_first_item():
    menu = Menu(items=["a", "b", "c"])
    assert menu.selected == "a"


def test_move_forward_wraps_around():
    menu = Menu(items=["a", "b", "c"])
    menu.move(1)
    assert menu.selected == "b"
    menu.move(1)
    menu.move(1)
    assert menu.selected == "a"


def test_move_backwards_wraps_too():
    menu = Menu(items=["a", "b", "c"])
    menu.move(-1)
    assert menu.selected == "c"


def test_move_on_empty_list_does_not_raise():
    menu: Menu[str] = Menu(items=[])
    menu.move(1)
