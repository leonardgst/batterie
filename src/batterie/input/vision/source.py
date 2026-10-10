"""Flux caméra pour l'application : démarre le processus vision et en lit les échantillons.

``VisionFeed`` enveloppe le processus (``multiprocessing``) et sa file de ``VisionSample`` :
l'application lit la file à chaque tour de boucle, sans jamais attendre (``poll`` ne
bloque pas), et sait si la caméra est encore là (``is_alive``). Rien ici ne touche à
pygame. L'écran de calibration s'en sert maintenant ; le jeu à la caméra (phase 04, PR 4)
s'en servira pour les coups.
"""

from __future__ import annotations

import multiprocessing as mp
import queue as queue_module
from collections.abc import Callable, Sequence
from typing import Any

from batterie.input.vision.process import MarkerSpec, VisionSample, run_markers_process

QUEUE_SIZE = 64
JOIN_TIMEOUT_S = 2.0


class VisionFeed:
    """Un processus vision en marche et sa file d'échantillons.

    Le constructeur reçoit une file et un processus déjà créés (ce qui permet de les
    remplacer dans les tests) ; ``VisionFeed.start`` crée les vrais.
    """

    def __init__(self, sample_queue: Any, process: Any) -> None:
        self._queue = sample_queue
        self._process = process
        self.latest: VisionSample | None = None

    @classmethod
    def start(
        cls,
        specs: Sequence[MarkerSpec],
        *,
        mirror: bool = False,
        send_frames: bool = False,
        target: Callable[..., None] = run_markers_process,
    ) -> VisionFeed:
        """Lance le processus vision (la caméra s'ouvre dedans, en une à deux secondes).

        ``target`` remplace la boucle caméra par une autre de même signature
        (``target(queue, specs, mirror=..., send_frames=...)``, définie au niveau du
        module) : sert à vérifier l'application sans ouvrir de vraie caméra.
        """
        sample_queue: mp.Queue = mp.Queue(maxsize=QUEUE_SIZE)
        process = mp.Process(
            target=target,
            args=(sample_queue, list(specs)),
            kwargs={"mirror": mirror, "send_frames": send_frames},
            daemon=True,
        )
        process.start()
        return cls(sample_queue, process)

    def poll(self) -> list[VisionSample]:
        """Tous les échantillons arrivés depuis le dernier appel. Ne bloque jamais."""
        samples = []
        try:
            while True:
                samples.append(self._queue.get_nowait())
        except queue_module.Empty:
            pass
        if samples:
            self.latest = samples[-1]
        return samples

    def is_alive(self) -> bool:
        """Faux si le processus s'est arrêté : caméra introuvable, occupée ou débranchée."""
        return bool(self._process.is_alive())

    def close(self) -> None:
        """Arrête le processus vision et libère la caméra."""
        self._process.terminate()
        self._process.join(timeout=JOIN_TIMEOUT_S)
