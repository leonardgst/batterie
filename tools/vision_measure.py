"""Séance de mesure vision : 50 coups à 80 BPM, coups détectés et latences (phase 03).

Un métronome donne 4 clics de décompte puis 50 clics : un coup par clic. Deux séances,
à lancer depuis le menu :

- **caméra** (touche V) : ouvre ta webcam (processus séparé, cadrage §4.1) et compte
  les coups détectés, les faux coups, les images/s réelles et le temps de traitement ;
- **clavier** (touche K) : même exercice à la barre d'espace, sans caméra. Sert de
  référence : la différence d'écart au clic entre les deux séances donne le retard de
  la caméra par rapport au clavier, sans aucun matériel de mesure.

Aucun son n'est joué sur tes coups, exprès : tu te calerais dessus et le retard
deviendrait invisible dans la mesure. Le décompte (clics aigus) et le métronome (clics
graves) sont audibles : une séance se joue sans regarder l'écran (ordinateur au sol,
pour la cible ``foot``) ; le résultat s'affiche à la fin et dans le terminal. La
calibration (couleur du marqueur, plan de frappe, seuils) est celle du préréglage de la
cible dans ``tools/vision_debug.py`` : règle-la là-bas d'abord. Le protocole complet est
dans ``docs/phases/phase-03-vision-poc.md``. Aucune image n'est enregistrée (cadrage R9).

Usage : ``uv run python tools/vision_measure.py`` (baguette, par défaut)
        ``uv run python tools/vision_measure.py --target foot`` (pied)
Sans caméra, pour voir le déroulé avec un marqueur fictif :
``uv run python tools/vision_measure.py --simulate``
"""

from __future__ import annotations

import argparse
import math
import multiprocessing as mp
import queue as queue_module
import sys
import time
from collections.abc import Iterator
from enum import Enum, auto
from typing import Any

import cv2
import numpy as np
import pygame

from batterie.audio.engine import init_mixer
from batterie.core.events import Source
from batterie.input.vision.color_tracker import ColorRange
from batterie.input.vision.measure import (
    SessionPlan,
    SessionRecorder,
    SessionResult,
    format_report,
)
from batterie.input.vision.process import WORKING_WIDTH, VisionSample, run_vision_process
from vision_debug import STICK, TARGETS, TargetPreset, add_target_argument

PLAN = SessionPlan(bpm=80.0, hit_count=50, count_in_beats=4)
LEAD_IN_S = 1.0  # délai entre Entrée et le premier clic de décompte

WINDOW_SIZE = (1000, 620)
PREVIEW_ORIGIN = (20, 20)
TEXT_X = 370
TARGET_FPS = 60
INPUT_POLL_HZ = 500

CLICK_DURATION_S = 0.03
COUNT_IN_CLICK_HZ = 1760.0
BEAT_CLICK_HZ = 880.0
BEAT_LAMP_S = 0.12

SIMULATED_FRAME_SIZE = (640, 480)
SIMULATED_FPS = 30
SIMULATED_MARKER_HALF_SIZE = 20

BACKGROUND_COLOR = (18, 18, 22)
TEXT_COLOR = (230, 230, 235)
DIM_TEXT_COLOR = (150, 150, 160)
ERROR_COLOR = (240, 120, 110)
PLANE_COLOR = (230, 90, 90)
POINT_COLOR = (255, 205, 90)
HIT_COLOR = (120, 220, 140)
LAMP_OFF_COLOR = (55, 58, 70)

NS_PER_SECOND = 1_000_000_000


class Phase(Enum):
    MENU = auto()
    CAMERA_WAIT = auto()
    READY = auto()
    RUNNING = auto()
    RESULT = auto()


