"""Le kit synthétique doit être équilibré : la charleston fermée ne doit pas être un « tic » faible.

À crête égale, un son très court s'entend nettement plus faible qu'un son long : la
charleston fermée (50 ms au départ) ne sonnait jamais fort, même à pleine vélocité. Ce test
compare l'énergie pondérée A (proxy de l'oreille, pas une mesure de sonie) des sons du kit,
le tom médium servant de référence (jugé « parfait » à l'oreille par l'utilisateur).
"""

import tomllib
import wave
from pathlib import Path

import numpy as np
import pytest

KIT_DIR = Path(__file__).resolve().parent.parent / "assets" / "kits" / "default"


def _a_weight(frequencies: np.ndarray) -> np.ndarray:
    f2 = np.maximum(frequencies, 1.0) ** 2
    response = (12194**2 * f2**2) / (
        (f2 + 20.6**2) * np.sqrt((f2 + 107.7**2) * (f2 + 737.9**2)) * (f2 + 12194**2)
    )
    return response / 0.7943  # 0 dB à 1 kHz


def _read(element_id: str) -> tuple[np.ndarray, int]:
    with (KIT_DIR / "kit.toml").open("rb") as handle:
        files = tomllib.load(handle)["samples"][element_id]
    with wave.open(str(KIT_DIR / files[0])) as wav:
        rate = wav.getframerate()
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
    return samples.astype(np.float64) / 32767, rate


def _gain(element_id: str) -> float:
    with (KIT_DIR / "kit.toml").open("rb") as handle:
        return float(tomllib.load(handle)["gains"].get(element_id, 1.0))


def _loudness_db(element_id: str) -> float:
    """Énergie pondérée A du son à pleine vélocité (gain du kit compris), en dB."""
    samples, rate = _read(element_id)
    spectrum = np.fft.rfft(samples * _gain(element_id))
    weights = _a_weight(np.fft.rfftfreq(len(samples), 1 / rate))
    energy = np.sum(np.abs(spectrum * weights) ** 2) / len(samples) / rate
    return 10 * np.log10(energy)


def test_the_closed_hihat_is_not_much_quieter_than_the_mid_tom():
    assert _loudness_db("hihat_closed") >= _loudness_db("tom_mid") - 1.0


def test_the_snare_is_not_much_quieter_than_the_toms_or_the_closed_hihat():
    snare = _loudness_db("snare")
    assert snare >= _loudness_db("tom_mid") - 1.0
    assert snare >= _loudness_db("hihat_closed") - 1.0


def test_the_closed_hihat_lasts_long_enough_to_be_heard():
    samples, rate = _read("hihat_closed")
    assert len(samples) / rate >= 0.1


def test_the_closed_hihat_is_still_quieter_than_the_open_one():
    assert _loudness_db("hihat_closed") < _loudness_db("hihat_open")


@pytest.mark.parametrize("element_id", ["kick", "snare", "tom_mid", "hihat_closed", "ride"])
def test_no_sound_clips_at_full_velocity(element_id):
    samples, _ = _read(element_id)
    assert np.abs(samples).max() * _gain(element_id) <= 0.9
