"""Écran de débogage vision : aperçu caméra, points suivis, vitesse, latence (phase 03-04).

Ouvre ta webcam (processus séparé, cadrage §4.1). Calibration : modifie le préréglage
de la cible (``STICK``, ``FOOT`` ou ``HANDS``, juste en dessous) selon ta caméra, tes
marqueurs et ta lumière, puis relance. La ligne du plan de frappe et les points suivis
sont dessinés dans le même repère de pixels que la détection (image réduite à
``WORKING_WIDTH``, voir ``input/vision/process.py``), donc ce que tu vois correspond
exactement à ce qui est détecté.

Usage : ``uv run python tools/vision_debug.py`` (baguette, par défaut)
        ``uv run python tools/vision_debug.py --target foot`` (pied, test de la phase 03)
        ``uv run python tools/vision_debug.py --target hands`` (deux mains, phase 04)
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import queue as queue_module
from dataclasses import dataclass

import cv2
import numpy as np
import pygame

from batterie.input.vision.color_tracker import GREEN, ORANGE, ColorRange
from batterie.input.vision.process import MarkerSpec, VisionSample, run_markers_process
from batterie.input.vision.strike_detector import DEFAULT_MIN_SPEED_PX_PER_S, DEFAULT_REFRACTORY_S

POINT_COLOR = (255, 205, 90)
ORANGE_DISPLAY_COLOR = (255, 150, 40)
GREEN_DISPLAY_COLOR = (90, 220, 120)


@dataclass(frozen=True)
class MarkerPreset:
    """Réglages d'un embout suivi : tout ce qui change entre une baguette et un pied."""

    name: str  # identifiant interne (« stick », « left », ...)
    label: str  # nom affiché à l'écran
    element_id: str
    color_range: ColorRange
    strike_plane_y: float  # pixels, dans l'image réduite (voir WORKING_WIDTH)
    min_speed_px_per_s: float
    refractory_s: float
    display_color: tuple[int, int, int] = POINT_COLOR  # cercle dessiné sur l'aperçu

    def to_spec(self) -> MarkerSpec:
        return MarkerSpec(
            name=self.name,
            color_range=self.color_range,
            strike_plane_y=self.strike_plane_y,
            element_id=self.element_id,
            min_speed_px_per_s=self.min_speed_px_per_s,
            refractory_s=self.refractory_s,
        )


@dataclass(frozen=True)
class TargetPreset:
    """Ce qu'on suit : un ou plusieurs embouts, et si l'image est retournée en miroir."""

    label: str
    markers: tuple[MarkerPreset, ...]
    mirror: bool = False  # vrai pour les mains : ta gauche apparaît à gauche, comme sur le kit

    def specs(self) -> list[MarkerSpec]:
        return [marker.to_spec() for marker in self.markers]

    def describe(self) -> str:
        """Texte de rappel (résultats de mesure) : la cible, et l'élément si elle est unique."""
        if len(self.markers) == 1:
            return f"{self.label} ({self.markers[0].element_id})"
        return self.label


# --- À calibrer pour ta caméra, tes marqueurs, ta lumière --------------------

# Une seule couleur pour les cibles à un embout : pendant le test du pied, un seul
# marqueur est dans l'image à la fois (déplace-le de la baguette à la chaussure).
MARKER_COLOR: ColorRange = GREEN

# Baguette : les valeurs par défaut du détecteur, qui ont suffi pour ta baguette à la
# clôture de la phase 03 (voir l'ADR 0002).
STICK = TargetPreset(
    label="baguette",
    markers=(
        MarkerPreset(
            name="stick",
            label="baguette",
            element_id="snare",
            color_range=MARKER_COLOR,
            strike_plane_y=150.0,
            min_speed_px_per_s=DEFAULT_MIN_SPEED_PX_PER_S,
            refractory_s=DEFAULT_REFRACTORY_S,
        ),
    ),
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
    markers=(
        MarkerPreset(
            name="foot",
            label="pied",
            element_id="kick",
            color_range=MARKER_COLOR,
            strike_plane_y=100.0,
            min_speed_px_per_s=80.0,
            refractory_s=0.20,
        ),
    ),
)

# Deux mains (phase 04) — NON CALIBRÉ : main gauche = embout orange, main droite = embout
# vert. Mêmes seuils et même plan de frappe que la baguette, qui ont suffi en phase 03 ;
# les deux mains portent ici le même élément (« snare ») : attribuer chaque coup au bon
# élément selon sa position est le travail des zones (PR 2 de la phase 04). L'image est
# retournée en miroir (ta main gauche apparaît à gauche). La plage ORANGE est à régler
# sur ton embout et ta lumière : un orange pâle n'est volontairement pas suivi (il
# ressemblerait à ta peau) ; si le cercle s'accroche à ta main ou à ton visage, resserre
# la saturation minimale dans ``ORANGE`` (color_tracker.py).
HANDS = TargetPreset(
    label="deux mains",
    mirror=True,
    markers=(
        MarkerPreset(
            name="left",
            label="Main gauche (orange)",
            element_id="snare",
            color_range=ORANGE,
            strike_plane_y=150.0,
            min_speed_px_per_s=DEFAULT_MIN_SPEED_PX_PER_S,
            refractory_s=DEFAULT_REFRACTORY_S,
            display_color=ORANGE_DISPLAY_COLOR,
        ),
        MarkerPreset(
            name="right",
            label="Main droite (verte)",
            element_id="snare",
            color_range=GREEN,
            strike_plane_y=150.0,
            min_speed_px_per_s=DEFAULT_MIN_SPEED_PX_PER_S,
            refractory_s=DEFAULT_REFRACTORY_S,
            display_color=GREEN_DISPLAY_COLOR,
        ),
    ),
)

