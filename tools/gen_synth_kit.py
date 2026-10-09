"""Génère un kit de sons synthétique de secours, sans aucune question de droits.

Ne lit ni ne redistribue aucun échantillon tiers : chaque son est calculé à partir
de formes d'onde simples (sinus, bruit blanc) avec la bibliothèque standard (``wave``,
``math``, ``random``). Le résultat est écrit dans ``assets/kits/default/`` avec son
``kit.toml`` et sa ``LICENSE`` (CC0-1.0, création originale du projet).

Usage : ``uv run python tools/gen_synth_kit.py``
"""

from __future__ import annotations

import math
import random
import struct
import wave
from collections.abc import Callable
from pathlib import Path

SAMPLE_RATE = 48_000
PEAK_AMPLITUDE = 0.85  # fraction de l'échelle 16 bits, garde une marge contre l'écrêtage
KIT_DIR = Path(__file__).resolve().parent.parent / "assets" / "kits" / "default"

Samples = list[float]


def _sine(freq_hz: float, duration_s: float, *, freq_end_hz: float | None = None) -> Samples:
    """Sinusoïde, avec glissando linéaire optionnel de ``freq_hz`` vers ``freq_end_hz``."""
    n = int(SAMPLE_RATE * duration_s)
    end = freq_end_hz if freq_end_hz is not None else freq_hz
    phase = 0.0
    out: Samples = []
    for i in range(n):
        t = i / n if n else 0.0
        freq = freq_hz + (end - freq_hz) * t
        phase += 2 * math.pi * freq / SAMPLE_RATE
        out.append(math.sin(phase))
    return out


def _white_noise(duration_s: float, *, seed: int) -> Samples:
    rng = random.Random(seed)
    n = int(SAMPLE_RATE * duration_s)
    return [rng.uniform(-1.0, 1.0) for _ in range(n)]


def _brighten(samples: Samples) -> Samples:
    """Différenciation simple (filtre passe-haut grossier) pour un bruit plus net."""
    return [samples[i] - (samples[i - 1] if i > 0 else 0.0) for i in range(len(samples))]


def _exponential_decay(n: int, tau_s: float) -> Samples:
    return [math.exp(-(i / SAMPLE_RATE) / tau_s) for i in range(n)]


def _apply_envelope(samples: Samples, tau_s: float) -> Samples:
    envelope = _exponential_decay(len(samples), tau_s)
    return [s * e for s, e in zip(samples, envelope, strict=True)]


def _mix(*layers: Samples) -> Samples:
    length = max(len(layer) for layer in layers)
    out = [0.0] * length
    for layer in layers:
        for i, value in enumerate(layer):
            out[i] += value
    return out


def _normalize(samples: Samples, peak: float = PEAK_AMPLITUDE) -> Samples:
    current_peak = max((abs(s) for s in samples), default=0.0)
    if current_peak == 0.0:
        return samples
    scale = peak / current_peak
    return [s * scale for s in samples]


def _kick(seed: int) -> Samples:
    body = _apply_envelope(_sine(150.0, 0.35, freq_end_hz=45.0), tau_s=0.09)
    click = _apply_envelope(_white_noise(0.01, seed=seed), tau_s=0.004)
    return _normalize(_mix(body, click))


def _snare(seed: int) -> Samples:
    noise = _apply_envelope(_brighten(_white_noise(0.18, seed=seed)), tau_s=0.05)
    body = _apply_envelope(_sine(200.0, 0.1), tau_s=0.035)
    return _normalize(_mix(noise, body))


def _hihat_closed(seed: int) -> Samples:
    noise = _apply_envelope(_brighten(_white_noise(0.05, seed=seed)), tau_s=0.012)
    return _normalize(noise)


def _hihat_open(seed: int) -> Samples:
    noise = _apply_envelope(_brighten(_white_noise(0.7, seed=seed)), tau_s=0.22)
    return _normalize(noise)


def _hihat_pedal(seed: int) -> Samples:
    noise = _apply_envelope(_white_noise(0.03, seed=seed), tau_s=0.006)
    return _normalize(noise, peak=0.4)


def _tom(freq_hz: float, seed: int) -> Samples:
    body = _apply_envelope(_sine(freq_hz, 0.45, freq_end_hz=freq_hz * 0.75), tau_s=0.14)
    click = _apply_envelope(_white_noise(0.01, seed=seed), tau_s=0.004)
    return _normalize(_mix(body, click))


