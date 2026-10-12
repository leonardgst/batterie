"""Séance de mesure vision : coups détectés, attribution et latences (phases 03 et 04).

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

**Séance US7** (``--pattern``, phase 04) : 100 croches à 90 BPM, un motif de 8 croches répété
sur la charleston fermée, la caisse claire, le tom médium et le ride, les deux mains en
alternance (gauche sur les croches impaires du motif, droite sur les paires). Chaque clic a un
élément attendu : en plus des coups détectés et des faux coups, l'outil compte les coups
attribués au bon élément, et chiffre les quatre critères US7 à la fin. Elle utilise tes zones
calibrées (``zones.toml``) et les réglages ``[camera]`` de ``settings.toml``, comme le jeu
à la caméra. La latence geste → son demande aussi la séance clavier de référence (touche K).
Protocole dans ``docs/phases/phase-04-deux-mains.md``.

Usage : ``uv run python tools/vision_measure.py`` (baguette, par défaut)
        ``uv run python tools/vision_measure.py --target foot`` (pied)
        ``uv run python tools/vision_measure.py --pattern`` (séance US7, deux mains)
        ``uv run python tools/vision_measure.py --pattern --bpm 70`` (même séance, plus lente)
Sans caméra, pour voir le déroulé avec un marqueur fictif :
``uv run python tools/vision_measure.py --simulate`` (ou ``--pattern --simulate``)
"""

from __future__ import annotations

import argparse
import math
import multiprocessing as mp
import queue as queue_module
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

import cv2
import numpy as np
import pygame

from batterie.audio.engine import init_mixer
from batterie.config.settings import CameraSettings, load_settings
from batterie.config.zones import ZonesError, load_zones, zones_path
from batterie.core.elements import ELEMENTS_BY_ID
from batterie.core.events import Source
from batterie.input.vision.hands import hand_specs
from batterie.input.vision.measure import (
    US7_PLAN,
    SessionPlan,
    SessionRecorder,
    SessionResult,
    format_report,
    hand_for_click,
    us7_plan_at,
)
from batterie.input.vision.process import (
    WORKING_WIDTH,
    CameraInfo,
    MarkerSpec,
    VisionSample,
    run_markers_process,
)
from batterie.input.vision.zones import Zone, ZoneMap
from batterie.ui.camera_view import draw_zones
from vision_debug import HANDS, STICK, TARGETS, TargetPreset, add_target_argument

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
ACCENT_CLICK_HZ = 1320.0  # premier clic de chaque motif de la séance US7
BEAT_LAMP_S = 0.12

PATTERN_CELL = (148, 54)  # case d'un clic du motif (séance US7)
PATTERN_GAP = 6
PATTERN_COLUMNS = 4
CURRENT_CELL_COLOR = (255, 205, 90)
HAND_LABELS = {"left": "G", "right": "D"}
# Noms raccourcis pour tenir dans une case du motif (148 px de large).
SHORT_LABELS = {"hihat_closed": "Charleston"}

SIMULATED_FRAME_SIZE = (640, 480)
# Zones fictives de la séance simulée, dans l'image réduite (320 de large) : quatre éléments
# côte à côte, plan de frappe au milieu.
SIMULATED_ZONES = ZoneMap(
    tuple(
        Zone(element_id, x_min, x_max, 60.0, 110.0, 170.0)
        for element_id, (x_min, x_max) in zip(
            ("hihat_closed", "snare", "tom_mid", "ride"),
            ((20.0, 80.0), (100.0, 160.0), (180.0, 240.0), (260.0, 310.0)),
            strict=True,
        )
    )
)
SIMULATED_STROKE_AMPLITUDE = 50.0

