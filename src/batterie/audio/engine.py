"""Moteur audio : configuration du mixeur, chargement d'un kit, lecture des coups.

Interface minimale décrite dans l'ADR 0001 (``play``, ``choke``) pour pouvoir changer
de moteur plus tard sans toucher au reste du programme.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

import pygame

from batterie.core.elements import ELEMENTS

MIXER_FREQUENCY = 48_000
MIXER_SIZE = -16
MIXER_CHANNELS = 2
MIXER_BUFFER = 256
NUM_VOICES = 32

# Groupe d'étouffement : un nouveau coup dans ce groupe coupe le son encore en train
# de jouer dans le même groupe (R4 du cadrage : fermée ou pédale coupe l'ouverte).
# Dérivé de core/elements.py pour n'avoir qu'une seule source de vérité.
CHOKE_GROUPS: dict[str, str] = {
    element.id: element.choke_group for element in ELEMENTS if element.choke_group is not None
}


@dataclass(frozen=True)
class Kit:
    """Un kit chargé : échantillons et métadonnées de licence."""

    name: str
    license: str
    attribution: str
    samples: dict[str, list[pygame.mixer.Sound]]
    gains: dict[str, float]


def init_mixer() -> None:
    """Configure le mixeur basse latence. À appeler avant ``pygame.init()``."""
    pygame.mixer.pre_init(MIXER_FREQUENCY, MIXER_SIZE, MIXER_CHANNELS, MIXER_BUFFER)


def load_kit(kit_dir: Path) -> Kit:
    """Charge un kit depuis son dossier (``kit.toml`` + fichiers audio)."""
    with (kit_dir / "kit.toml").open("rb") as handle:
        data = tomllib.load(handle)

    samples = {
        element_id: [pygame.mixer.Sound(str(kit_dir / filename)) for filename in filenames]
        for element_id, filenames in data["samples"].items()
    }

    return Kit(
        name=data["name"],
        license=data["license"],
        attribution=data["attribution"],
        samples=samples,
        gains=dict(data.get("gains", {})),
    )


class AudioEngine:
    """Joue les coups d'un kit chargé, avec étouffement de groupe (charleston)."""

    def __init__(self, kit: Kit, master_volume: float = 1.0) -> None:
        pygame.mixer.set_num_channels(NUM_VOICES)
        self._kit = kit
        self._round_robin: dict[str, int] = {}
        self._group_channels: dict[str, pygame.mixer.Channel] = {}
        self._master_volume = _clamp01(master_volume)

    def set_master_volume(self, volume: float) -> None:
        """Change le volume général (0.0 à 1.0), appliqué à tous les coups suivants."""
        self._master_volume = _clamp01(volume)

    def play(self, element_id: str, velocity: float = 1.0) -> None:
        """Joue un coup sur ``element_id``. ``velocity`` entre 0 et 1 (1 au clavier)."""
        sounds = self._kit.samples.get(element_id)
        if not sounds:
            return

        group = CHOKE_GROUPS.get(element_id)
        if group is not None:
            self.choke(group)

        sound = self._next_sound(element_id, sounds)
        gain = self._kit.gains.get(element_id, 1.0)
        sound.set_volume(_clamp01(velocity) * gain * self._master_volume)
        channel = sound.play()

        if group is not None and channel is not None:
            self._group_channels[group] = channel

    def choke(self, group: str) -> None:
        """Coupe immédiatement le son en cours dans ``group``, s'il y en a un."""
        channel = self._group_channels.pop(group, None)
        if channel is not None:
            channel.stop()

    def _next_sound(self, element_id: str, sounds: list[pygame.mixer.Sound]) -> pygame.mixer.Sound:
        index = self._round_robin.get(element_id, 0)
        self._round_robin[element_id] = (index + 1) % len(sounds)
        return sounds[index]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))
