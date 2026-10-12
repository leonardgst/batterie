"""Faux flux caméra partagés par les tests de l'écran de calibration et du jeu caméra."""

import queue as queue_module


class FakeQueue:
    def __init__(self) -> None:
        self.items: list = []

    def get_nowait(self):
        if not self.items:
            raise queue_module.Empty
        return self.items.pop(0)


class FakeProcess:
    def __init__(self) -> None:
        self.alive = True
        self.terminated = False
        self.joined_with: float | None = None

    def is_alive(self) -> bool:
        return self.alive

    def terminate(self) -> None:
        self.terminated = True
        self.alive = False

    def join(self, timeout: float | None = None) -> None:
        self.joined_with = timeout