MIN_BPM, MAX_BPM = 40.0, 200.0  # bornes de --bpm
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
    specs: Sequence[MarkerSpec], beat_interval_s: float, mirror: bool = False
) -> Iterator[np.ndarray]:
    """Embouts fictifs (mode ``--simulate``) : un carré de la couleur calibrée par embout.

    Avec un seul embout, il franchit le plan de frappe vers le bas à chaque multiple de
    ``beat_interval_s`` de l'horloge. Avec plusieurs, ils se relaient : l'embout ``k``
    frappe un clic sur ``n``, à tour de rôle, côte à côte dans l'image. Filmé à
    ``SIMULATED_FPS``. Comme une vraie caméra face à toi, l'image brute montre le premier
    embout (ta main gauche) à droite quand ``mirror`` est vrai : c'est le traitement qui
    la remet à gauche."""
    width, height = SIMULATED_FRAME_SIZE
    half = SIMULATED_MARKER_HALF_SIZE
    count = len(specs)
    colors = []
    for spec in specs:
        middle_hsv = [
            (low + high) // 2
            for low, high in zip(spec.color_range.lower, spec.color_range.upper, strict=True)
        ]
        colors.append(cv2.cvtColor(np.uint8([[middle_hsv]]), cv2.COLOR_HSV2BGR)[0][0])
    period_s = count * beat_interval_s
    while True:
        now = time.perf_counter()
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        for index, spec in enumerate(specs):
            plane_y = spec.strike_plane_y * width / WORKING_WIDTH
            amplitude = max(10.0, min(120.0, plane_y - half - 5, height - half - 5 - plane_y))
            phase = ((now - index * beat_interval_s) % period_s) / period_s
            y = int(plane_y + amplitude * math.sin(2 * math.pi * phase))
            slot = count - index if mirror else index + 1
            x = width * slot // (count + 1)
            frame[max(0, y - half) : y + half, x - half : x + half] = colors[index]
        yield frame
        time.sleep(1 / SIMULATED_FPS)


