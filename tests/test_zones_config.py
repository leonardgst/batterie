"""Tests de zones.toml : lecture, écriture, erreurs claires. Aucun fichier utilisateur touché."""

import pytest

from batterie.config.settings import settings_path
from batterie.config.zones import ZonesError, load_zones, save_zones, zones_path
from batterie.input.vision.zones import Zone, ZoneMap

WIDTH = 320


def _zone(element_id: str, x_min: float, x_max: float) -> Zone:
    return Zone(element_id, x_min, x_max, y_top=60.0, strike_plane_y=150.5, y_bottom=190.0)


def _kit() -> ZoneMap:
    return ZoneMap(
        (
            _zone("hihat_closed", 10, 70),
            _zone("snare", 90, 150),
            _zone("tom_mid", 170, 230),
            _zone("ride", 250, 310),
        )
    )


def _write(tmp_path, text: str):
    path = tmp_path / "zones.toml"
    path.write_text(text, encoding="utf-8")
    return path


VALID_ZONE = """
[[zones]]
element = "snare"
x_min = 90.0
x_max = 150.0
y_top = 60.0
strike_plane_y = 150.0
y_bottom = 190.0
"""


def test_zones_file_sits_next_to_the_settings_file():
    assert zones_path().name == "zones.toml"
    assert zones_path().parent == settings_path().parent


def test_zones_survive_a_save_and_load(tmp_path):
    path = tmp_path / "zones.toml"
    save_zones(_kit(), path, working_width=WIDTH)
    assert load_zones(path, working_width=WIDTH) == _kit()


def test_saved_file_is_readable_text_that_says_not_to_edit_it(tmp_path):
    path = tmp_path / "zones.toml"
    save_zones(_kit(), path, working_width=WIDTH)
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# Zones de frappe")
    assert 'element = "ride"' in text
    assert f"working_width = {WIDTH}" in text


def test_save_creates_missing_folders_and_leaves_no_temporary_file(tmp_path):
    path = tmp_path / "deep" / "folder" / "zones.toml"
    save_zones(_kit(), path, working_width=WIDTH)
    assert path.exists()
    assert [p.name for p in path.parent.iterdir()] == ["zones.toml"]


def test_save_replaces_the_previous_zones(tmp_path):
    path = tmp_path / "zones.toml"
    save_zones(_kit(), path, working_width=WIDTH)
    save_zones(ZoneMap((_zone("snare", 90, 150),)), path, working_width=WIDTH)
    assert [z.element_id for z in load_zones(path)] == ["snare"]


def test_a_failed_save_leaves_the_previous_zones_untouched(tmp_path, monkeypatch):
    path = tmp_path / "zones.toml"
    save_zones(_kit(), path, working_width=WIDTH)
    before = path.read_bytes()

    def explode(*args, **kwargs):
        raise OSError("disque plein")

    monkeypatch.setattr("batterie.config.zones.tomli_w.dump", explode)
    with pytest.raises(OSError):
        save_zones(ZoneMap((_zone("snare", 0, 50),)), path, working_width=WIDTH)

    assert path.read_bytes() == before


def test_missing_file_means_nothing_is_calibrated(tmp_path):
    assert len(load_zones(tmp_path / "absent.toml")) == 0


def test_zones_calibrated_for_another_image_width_are_refused(tmp_path):
    path = tmp_path / "zones.toml"
    save_zones(_kit(), path, working_width=640)
    with pytest.raises(ZonesError, match=r"640 px.*utilise 320"):
        load_zones(path, working_width=WIDTH)
    assert len(load_zones(path)) == 4  # sans vérification de largeur, le fichier se lit


def test_garbage_file_names_the_file(tmp_path):
    path = _write(tmp_path, "ceci n'est pas du toml [[[")
    with pytest.raises(ZonesError, match="zones.toml"):
        load_zones(path)


def test_unknown_version_is_refused(tmp_path):
    path = _write(tmp_path, f"version = 99\nworking_width = {WIDTH}\n")
    with pytest.raises(ZonesError, match="version"):
        load_zones(path)


def test_missing_field_names_the_zone_and_the_field(tmp_path):
    body = VALID_ZONE.replace("y_bottom = 190.0\n", "")
    path = _write(tmp_path, f"version = 1\nworking_width = {WIDTH}\n{body}")
    with pytest.raises(ZonesError, match=r"zone n°1.*snare.*y_bottom"):
        load_zones(path)


def test_non_numeric_field_is_refused(tmp_path):
    body = VALID_ZONE.replace("x_min = 90.0", 'x_min = "gauche"')
    path = _write(tmp_path, f"version = 1\nworking_width = {WIDTH}\n{body}")
    with pytest.raises(ZonesError, match="x_min.*nombre"):
        load_zones(path)


def test_unknown_element_is_refused(tmp_path):
    body = VALID_ZONE.replace('"snare"', '"cowbell"')
    path = _write(tmp_path, f"version = 1\nworking_width = {WIDTH}\n{body}")
    with pytest.raises(ZonesError, match="cowbell"):
        load_zones(path)


def test_inverted_zone_is_refused(tmp_path):
    body = VALID_ZONE.replace("x_max = 150.0", "x_max = 50.0")
    path = _write(tmp_path, f"version = 1\nworking_width = {WIDTH}\n{body}")
    with pytest.raises(ZonesError, match="x_min"):
        load_zones(path)


def test_overlapping_zones_in_the_file_are_refused(tmp_path):
    second = VALID_ZONE.replace('"snare"', '"tom_mid"').replace("x_min = 90.0", "x_min = 120.0")
    path = _write(tmp_path, f"version = 1\nworking_width = {WIDTH}\n{VALID_ZONE}{second}")
    with pytest.raises(ZonesError, match="chevauchent"):
        load_zones(path)