# -----------------------------------------------------------------------------

TARGETS: dict[str, TargetPreset] = {"stick": STICK, "foot": FOOT, "hands": HANDS}
DEFAULT_TARGET = "stick"

WINDOW_SIZE = (900, 560)
PREVIEW_ORIGIN = (20, 20)
SIDEBAR_X = 360
TARGET_FPS = 60

BACKGROUND_COLOR = (18, 18, 22)
TEXT_COLOR = (230, 230, 235)
PLANE_COLOR = (230, 90, 90)
HIT_COLOR = (255, 255, 255)
NO_SIGNAL_COLOR = (90, 90, 100)


def add_target_argument(parser: argparse.ArgumentParser) -> None:
    """Ajoute ``--target stick|foot|hands`` (partagé avec ``vision_measure.py``)."""
    parser.add_argument(
        "--target",
        choices=list(TARGETS),
        default=DEFAULT_TARGET,
        help=(
            "ce qu'on suit : stick = baguette (défaut), foot = pointe du pied (grosse caisse), "
            "hands = deux mains (orange à gauche, vert à droite)"
        ),
    )


def parse_arguments(argv: list[str] | None = None) -> TargetPreset:
    """Lit la ligne de commande et renvoie le préréglage de la cible choisie."""
    parser = argparse.ArgumentParser(description="Écran de débogage vision (phase 03-04).")
    add_target_argument(parser)
    return TARGETS[parser.parse_args(argv).target]


def _frame_to_surface(frame_bgr: np.ndarray) -> pygame.Surface:
    """Convertit une image OpenCV (BGR, hauteur×largeur) en surface pygame."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return pygame.surfarray.make_surface(rgb.swapaxes(0, 1))


def _format_point(sample: VisionSample | None, name: str) -> str:
    marker = sample.markers.get(name) if sample is not None else None
    if marker is None or marker.point is None:
        return "non détecté"
    point = marker.point
    return f"({point.x:.0f}, {point.y:.0f})  aire {point.area:.0f} px²"


def sidebar_lines(
    target: TargetPreset, latest: VisionSample | None, hit_counts: dict[str, int]
) -> list[str]:
    """Texte de la colonne de droite : compteurs, positions, vitesses, images/s, latence."""
    lines = [f"Cible : {target.describe()}", f"Coups détectés : {sum(hit_counts.values())}", ""]
    single = len(target.markers) == 1
    for marker in target.markers:
        sample = latest.markers.get(marker.name) if latest is not None else None
        if not single:
            lines.append(f"{marker.label} : {hit_counts[marker.name]} coups")
        prefix = "" if single else "  "
        lines.append(f"{prefix}Position : {_format_point(latest, marker.name)}")
        speed = f"{sample.velocity_px_per_s:.0f} px/s" if sample else "—"
        lines.append(f"{prefix}Vitesse : {speed}")
        if not single:
            lines.append("")
    lines.append(f"Images/s : {latest.fps:.0f}" if latest else "Images/s : —")
    lines.append(
        f"Latence de traitement : {latest.processing_ms:.1f} ms"
        if latest
        else "Latence de traitement : —"
    )
    lines += [
        "",
        "Échap pour quitter.",
        "Calibration : édite le préréglage de la cible",
        "en haut de tools/vision_debug.py, puis relance.",
    ]
    return lines


def run(target: TargetPreset = STICK) -> None:
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption(f"Batterie — débogage vision ({target.label})")
    font = pygame.font.SysFont("consolas", 20)
    title_font = pygame.font.SysFont("consolas", 22, bold=True)

    sample_queue: mp.Queue = mp.Queue(maxsize=4)
    process = mp.Process(
        target=run_markers_process,
        args=(sample_queue, target.specs()),
        kwargs={"mirror": target.mirror, "send_frames": True},
        daemon=True,
    )
    process.start()

    latest: VisionSample | None = None
    hit_counts = {marker.name: 0 for marker in target.markers}
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
                    for name, marker_sample in latest.markers.items():
                        if marker_sample.hit_event is not None:
                            hit_counts[name] += 1
            except queue_module.Empty:
                pass

            screen.fill(BACKGROUND_COLOR)

            if latest is not None and latest.frame_preview is not None:
                surface = _frame_to_surface(latest.frame_preview)
                screen.blit(surface, PREVIEW_ORIGIN)
                for marker in target.markers:
                    plane_y = PREVIEW_ORIGIN[1] + int(marker.strike_plane_y)
                    plane_start = (PREVIEW_ORIGIN[0], plane_y)
                    plane_end = (PREVIEW_ORIGIN[0] + surface.get_width(), plane_y)
                    pygame.draw.line(screen, PLANE_COLOR, plane_start, plane_end, 2)
                for marker in target.markers:
                    marker_sample = latest.markers[marker.name]
                    if marker_sample.point is not None:
                        center = (
                            PREVIEW_ORIGIN[0] + int(marker_sample.point.x),
                            PREVIEW_ORIGIN[1] + int(marker_sample.point.y),
                        )
                        hit = marker_sample.hit_event is not None
                        color = HIT_COLOR if hit else marker.display_color
                        pygame.draw.circle(screen, color, center, 10 if hit else 8, width=3)
            else:
                waiting = title_font.render("En attente de la caméra...", True, NO_SIGNAL_COLOR)
                screen.blit(waiting, (PREVIEW_ORIGIN[0], PREVIEW_ORIGIN[1] + 100))

            for i, line in enumerate(sidebar_lines(target, latest, hit_counts)):
                text_surface = font.render(line, True, TEXT_COLOR)
                screen.blit(text_surface, (SIDEBAR_X, 20 + i * 26))

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
