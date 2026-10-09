"""Tests du moteur audio : chargement du kit par défaut et étouffement de la charleston."""

from pathlib import Path

import pygame
import pytest

from batterie.audio.engine import AudioEngine, init_mixer, load_kit

KIT_DIR = Path(__file__).resolve().parent.parent / "assets" / "kits" / "default"

ELEMENT_IDS = [
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
]


@pytest.fixture(autouse=True)
def _mixer():
    init_mixer()
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def engine() -> AudioEngine:
    kit = load_kit(KIT_DIR)
    return AudioEngine(kit)


def test_load_kit_declares_a_license():
    kit = load_kit(KIT_DIR)
    assert kit.license
    assert kit.attribution


@pytest.mark.parametrize("element_id", ELEMENT_IDS)
def test_load_kit_has_a_sample_for_every_element(element_id: str):
    kit = load_kit(KIT_DIR)
    assert element_id in kit.samples
    assert len(kit.samples[element_id]) >= 1


def test_play_unknown_element_does_not_raise(engine: AudioEngine):
    engine.play("not_an_element")


def test_play_known_element_starts_a_channel(engine: AudioEngine):
    engine.play("snare")
    assert pygame.mixer.get_busy()


def test_closed_hihat_chokes_the_open_hihat(engine: AudioEngine):
    engine.play("hihat_open")
    open_sound = engine._kit.samples["hihat_open"][0]
    assert open_sound.get_num_channels() >= 1

    engine.play("hihat_closed")

    assert open_sound.get_num_channels() == 0


def test_hihat_pedal_also_chokes_the_open_hihat(engine: AudioEngine):
    engine.play("hihat_open")
    open_sound = engine._kit.samples["hihat_open"][0]

    engine.play("hihat_pedal")

    assert open_sound.get_num_channels() == 0


def test_kick_is_not_choked_by_hihat(engine: AudioEngine):
    engine.play("hihat_open")
    engine.play("kick")

    # Le kick ne doit jamais apparaître dans un groupe d'étouffement.
    assert "kick" not in engine._group_channels
