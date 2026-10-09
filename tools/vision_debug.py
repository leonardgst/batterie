"""Écran de débogage vision : aperçu caméra, point suivi, vitesse, latence (phase 03).

Ouvre ta webcam (processus séparé, cadrage §4.1). Calibration : modifie
``COLOR_RANGE`` et ``STRIKE_PLANE_Y`` ci-dessous selon ta caméra, ton embout et ta
lumière, puis relance. La ligne du plan de frappe et le point suivi sont dessinés
dans le même repère de pixels que la détection (image réduite à ``WORKING_WIDTH``,
voir ``input/vision/process.py``), donc ce que tu vois correspond exactement à ce
qui est détecté.

Usage : ``uv run python tools/vision_debug.py``
"""

from __future__ import annotations

import multiprocessing as mp
import queue as queue_module

import cv2
import numpy as np
import pygame

from batterie.input.vision.color_tracker import GREEN, ColorRange
from batterie.input.vision.process import VisionSample, run_vision_process

# --- À calibrer pour ta caméra, ton embout, ta lumière ----------------------
COLOR_RANGE: ColorRange = GREEN
STRIKE_PLANE_Y = 150.0  # pixels, dans l'image réduite (voir WORKING_WIDTH)
ELEMENT_ID = "snare"
# -----------------------------------------------------------------------

WINDOW_SIZE = (900, 560)
PREVIEW_ORIGIN = (20, 20)
SIDEBAR_X = 360
TARGET_FPS = 60

BACKGROUND_COLOR = (18, 18, 22)
TEXT_COLOR = (230, 230, 235)
PLANE_COLOR = (230, 90, 90)
POINT_COLOR = (255, 205, 90)
HIT_COLOR = (120, 220, 140)
NO_SIGNAL_COLOR = (90, 90, 100)


def _frame_to_surface(frame_bgr: np.ndarray) -> pygame.Surface:
    """Convertit une image OpenCV (BGR, hauteur×largeur) en surface pygame."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return pygame.surfarray.make_surface(rgb.swapaxes(0, 1))


def _format_point(sample: VisionSample | None) -> str:
    if sample is None or sample.point is None:
        return "non détectée"
    return f"({sample.point.x:.0f}, {sample.point.y:.0f})  aire {sample.point.area:.0f} px²"


def run() -> None:
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("Batterie — débogage vision")
    font = pygame.font.SysFont("consolas", 20)
    title_font = pygame.font.SysFont("consolas", 22, bold=True)

    sample_queue: mp.Queue = mp.Queue(maxsize=4)
    process = mp.Process(
        target=run_vision_process,
        args=(sample_queue, COLOR_RANGE, STRIKE_PLANE_Y),
        kwargs={"element_id": ELEMENT_ID, "send_frames": True},
        daemon=True,
    )
    process.start()

    latest: VisionSample | None = None
    hit_count = 0
    clock = pygame.time.Clock()

    running = True
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

            try:
                while True:
                    latest = sample_queue.get_nowait()
                    if latest.hit_event is not None:
                        hit_count += 1
            except queue_module.Empty:
                pass

            screen.fill(BACKGROUND_COLOR)

            if latest is not None and latest.frame_preview is not None:
                surface = _frame_to_surface(latest.frame_preview)
                screen.blit(surface, PREVIEW_ORIGIN)
                plane_y = PREVIEW_ORIGIN[1] + int(STRIKE_PLANE_Y)
                plane_start = (PREVIEW_ORIGIN[0], plane_y)
                plane_end = (PREVIEW_ORIGIN[0] + surface.get_width(), plane_y)
                pygame.draw.line(screen, PLANE_COLOR, plane_start, plane_end, 2)
                if latest.point is not None:
                    px = PREVIEW_ORIGIN[0] + int(latest.point.x)
                    py = PREVIEW_ORIGIN[1] + int(latest.point.y)
                    color = HIT_COLOR if latest.hit_event is not None else POINT_COLOR
                    pygame.draw.circle(screen, color, (px, py), 8, width=2)
            else:
                waiting = title_font.render("En attente de la caméra...", True, NO_SIGNAL_COLOR)
                screen.blit(waiting, (PREVIEW_ORIGIN[0], PREVIEW_ORIGIN[1] + 100))

            lines = [
                f"Coups détectés : {hit_count}",
                "",
                f"Position : {_format_point(latest)}",
                f"Vitesse : {latest.velocity_px_per_s:.0f} px/s" if latest else "Vitesse : —",
                f"Images/s : {latest.fps:.0f}" if latest else "Images/s : —",
                (
                    f"Latence de traitement : {latest.processing_ms:.1f} ms"
                    if latest
                    else "Latence de traitement : —"
                ),
                "",
                "Échap pour quitter.",
                "Calibration : édite COLOR_RANGE / STRIKE_PLANE_Y en haut du fichier.",
            ]
            for i, line in enumerate(lines):
                text_surface = font.render(line, True, TEXT_COLOR)
                screen.blit(text_surface, (SIDEBAR_X, 20 + i * 28))

            pygame.display.flip()
            clock.tick(TARGET_FPS)
    finally:
        process.terminate()
        process.join(timeout=2)
        pygame.quit()


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