def _simulated_pattern_frames(
    specs: Sequence[MarkerSpec],
    plan: SessionPlan,
    zones: ZoneMap,
    mirror: bool = False,
    *,
    clock: Callable[[], float] = time.perf_counter,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[np.ndarray]:
    """Deux mains fictives qui jouent le motif de la séance US7 (mode ``--pattern --simulate``).

    Le clic ``k`` tombe sur les multiples de l'intervalle de l'horloge ; la main gauche
    frappe les clics pairs, la droite les impairs (``hand_for_click``), sur l'élément du
    motif. Chaque main fait un aller-retour par deux clics : elle franchit le plan de frappe
    vers le bas exactement sur son clic, puis se déplace vers l'élément de son clic suivant.
    Comme une vraie caméra, l'image brute est retournée quand ``mirror`` est vrai."""
    width, height = SIMULATED_FRAME_SIZE
    half = SIMULATED_MARKER_HALF_SIZE
    scale = width / WORKING_WIDTH
    interval = plan.beat_interval_s
    assert specs[0].name == "left" and specs[1].name == "right"
    colors = []
    for spec in specs:
        middle_hsv = [
            (low + high) // 2
            for low, high in zip(spec.color_range.lower, spec.color_range.upper, strict=True)
        ]
        colors.append(cv2.cvtColor(np.uint8([[middle_hsv]]), cv2.COLOR_HSV2BGR)[0][0])

    def center_x(click: int) -> float:
        zone = zones.get(plan.expected_element(click) or "")
        assert zone is not None
        return (zone.x_min + zone.x_max) / 2

    plane_y = next(iter(zones)).strike_plane_y
    while True:
        now = clock()
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        for hand_index, spec in enumerate(specs):
            click = math.floor(now / interval)
            if hand_for_click(click) != spec.name:
                click -= 1
            progress = (now - click * interval) / (2 * interval)  # 0 au clic, 1 au suivant
            x = center_x(click) + (center_x(click + 2) - center_x(click)) * progress
            y = plane_y + SIMULATED_STROKE_AMPLITUDE * math.sin(2 * math.pi * progress)
            raw_x = int((WORKING_WIDTH - x) * scale if mirror else x * scale)
            raw_y = int(y * scale)
            frame[max(0, raw_y - half) : raw_y + half, max(0, raw_x - half) : raw_x + half] = (
                colors[hand_index]
            )
        yield frame
        sleep(1 / SIMULATED_FPS)


def _run_simulated_pattern(
    sample_queue: Any, specs: Sequence[MarkerSpec], plan: SessionPlan, mirror: bool
) -> None:
    """Point d'entrée du processus vision en mode ``--pattern --simulate``."""
    run_markers_process(
        sample_queue,
        specs,
        mirror=mirror,
        send_frames=True,
        frames=_simulated_pattern_frames(specs, plan, SIMULATED_ZONES, mirror),
    )


def _run_simulated_vision(
    sample_queue: Any, specs: Sequence[MarkerSpec], beat_interval_s: float, mirror: bool
) -> None:
    """Point d'entrée du processus vision en mode ``--simulate`` (aucune caméra ouverte)."""
    run_markers_process(
        sample_queue,
        specs,
        mirror=mirror,
        send_frames=True,
        frames=_simulated_frames(specs, beat_interval_s, mirror),
    )


class MeasureApp:
    """État de l'outil : menu, séance en cours, résultats. Appelée à chaque tour de boucle."""

    def __init__(
        self,
        target: TargetPreset = STICK,
        *,
        simulate: bool = False,
        pattern: bool = False,
        bpm: float = US7_PLAN.bpm,
        zones: ZoneMap | None = None,
        camera: CameraSettings | None = None,
    ) -> None:
        self.target = target
        self.simulate = simulate
        self.pattern = pattern
        self.plan = us7_plan_at(bpm) if pattern else PLAN
        # Séance US7 : les coups sont attribués d'après les zones (fictives en simulation).
        self.zones = (SIMULATED_ZONES if simulate else zones) if pattern else None
        self.camera = camera
        self.camera_info: CameraInfo | None = None
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
        self._accent_click = _make_click(ACCENT_CLICK_HZ)
        self._font = pygame.font.SysFont("consolas", 18)
        self._small_font = pygame.font.SysFont("consolas", 16)
        self._title_font = pygame.font.SysFont("consolas", 22, bold=True)
        self._big_font = pygame.font.SysFont("consolas", 44, bold=True)

    # --- Processus caméra -------------------------------------------------

    def _start_camera(self) -> None:
        self._queue = mp.Queue(maxsize=64)
        if self.pattern:
            assert self.zones is not None
            specs = hand_specs(self.zones)
        else:
            specs = self.target.specs()
        kwargs: dict = {}
        if self.simulate and self.pattern:
            entry_point = _run_simulated_pattern
            args: tuple = (self._queue, specs, self.plan, self.target.mirror)
        elif self.simulate:
            entry_point = _run_simulated_vision
            args = (self._queue, specs, self.plan.beat_interval_s, self.target.mirror)
        else:
            entry_point = run_markers_process
            args = (self._queue, specs)
            kwargs = {"mirror": self.target.mirror, "send_frames": True}
            if self.pattern and self.camera is not None:
                kwargs["camera"] = self.camera
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
                if sample.camera is not None:
                    self.camera_info = sample.camera
                hit_events = sample.hit_events
                if hit_events:
                    self._last_hit_ns = hit_events[-1].t_ns
                if recording and self._recorder is not None:
                    tracked = any(m.point is not None for m in sample.markers.values())
                    self._recorder.add_frame(
                        sample.t_ns / NS_PER_SECOND, sample.processing_ms, tracked
                    )
                    for hit_event in hit_events:
                        self._recorder.add_hit(hit_event.t_ns / NS_PER_SECOND, hit_event.element_id)
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
        plan = self.plan
        first_beat_s = (
            now_ns / NS_PER_SECOND + LEAD_IN_S + plan.count_in_beats * plan.beat_interval_s
        )
        if self.simulate and self.source is Source.VISION:
            # Les embouts fictifs frappent sur les multiples de l'intervalle (et, pour le motif,
            # le motif recommence sur les multiples de sa durée) : on cale les clics dessus.
            step_s = plan.beat_interval_s * (len(plan.pattern) or 1)
            first_beat_s = math.ceil(first_beat_s / step_s) * step_s
        self._recorder = SessionRecorder(plan=plan, source=self.source, first_beat_s=first_beat_s)
        self._next_click = -plan.count_in_beats
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
        plan = self.plan
        while self._next_click < plan.hit_count and now_s >= (
            self._recorder.first_beat_s + plan.beat_time_s(self._next_click)
        ):
            self._click_for(self._next_click).play()
            self._last_click_ns = now_ns
            self._next_click += 1

        if self._recorder.is_over(now_s):
            self.results[self.source] = self._recorder.result()
            self._recorder = None
            self.phase = Phase.RESULT
            print("\n".join(["", *self.summary_lines()]), flush=True)

    def _click_for(self, index: int) -> pygame.mixer.Sound:
        """Clic aigu pendant le décompte, grave ensuite, plus marqué au début de chaque motif."""
        if index < 0:
            return self._count_in_click
        if self.plan.pattern and index % len(self.plan.pattern) == 0:
            return self._accent_click
        return self._beat_click

    def summary_lines(self) -> list[str]:
        """Résultats des séances terminées (caméra comparée au clavier s'il a été fait)."""
        lines: list[str] = []
        if self.results:
            lines.append(f"Cible : {self.target.describe()}")
            if self.camera_info is not None and not self.simulate:
                lines.append(f"Caméra obtenue : {self.camera_info.describe()}")
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
        if self.zones is not None:
            draw_zones(screen, PREVIEW_ORIGIN, 1.0, self.zones, self._small_font)
        else:
            plane_end_x = PREVIEW_ORIGIN[0] + surface.get_width()
            for marker in self.target.markers:
                plane_y = PREVIEW_ORIGIN[1] + int(marker.strike_plane_y)
                start, end = (PREVIEW_ORIGIN[0], plane_y), (plane_end_x, plane_y)
                pygame.draw.line(screen, PLANE_COLOR, start, end)
        for marker in self.target.markers:
            point = self._latest.markers[marker.name].point
            if point is not None:
                center = (PREVIEW_ORIGIN[0] + int(point.x), PREVIEW_ORIGIN[1] + int(point.y))
                color = self._lamp_color(now_ns, marker.display_color)
                pygame.draw.circle(screen, color, center, 8, width=2)

    def _tracked_markers(self) -> list[str]:
        """Libellés des embouts actuellement vus dans l'image."""
        if self._latest is None:
            return []
        return [
            marker.label
            for marker in self.target.markers
            if self._latest.markers[marker.name].point is not None
        ]

    def _lamp_color(self, now_ns: int, idle: tuple[int, int, int]) -> tuple[int, int, int]:
        """Vert pendant un court instant après un coup détecté, ``idle`` sinon."""
        if self._last_hit_ns is None:
            return idle
        lit = (now_ns - self._last_hit_ns) / NS_PER_SECOND < BEAT_LAMP_S
        return HIT_COLOR if lit else idle

    def _progress_text(self) -> str:
        last_click = self._next_click - 1
        if last_click < -self.plan.count_in_beats:
            return "Prépare-toi…"
        if last_click < 0:
            return f"Décompte : {last_click + self.plan.count_in_beats + 1}"
        return f"Coup {last_click + 1} / {self.plan.hit_count}"

    def _draw_pattern(self, screen: pygame.Surface, origin: tuple[int, int]) -> int:
        """Dessine le motif en cases (main et élément de chaque clic) ; renvoie l'ordonnée sous
        la dernière ligne. Le clic en cours est plein, le suivant est cerclé."""
        pattern = self.plan.pattern
        running = self.phase is Phase.RUNNING and self._next_click > 0
        current = (self._next_click - 1) % len(pattern) if running else None
        upcoming = self._next_click % len(pattern) if self.phase is Phase.RUNNING else None
        width, height = PATTERN_CELL
        x0, y0 = origin
        for index, element_id in enumerate(pattern):
            column, row = index % PATTERN_COLUMNS, index // PATTERN_COLUMNS
            cell = pygame.Rect(
                x0 + column * (width + PATTERN_GAP),
                y0 + row * (height + PATTERN_GAP),
                width,
                height,
            )
            if index == current:
                pygame.draw.rect(screen, CURRENT_CELL_COLOR, cell, border_radius=6)
                text_color = BACKGROUND_COLOR
            else:
                pygame.draw.rect(screen, LAMP_OFF_COLOR, cell, border_radius=6)
                if index == upcoming:
                    pygame.draw.rect(screen, CURRENT_CELL_COLOR, cell, width=2, border_radius=6)
                text_color = TEXT_COLOR
            hand = HAND_LABELS[hand_for_click(index)]
            screen.blit(
                self._small_font.render(f"{index + 1}  main {hand}", True, text_color),
                (cell.x + 8, cell.y + 6),
            )
            label = SHORT_LABELS.get(element_id, ELEMENTS_BY_ID[element_id].label_fr)
            screen.blit(self._font.render(label, True, text_color), (cell.x + 8, cell.y + 28))
        rows = math.ceil(len(pattern) / PATTERN_COLUMNS)
        return y0 + rows * (height + PATTERN_GAP)

    def draw(self, screen: pygame.Surface, now_ns: int) -> None:
        screen.fill(BACKGROUND_COLOR)
        uses_camera = self.source is Source.VISION and self.phase in (Phase.READY, Phase.RUNNING)
        if uses_camera:
            self._draw_preview(screen, now_ns)

        if self.pattern:
            title = f"Mesure US7 — {self.plan.hit_count} croches à {self.plan.bpm:.0f} BPM"
        else:
            title = (
                f"Mesure {self.target.label} — {self.plan.hit_count} coups "
                f"à {self.plan.bpm:.0f} BPM"
            )
        if self.simulate:
            title += " (simul.)"
        text_x = TEXT_X if uses_camera else PREVIEW_ORIGIN[0]
        screen.blit(self._title_font.render(title, True, TEXT_COLOR), (text_x, 20))
        top = (text_x, 64)

        if self.phase is Phase.MENU:
            y = self._draw_lines(
                screen,
                [
                    f"V : séance caméra — {self.target.label}",
                    "K : séance clavier de référence (barre d'espace, sans caméra)",
                    *(
                        ["(la latence geste → son demande les deux séances)"]
                        if self.pattern
                        else []
                    ),
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
                tracked = self._tracked_markers()
                lines = [
                    "Place-toi comme pour jouer. La ligne rouge est le plan",
                    "de frappe : le marqueur doit la traverser à chaque coup.",
                ]
                if self.pattern:
                    lines = [
                        "Place-toi comme pour jouer, embouts visibles.",
                        "Rectangle = ta zone, ligne rouge = plan de frappe.",
                    ]
                for marker in self.target.markers:
                    status = "suivi" if marker.label in tracked else "non détecté"
                    lines.append(f"{marker.label} : {status}")
            else:
                lines = ["Tape la barre d'espace sur chaque clic, d'un doigt."]
            lines += [
                "",
                f"Entrée : démarrer ({self.plan.count_in_beats} clics aigus de décompte,",
                f"puis un coup sur chacun des {self.plan.hit_count} clics graves)",
                "Échap : retour",
            ]
            y = self._draw_lines(screen, lines, top)
            if self.pattern and self.source is Source.VISION:
                self._draw_pattern(screen, (text_x, y + 16))

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
            if self.pattern and self.source is Source.VISION:
                self._draw_pattern(screen, (text_x, top[1] + 260))

        elif self.phase is Phase.RESULT:
            y = self._draw_lines(screen, ["Séance terminée. Entrée : retour au menu"], top)
            self._draw_lines(screen, self.summary_lines(), (text_x, y + 24), font=self._small_font)


def run(
    target: TargetPreset = STICK,
    *,
    simulate: bool = False,
    pattern: bool = False,
    bpm: float = US7_PLAN.bpm,
    zones: ZoneMap | None = None,
    camera: CameraSettings | None = None,
) -> None:
    init_mixer()
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption(f"Batterie — mesure vision ({target.label})")

    app = MeasureApp(
        target, simulate=simulate, pattern=pattern, bpm=bpm, zones=zones, camera=camera
    )
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


@dataclass(frozen=True)
class Options:
    """Ce que dit la ligne de commande."""

    target: TargetPreset
    simulate: bool = False
    pattern: bool = False  # séance US7 : motif de croches sur 4 éléments, deux mains
    bpm: float = US7_PLAN.bpm  # tempo de la séance US7


def parse_arguments(argv: list[str] | None = None) -> Options:
    """Lit la ligne de commande : la cible, le mode simulation et la séance US7."""
    parser = argparse.ArgumentParser(description="Séance de mesure vision (phases 03 et 04).")
    add_target_argument(parser)
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="marqueur fictif à la place de la webcam (pour voir le déroulé sans caméra)",
    )
    parser.add_argument(
        "--pattern",
        action="store_true",
        help=(
            "séance US7 : 100 croches à 90 BPM, motif de 8 croches sur 4 éléments, deux mains "
            "(zones calibrées nécessaires, sauf avec --simulate)"
        ),
    )
    parser.add_argument(
        "--bpm",
        type=float,
        default=US7_PLAN.bpm,
        help=(
            f"tempo de la séance US7, en BPM ({MIN_BPM:.0f} à {MAX_BPM:.0f}, défaut "
            f"{US7_PLAN.bpm:.0f}, le tempo du critère) ; avec --pattern seulement"
        ),
    )
    arguments = parser.parse_args(argv)
    if not MIN_BPM <= arguments.bpm <= MAX_BPM:
        parser.error(f"--bpm doit être entre {MIN_BPM:.0f} et {MAX_BPM:.0f}")
    if arguments.bpm != US7_PLAN.bpm and not arguments.pattern:
        parser.error("--bpm ne sert qu'avec --pattern (la séance de la phase 03 reste à 80 BPM)")
    if arguments.pattern:
        explicit_target = any(arg.startswith("--target") for arg in (argv or sys.argv[1:]))
        if explicit_target and arguments.target != "hands":
            parser.error(
                "--pattern se joue à deux mains : enlève --target ou utilise --target hands"
            )
        return Options(HANDS, simulate=arguments.simulate, pattern=True, bpm=arguments.bpm)
    return Options(TARGETS[arguments.target], simulate=arguments.simulate)


def _load_session_zones() -> ZoneMap | None:
    """Zones calibrées pour la séance US7 ; ``None`` (avec un message) si elles manquent."""
    try:
        zones = load_zones(working_width=WORKING_WIDTH)
    except ZonesError as error:
        print(f"{error}\nRecalibre depuis l'application : « Calibrer la caméra ».", file=sys.stderr)
        return None
    if not len(zones):
        print(
            f"Aucune zone calibrée ({zones_path()}).\n"
            "Lance l'application (uv run batterie), « Calibrer la caméra », puis reviens ici.",
            file=sys.stderr,
        )
        return None
    return zones


def main(argv: list[str] | None = None) -> int:
    # Les résultats contiennent « ≥ » et « − » : sortie en UTF-8 même redirigée vers un fichier.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    options = parse_arguments(argv)
    zones = None
    camera = None
    if options.pattern and not options.simulate:
        zones = _load_session_zones()
        if zones is None:
            return 1
        camera = load_settings().camera
    run(
        options.target,
        simulate=options.simulate,
        pattern=options.pattern,
        bpm=options.bpm,
        zones=zones,
        camera=camera,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
