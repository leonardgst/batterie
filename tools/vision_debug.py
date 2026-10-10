"""Écran de débogage vision : aperçu caméra, point suivi, vitesse, latence (phase 03).

Ouvre ta webcam (processus séparé, cadrage §4.1). Calibration : modifie le préréglage
de la cible (``STICK`` ou ``FOOT``, juste en dessous) selon ta caméra, ton marqueur et
ta lumière, puis relance. La ligne du plan de frappe et le point suivi sont dessinés
dans le même repère de pixels que la détection (image réduite à ``WORKING_WIDTH``,
voir ``input/vision/process.py``), donc ce que tu vois correspond exactement à ce
qui est détecté.

Usage : ``uv run python tools/vision_debug.py`` (baguette, par défaut)
        ``uv run python tools/vision_debug.py --target foot`` (pied, test de la phase 03)
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import queue as queue_module
from dataclasses import dataclass

import cv2
import numpy as np
import pygame

from batterie.input.vision.color_tracker import GREEN, ColorRange
from batterie.input.vision.process import VisionSample, run_vision_process
from batterie.input.vision.strike_detector import DEFAULT_MIN_SPEED_PX_PER_S, DEFAULT_REFRACTORY_S


@dataclass(frozen=True)
class TargetPreset:
    """Réglages de ce qu'on suit : tout ce qui change entre une baguette et un pied."""

    label: str  # nom affiché à l'écran
    element_id: str
    color_range: ColorRange
    strike_plane_y: float  # pixels, dans l'image réduite (voir WORKING_WIDTH)
    min_speed_px_per_s: float
    refractory_s: float


# --- À calibrer pour ta caméra, ton marqueur, ta lumière ---------------------

# Une seule couleur pour les deux cibles : pendant le test du pied, un seul marqueur
# est dans l'image à la fois (déplace-le de la baguette à la chaussure).
MARKER_COLOR: ColorRange = GREEN

# Baguette : les valeurs par défaut du détecteur, qui ont suffi pour ta baguette à la
# clôture de la phase 03 (voir l'ADR 0002).
STICK = TargetPreset(
    label="baguette",
    element_id="snare",
    color_range=MARKER_COLOR,
    strike_plane_y=150.0,
    min_speed_px_per_s=DEFAULT_MIN_SPEED_PX_PER_S,
    refractory_s=DEFAULT_REFRACTORY_S,
)

# Pied (grosse caisse) — NON CALIBRÉ : valeurs de départ estimées, pas mesurées. Un
# ordre de grandeur, pour la webcam du portable posée au sol à 50-80 cm des pieds :
# - vitesse minimale 80 px/s, contre 200 pour la baguette. La pointe du pied se lève
#   et retombe d'environ 5 à 10 cm (une baguette : 20 cm ou plus), ce qui fait quelques
#   dizaines de pixels dans l'image réduite, en un dixième de seconde environ : de
#   l'ordre de 40 % de la vitesse de la baguette. Plus bas, le tremblement du point
#   suivi pourrait déclencher des coups ; plus haut, on raterait les coups doux ;
# - anti-rebond 0,20 s, contre 0,15 : le pied va moins vite qu'une main, donc deux coups
#   à moins de 0,2 s sont plus probablement un rebond ou un tremblement de la pointe
#   près du plan qu'un vrai double coup ;
# - plan de frappe à 100 px : vers le milieu de l'image (90 px en 16:9, 120 en 4:3),
#   là où la pointe se lève et retombe. À régler en regardant l'aperçu, pas avant.
FOOT = TargetPreset(
    label="pied",
    element_id="kick",
    color_range=MARKER_COLOR,
    strike_plane_y=100.0,
    min_speed_px_per_s=80.0,
    refractory_s=0.20,
)

# -----------------------------------------------------------------------------

TARGETS: dict[str, TargetPreset] = {"stick": STICK, "foot": FOOT}
DEFAULT_TARGET = "stick"

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


def add_target_argument(parser: argparse.ArgumentParser) -> None:
    """Ajoute ``--target stick|foot`` (partagé avec ``vision_measure.py``)."""
    parser.add_argument(
        "--target",
        choices=list(TARGETS),
        default=DEFAULT_TARGET,
        help="ce qu'on suit : stick = baguette (défaut), foot = pointe du pied (grosse caisse)",
    )


def parse_arguments(argv: list[str] | None = None) -> TargetPreset:
    """Lit la ligne de commande et renvoie le préréglage de la cible choisie."""
    parser = argparse.ArgumentParser(description="Écran de débogage vision (phase 03).")
    add_target_argument(parser)
    return TARGETS[parser.parse_args(argv).target]


def _frame_to_surface(frame_bgr: np.ndarray) -> pygame.Surface:
    """Convertit une image OpenCV (BGR, hauteur×largeur) en surface pygame."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return pygame.surfarray.make_surface(rgb.swapaxes(0, 1))


def _format_point(sample: VisionSample | None) -> str:
    if sample is None or sample.point is None:
        return "non détectée"
    return f"({sample.point.x:.0f}, {sample.point.y:.0f})  aire {sample.point.area:.0f} px²"


def run(target: TargetPreset = STICK) -> None:
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption(f"Batterie — débogage vision ({target.label})")
    font = pygame.font.SysFont("consolas", 20)
    title_font = pygame.font.SysFont("consolas", 22, bold=True)

    sample_queue: mp.Queue = mp.Queue(maxsize=4)
    process = mp.Process(
        target=run_vision_process,
        args=(sample_queue, target.color_range, target.strike_plane_y),
        kwargs={
            "element_id": target.element_id,
            "min_speed_px_per_s": target.min_speed_px_per_s,
            "refractory_s": target.refractory_s,
            "send_frames": True,
        },
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
                plane_y = PREVIEW_ORIGIN[1] + int(target.strike_plane_y)
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
                f"Cible : {target.label} ({target.element_id})",
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
                "Calibration : édite le préréglage STICK / FOOT",
                "en haut de tools/vision_debug.py, puis relance.",
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


def main(argv: list[str] | None = None) -> int:
    run(parse_arguments(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
