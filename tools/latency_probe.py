"""Mesure la latence logicielle du moteur audio : appel ``AudioEngine.play`` -> mixeur.

Ne mesure pas la latence matérielle (carte son, casque, Bluetooth) : seulement le
temps pris côté Python pour remettre un son au mixeur SDL, plus la latence de
tampon théorique (tampon / fréquence). À comparer au critère de bascule de
l'ADR 0001 (voir docs/adr/0001-choix-du-moteur-audio.md).

Usage : ``uv run python tools/latency_probe.py``
"""

from __future__ import annotations

import statistics
import time
from pathlib import Path

import pygame

from batterie.audio.engine import MIXER_BUFFER, AudioEngine, init_mixer, load_kit

DEFAULT_KIT_DIR = Path(__file__).resolve().parent.parent / "assets" / "kits" / "default"
TRIALS = 200
ELEMENT = "snare"
PAUSE_BETWEEN_HITS_S = 0.05


def measure_trigger_latency_ms(engine: AudioEngine, element: str, trials: int) -> list[float]:
    """Mesure ``trials`` fois le temps d'appel de ``AudioEngine.play`` (en millisecondes)."""
    latencies_ms = []
    for _ in range(trials):
        start = time.perf_counter_ns()
        engine.play(element)
        end = time.perf_counter_ns()
        latencies_ms.append((end - start) / 1_000_000)
        time.sleep(PAUSE_BETWEEN_HITS_S)
    return latencies_ms


def main() -> int:
    init_mixer()
    pygame.init()

    kit = load_kit(DEFAULT_KIT_DIR)
    engine = AudioEngine(kit)

    freq, _fmt, channels = pygame.mixer.get_init()
    buffer_latency_ms = MIXER_BUFFER / freq * 1000

    latencies = measure_trigger_latency_ms(engine, ELEMENT, TRIALS)
    mean_ms = statistics.mean(latencies)

    print(f"Mixeur : {freq} Hz, {channels} canal(aux), tampon visé {MIXER_BUFFER} échantillons")
    print(f"Latence de tampon théorique : {buffer_latency_ms:.2f} ms")
    print(f"Appel AudioEngine.play — {TRIALS} essais sur « {ELEMENT} »")
    print(f"  moyenne : {mean_ms:.3f} ms")
    print(f"  médiane : {statistics.median(latencies):.3f} ms")
    print(f"  max     : {max(latencies):.3f} ms")
    total_ms = mean_ms + buffer_latency_ms
    print(f"Latence logicielle totale estimée (appel + tampon) : {total_ms:.3f} ms")

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