def _frame_to_surface(frame_bgr: np.ndarray) -> pygame.Surface:
    """Convertit une image OpenCV (BGR, hauteur×largeur) en surface pygame."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return pygame.surfarray.make_surface(rgb.swapaxes(0, 1))


def _make_click(frequency_hz: float) -> pygame.mixer.Sound:
    """Clic bref synthétisé (sinus amorti), au format du mixeur ouvert."""
    mixer_frequency, _format, channels = pygame.mixer.get_init()
    t = np.arange(int(mixer_frequency * CLICK_DURATION_S)) / mixer_frequency
    wave = np.sin(2 * np.pi * frequency_hz * t) * np.exp(-t * 120)
    samples = (wave * 0.6 * 32767).astype(np.int16)
    if channels > 1:
        samples = np.repeat(samples[:, np.newaxis], channels, axis=1)
    return pygame.sndarray.make_sound(np.ascontiguousarray(samples))


def _simulated_frames(
    color_range: ColorRange, strike_plane_y: float, beat_interval_s: float
) -> Iterator[np.ndarray]:
    """Embout fictif (mode ``--simulate``) : un carré de la couleur calibrée qui
    franchit le plan de frappe vers le bas à chaque multiple de ``beat_interval_s``
    de l'horloge, filmé à ``SIMULATED_FPS``."""
    width, height = SIMULATED_FRAME_SIZE
    half = SIMULATED_MARKER_HALF_SIZE
    middle_hsv = [
        (low + high) // 2 for low, high in zip(color_range.lower, color_range.upper, strict=True)
    ]
    marker_bgr = cv2.cvtColor(np.uint8([[middle_hsv]]), cv2.COLOR_HSV2BGR)[0][0]
    plane_y = strike_plane_y * width / WORKING_WIDTH
    amplitude = max(10.0, min(120.0, plane_y - half - 5, height - half - 5 - plane_y))
    while True:
        phase = (time.perf_counter() % beat_interval_s) / beat_interval_s
        y = int(plane_y + amplitude * math.sin(2 * math.pi * phase))
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[max(0, y - half) : y + half, width // 2 - half : width // 2 + half] = marker_bgr
        yield frame
        time.sleep(1 / SIMULATED_FPS)


def _run_simulated_vision(
    sample_queue: Any,
    color_range: ColorRange,
    strike_plane_y: float,
    element_id: str,
    beat_interval_s: float,
    min_speed_px_per_s: float,
    refractory_s: float,
) -> None:
    """Point d'entrée du processus vision en mode ``--simulate`` (aucune caméra ouverte)."""
    run_vision_process(
        sample_queue,
        color_range,
        strike_plane_y,
        element_id=element_id,
        min_speed_px_per_s=min_speed_px_per_s,
        refractory_s=refractory_s,
        send_frames=True,
        frames=_simulated_frames(color_range, strike_plane_y, beat_interval_s),
    )


class MeasureApp:
    """État de l'outil : menu, séance en cours, résultats. Appelée à chaque tour de boucle."""

    def __init__(self, target: TargetPreset = STICK, *, simulate: bool = False) -> None:
        self.target = target
        self.simulate = simulate
        self.phase = Phase.MENU
        self.source = Source.VISION
        self.results: dict[Source, SessionResult] = {}
        self.message = ""

        self._recorder: SessionRecorder | None = None
        self._next_click = 0
        self._last_click_ns: int | None = None

        self._queue: mp.Queue | None = None
        self._process: mp.Process | None = None
        self._latest: VisionSample | None = None
        self._last_hit_ns: int | None = None

        self._count_in_click = _make_click(COUNT_IN_CLICK_HZ)
        self._beat_click = _make_click(BEAT_CLICK_HZ)
        self._font = pygame.font.SysFont("consolas", 18)
        self._small_font = pygame.font.SysFont("consolas", 16)
        self._title_font = pygame.font.SysFont("consolas", 22, bold=True)
        self._big_font = pygame.font.SysFont("consolas", 44, bold=True)

    # --- Processus caméra -------------------------------------------------

    def _start_camera(self) -> None:
        self._queue = mp.Queue(maxsize=64)
        preset = self.target
        if self.simulate:
            entry_point = _run_simulated_vision
            args: tuple = (
                self._queue,
                preset.color_range,
                preset.strike_plane_y,
                preset.element_id,
                PLAN.beat_interval_s,
                preset.min_speed_px_per_s,
                preset.refractory_s,
            )
            kwargs: dict = {}
        else:
            entry_point = run_vision_process
            args = (self._queue, preset.color_range, preset.strike_plane_y)
            kwargs = {
                "element_id": preset.element_id,
                "min_speed_px_per_s": preset.min_speed_px_per_s,
                "refractory_s": preset.refractory_s,
                "send_frames": True,
            }
        self._process = mp.Process(target=entry_point, args=args, kwargs=kwargs, daemon=True)
        self._process.start()

    def _stop_camera(self) -> None:
        if self._process is not None:
            self._process.terminate()
            self._process.join(timeout=2)
        self._process = None
        self._queue = None
        self._latest = None

    def _drain_camera(self) -> None:
        """Lit tous les échantillons en attente ; les enregistre si une séance caméra tourne."""
        if self._queue is None:
            return
        recording = self.phase is Phase.RUNNING and self.source is Source.VISION
        try:
            while True:
                sample: VisionSample = self._queue.get_nowait()
                self._latest = sample
                if sample.hit_event is not None:
                    self._last_hit_ns = sample.hit_event.t_ns
                if recording and self._recorder is not None:
                    self._recorder.add_frame(
                        sample.t_ns / NS_PER_SECOND, sample.processing_ms, sample.point is not None
                    )
                    if sample.hit_event is not None:
                        self._recorder.add_hit(sample.hit_event.t_ns / NS_PER_SECOND)
        except queue_module.Empty:
            pass

    def _camera_lost(self) -> bool:
        return self._process is not None and not self._process.is_alive()

    # --- Déroulé ----------------------------------------------------------

    def handle_events(self, events: list[pygame.event.Event], now_ns: int) -> bool:
        """Traite les événements du tour de boucle. Renvoie ``False`` pour quitter."""
        for event in events:
            if event.type == pygame.QUIT:
                return False
            if event.type != pygame.KEYDOWN or getattr(event, "repeat", False):
                continue

            if self.phase is Phase.MENU:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_v:
                    self.source = Source.VISION
                    self.message = ""
                    if self._process is None:
                        self._start_camera()
                    self.phase = Phase.CAMERA_WAIT
                elif event.key == pygame.K_k:
                    self.source = Source.KEYBOARD
                    self.message = ""
                    self.phase = Phase.READY

            elif self.phase in (Phase.CAMERA_WAIT, Phase.READY):
                if event.key == pygame.K_ESCAPE:
                    self.phase = Phase.MENU
                elif event.key == pygame.K_RETURN and self.phase is Phase.READY:
                    self._start_session(now_ns)

            elif self.phase is Phase.RUNNING:
                if event.key == pygame.K_ESCAPE:
                    self._recorder = None
                    self.phase = Phase.MENU
                elif (
                    event.scancode == pygame.KSCAN_SPACE
                    and self.source is Source.KEYBOARD
                    and self._recorder is not None
                ):
                    self._recorder.add_hit(now_ns / NS_PER_SECOND)
                    self._last_hit_ns = now_ns

            elif self.phase is Phase.RESULT:
                if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    self.phase = Phase.MENU
        return True

    def _start_session(self, now_ns: int) -> None:
        first_beat_s = (
            now_ns / NS_PER_SECOND + LEAD_IN_S + PLAN.count_in_beats * PLAN.beat_interval_s
        )
        if self.simulate and self.source is Source.VISION:
            # L'embout fictif frappe sur les multiples de l'intervalle : on cale les clics dessus.
            first_beat_s = math.ceil(first_beat_s / PLAN.beat_interval_s) * PLAN.beat_interval_s
        self._recorder = SessionRecorder(plan=PLAN, source=self.source, first_beat_s=first_beat_s)
        self._next_click = -PLAN.count_in_beats
        self._last_click_ns = None
        self._last_hit_ns = None
        self.phase = Phase.RUNNING

    def update(self, now_ns: int) -> None:
        """Avance d'un tour de boucle : caméra, clics de métronome, fin de séance."""
        self._drain_camera()

        if self.phase is Phase.CAMERA_WAIT and self._latest is not None:
            self.phase = Phase.READY

        uses_camera = self.source is Source.VISION and self.phase in (
            Phase.CAMERA_WAIT,
            Phase.READY,
            Phase.RUNNING,
        )
        if uses_camera and self._camera_lost():
            self._stop_camera()
            self._recorder = None
            self.message = (
                "Caméra introuvable ou déconnectée. Ferme les autres applications "
                "qui l'utilisent, puis réessaie."
            )
            self.phase = Phase.MENU
            return

        if self.phase is not Phase.RUNNING or self._recorder is None:
            return

        now_s = now_ns / NS_PER_SECOND
        while (
            self._next_click < PLAN.hit_count
            and now_s >= self._recorder.first_beat_s + PLAN.beat_time_s(self._next_click)
        ):
            (self._count_in_click if self._next_click < 0 else self._beat_click).play()
            self._last_click_ns = now_ns
            self._next_click += 1

        if self._recorder.is_over(now_s):
            self.results[self.source] = self._recorder.result()
            self._recorder = None
            self.phase = Phase.RESULT
            print("\n".join(["", *self.summary_lines()]), flush=True)

    def summary_lines(self) -> list[str]:
        """Résultats des séances terminées (caméra comparée au clavier s'il a été fait)."""
        lines: list[str] = []
        if self.results:
            lines.append(f"Cible : {self.target.label} ({self.target.element_id})")
            lines.append("")
        for source in (Source.VISION, Source.KEYBOARD):
            result = self.results.get(source)
            if result is None:
                continue
            reference = self.results.get(Source.KEYBOARD) if source is Source.VISION else None
            if lines:
                lines.append("")
            lines.extend(format_report(result, reference=reference))
        return lines

    def close(self) -> None:
        self._stop_camera()

    # --- Dessin -----------------------------------------------------------

    def _draw_lines(
        self,
        screen: pygame.Surface,
        lines: list[str],
        origin: tuple[int, int],
        *,
        font: pygame.font.Font | None = None,
        color: tuple[int, int, int] = TEXT_COLOR,
    ) -> int:
        """Écrit ``lines`` l'une sous l'autre ; renvoie l'ordonnée sous la dernière."""
        font = font or self._font
        x, y = origin
        for line in lines:
            screen.blit(font.render(line, True, color), (x, y))
            y += font.get_linesize() + 4
        return y

    def _draw_preview(self, screen: pygame.Surface, now_ns: int) -> None:
        if self._latest is None or self._latest.frame_preview is None:
            return
        surface = _frame_to_surface(self._latest.frame_preview)
        screen.blit(surface, PREVIEW_ORIGIN)
        plane_y = PREVIEW_ORIGIN[1] + int(self.target.strike_plane_y)
        plane_end_x = PREVIEW_ORIGIN[0] + surface.get_width()
        pygame.draw.line(screen, PLANE_COLOR, (PREVIEW_ORIGIN[0], plane_y), (plane_end_x, plane_y))
        if self._latest.point is not None:
            center = (
                PREVIEW_ORIGIN[0] + int(self._latest.point.x),
                PREVIEW_ORIGIN[1] + int(self._latest.point.y),
            )
            pygame.draw.circle(screen, self._lamp_color(now_ns, POINT_COLOR), center, 8, width=2)

    def _lamp_color(self, now_ns: int, idle: tuple[int, int, int]) -> tuple[int, int, int]:
        """Vert pendant un court instant après un coup détecté, ``idle`` sinon."""
        if self._last_hit_ns is None:
            return idle
        lit = (now_ns - self._last_hit_ns) / NS_PER_SECOND < BEAT_LAMP_S
        return HIT_COLOR if lit else idle

    def _progress_text(self) -> str:
        last_click = self._next_click - 1
        if last_click < -PLAN.count_in_beats:
            return "Prépare-toi…"
        if last_click < 0:
            return f"Décompte : {last_click + PLAN.count_in_beats + 1}"
        return f"Coup {last_click + 1} / {PLAN.hit_count}"

    def draw(self, screen: pygame.Surface, now_ns: int) -> None:
        screen.fill(BACKGROUND_COLOR)
        uses_camera = self.source is Source.VISION and self.phase in (Phase.READY, Phase.RUNNING)
        if uses_camera:
            self._draw_preview(screen, now_ns)

        title = f"Mesure {self.target.label} — {PLAN.hit_count} coups à {PLAN.bpm:.0f} BPM"
        if self.simulate:
            title += " (simulation)"
        text_x = TEXT_X if uses_camera else PREVIEW_ORIGIN[0]
        screen.blit(self._title_font.render(title, True, TEXT_COLOR), (text_x, 20))
        top = (text_x, 64)

        if self.phase is Phase.MENU:
            y = self._draw_lines(
                screen,
                [
                    f"V : séance caméra ({self.target.label} filmé par la webcam)",
                    "K : séance clavier de référence (barre d'espace, sans caméra)",
                    "Échap : quitter",
                ],
                top,
            )
            if self.message:
                y = self._draw_lines(screen, [self.message], (text_x, y + 12), color=ERROR_COLOR)
            self._draw_lines(screen, self.summary_lines(), (text_x, y + 24), font=self._small_font)

        elif self.phase is Phase.CAMERA_WAIT:
            self._draw_lines(
                screen, ["Ouverture de la caméra…", "", "Échap : retour"], top, color=DIM_TEXT_COLOR
            )

        elif self.phase is Phase.READY:
            if self.source is Source.VISION:
                tracked = self._latest is not None and self._latest.point is not None
                lines = [
                    "Place-toi comme pour jouer. La ligne rouge est le plan",
                    "de frappe : le marqueur doit la traverser à chaque coup.",
                    f"Marqueur : {'suivi (cercle jaune)' if tracked else 'non détecté'}",
                ]
            else:
                lines = ["Tape la barre d'espace sur chaque clic, d'un doigt."]
            lines += [
                "",
                f"Entrée : démarrer ({PLAN.count_in_beats} clics aigus de décompte,",
                f"puis un coup sur chacun des {PLAN.hit_count} clics graves)",
                "Échap : retour",
            ]
            self._draw_lines(screen, lines, top)

        elif self.phase is Phase.RUNNING and self._recorder is not None:
            screen.blit(self._big_font.render(self._progress_text(), True, TEXT_COLOR), top)
            clicked = (
                self._last_click_ns is not None
                and (now_ns - self._last_click_ns) / NS_PER_SECOND < BEAT_LAMP_S
            )
            lamp_center = (text_x + 30, top[1] + 110)
            pygame.draw.circle(screen, TEXT_COLOR if clicked else LAMP_OFF_COLOR, lamp_center, 26)
            hit_lamp_center = (text_x + 110, top[1] + 110)
            pygame.draw.circle(
                screen, self._lamp_color(now_ns, LAMP_OFF_COLOR), hit_lamp_center, 26
            )
            self._draw_lines(
                screen,
                [
                    "clic    coup",
                    "",
                    f"Détections : {self._recorder.hit_count}",
                    "Échap : abandonner la séance",
                ],
                (text_x, top[1] + 150),
            )

        elif self.phase is Phase.RESULT:
            y = self._draw_lines(screen, ["Séance terminée. Entrée : retour au menu"], top)
            self._draw_lines(screen, self.summary_lines(), (text_x, y + 24), font=self._small_font)


def run(target: TargetPreset = STICK, *, simulate: bool = False) -> None:
    init_mixer()
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption(f"Batterie — mesure vision ({target.label})")

    app = MeasureApp(target, simulate=simulate)
    poll_clock = pygame.time.Clock()
    render_interval_s = 1.0 / TARGET_FPS
    next_render = time.perf_counter()

    running = True
    try:
        while running:
            events = pygame.event.get()
            now_ns = time.perf_counter_ns()
            running = app.handle_events(events, now_ns)
            app.update(now_ns)

            now = time.perf_counter()
            if now >= next_render:
                app.draw(screen, now_ns)
                pygame.display.flip()
                next_render = now + render_interval_s

            poll_clock.tick(INPUT_POLL_HZ)
    finally:
        app.close()
        pygame.quit()


def parse_arguments(argv: list[str] | None = None) -> tuple[TargetPreset, bool]:
    """Lit la ligne de commande : renvoie le préréglage de la cible et le mode simulation."""
    parser = argparse.ArgumentParser(description="Séance de mesure vision (phase 03).")
    add_target_argument(parser)
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="marqueur fictif à la place de la webcam (pour voir le déroulé sans caméra)",
    )
    arguments = parser.parse_args(argv)
    return TARGETS[arguments.target], arguments.simulate


def main(argv: list[str] | None = None) -> int:
    # Les résultats contiennent « ≥ » et « − » : sortie en UTF-8 même redirigée vers un fichier.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    target, simulate = parse_arguments(argv)
    run(target, simulate=simulate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