def _crash(seed: int) -> Samples:
    noise = _apply_envelope(_brighten(_white_noise(1.6, seed=seed)), tau_s=0.5)
    shimmer = _apply_envelope(
        _mix(_sine(3600.0, 1.6), _sine(5200.0, 1.6), _sine(7400.0, 1.6)), tau_s=0.4
    )
    return _normalize(_mix(noise, [s * 0.25 for s in shimmer]))


def _ride(seed: int) -> Samples:
    ping = _apply_envelope(_sine(2600.0, 1.1), tau_s=0.35)
    noise = _apply_envelope(_brighten(_white_noise(1.1, seed=seed)), tau_s=0.3)
    return _normalize(_mix([s * 0.6 for s in ping], [s * 0.7 for s in noise]))


# élément -> (nom de fichier, générateur, graine de bruit)
ELEMENTS: dict[str, tuple[str, Callable[[int], Samples], int]] = {
    "kick": ("kick.wav", _kick, 1),
    "hihat_pedal": ("hihat_pedal.wav", _hihat_pedal, 2),
    "hihat_closed": ("hihat_closed.wav", _hihat_closed, 3),
    "hihat_open": ("hihat_open.wav", _hihat_open, 4),
    "snare": ("snare.wav", _snare, 5),
    "tom_high": ("tom_high.wav", lambda seed: _tom(300.0, seed), 6),
    "tom_mid": ("tom_mid.wav", lambda seed: _tom(220.0, seed), 7),
    "tom_floor": ("tom_floor.wav", lambda seed: _tom(150.0, seed), 8),
    "crash": ("crash.wav", _crash, 9),
    "ride": ("ride.wav", _ride, 10),
}

KIT_TOML = """\
# Kit synthétique de secours : généré par tools/gen_synth_kit.py, sans échantillon tiers.
name = "default"
license = "CC0-1.0"
attribution = "Projet Batterie — sons synthétiques générés par tools/gen_synth_kit.py"

[samples]
kick = ["kick.wav"]
hihat_pedal = ["hihat_pedal.wav"]
hihat_closed = ["hihat_closed.wav"]
hihat_open = ["hihat_open.wav"]
snare = ["snare.wav"]
tom_high = ["tom_high.wav"]
tom_mid = ["tom_mid.wav"]
tom_floor = ["tom_floor.wav"]
crash = ["crash.wav"]
ride = ["ride.wav"]

[gains]
kick = 1.0
hihat_pedal = 0.8
hihat_closed = 0.9
hihat_open = 0.9
snare = 1.0
tom_high = 0.95
tom_mid = 0.95
tom_floor = 0.95
crash = 0.9
ride = 0.9
"""

LICENSE_TEXT = """\
CC0 1.0 Universal (domaine public)

Les fichiers audio de ce dossier (assets/kits/default/) sont une création
originale du projet Batterie, générée par tools/gen_synth_kit.py à partir de
formes d'onde synthétiques (sinus, bruit blanc). Aucun échantillon tiers n'est
utilisé.

Dans la mesure permise par la loi, l'auteur dédie ce travail au domaine public
en renonçant à tous ses droits, y compris les droits d'auteur, dans le monde
entier, sous les termes de la licence CC0 1.0 Universal.

Texte complet de la licence : https://creativecommons.org/publicdomain/zero/1.0/
"""


def _write_wav(path: Path, samples: Samples) -> None:
    frames = struct.pack(
        f"<{len(samples)}h",
        *(max(-32768, min(32767, round(s * 32767))) for s in samples),
    )
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(frames)


def generate(output_dir: Path = KIT_DIR) -> None:
    """Génère tous les fichiers du kit synthétique dans ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for element_id, (filename, generator, seed) in ELEMENTS.items():
        samples = generator(seed)
        _write_wav(output_dir / filename, samples)
        print(f"  {element_id:<14} -> {filename}")

    (output_dir / "kit.toml").write_text(KIT_TOML, encoding="utf-8")
    (output_dir / "LICENSE").write_text(LICENSE_TEXT, encoding="utf-8")


def main() -> int:
    print(f"Génération du kit synthétique dans {KIT_DIR} ...")
    generate()
    print("Terminé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
