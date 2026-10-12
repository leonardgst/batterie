"""Tests des réglages utilisateur : chargement, modèle par défaut, sauvegarde."""

from pathlib import Path

from batterie.config.settings import CameraSettings, Settings, load_settings, save_settings
from batterie.core.elements import ELEMENTS


def test_load_settings_creates_a_commented_file_when_missing(tmp_path: Path):
    target = tmp_path / "settings.toml"

    settings = load_settings(target)

    assert target.exists()
    assert "#" in target.read_text(encoding="utf-8")
    assert settings.volume == 1.0
    assert len(settings.key_map) == len(ELEMENTS)
    for element in ELEMENTS:
        assert settings.key_map[element.id] == element.default_scancode_name


def test_load_settings_reads_an_existing_file(tmp_path: Path):
    target = tmp_path / "settings.toml"
    target.write_text('volume = 0.5\n\n[keys]\nkick = "M"\n', encoding="utf-8")

    settings = load_settings(target)

    assert settings.volume == 0.5
    assert settings.key_map["kick"] == "M"
    # Les éléments non mentionnés gardent leur touche par défaut.
    assert settings.key_map["snare"] == "F"


def test_load_settings_clamps_out_of_range_volume(tmp_path: Path):
    target = tmp_path / "settings.toml"
    target.write_text("volume = 3.0\n", encoding="utf-8")

    assert load_settings(target).volume == 1.0


def test_save_then_load_round_trips(tmp_path: Path):
    target = tmp_path / "settings.toml"
    original = Settings(key_map={"kick": "M"}, volume=0.3)

    save_settings(original, target)
    loaded = load_settings(target)

    assert loaded.volume == 0.3
    assert loaded.key_map["kick"] == "M"


def test_camera_defaults_when_there_is_no_camera_section(tmp_path: Path):
    target = tmp_path / "settings.toml"
    target.write_text('volume = 0.5\n\n[keys]\nkick = "M"\n', encoding="utf-8")

    assert load_settings(target).camera == CameraSettings()


def test_camera_section_is_read(tmp_path: Path):
    target = tmp_path / "settings.toml"
    target.write_text(
        "[camera]\ndevice_index = 1\nwidth = 1280\nheight = 720\nfps = 60\nmjpeg = true\n",
        encoding="utf-8",
    )

    assert load_settings(target).camera == CameraSettings(
        device_index=1, width=1280, height=720, fps=60, mjpeg=True
    )


def test_camera_section_may_set_only_some_values(tmp_path: Path):
    target = tmp_path / "settings.toml"
    target.write_text("[camera]\nfps = 60\n", encoding="utf-8")

    camera = load_settings(target).camera

    assert camera.fps == 60
    assert camera.width == CameraSettings().width


def test_invalid_camera_values_fall_back_to_the_defaults(tmp_path: Path):
    target = tmp_path / "settings.toml"
    target.write_text(
        '[camera]\nwidth = -5\nheight = "grand"\nfps = 0\ndevice_index = true\n',
        encoding="utf-8",
    )

    assert load_settings(target).camera == CameraSettings()


def test_default_template_documents_the_camera_without_activating_it(tmp_path: Path):
    target = tmp_path / "settings.toml"

    load_settings(target)

    text = target.read_text(encoding="utf-8")
    assert "# [camera]" in text
    assert "\n[camera]" not in text
    assert load_settings(target).camera == CameraSettings()  # le modèle se relit tel quel


def test_camera_round_trips(tmp_path: Path):
    target = tmp_path / "settings.toml"
    original = Settings(camera=CameraSettings(device_index=1, fps=60, mjpeg=True))

    save_settings(original, target)

    assert load_settings(target).camera == original.camera
