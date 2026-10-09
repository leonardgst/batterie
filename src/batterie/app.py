"""Boucle principale : accueil, jeu libre, choix et lecture d'une partition.

Le clavier est lu à chaque tour de boucle (≥ 500 Hz) ; le rendu est limité à
60 images/s. Une touche n'attend jamais l'image suivante pour sonner.
"""

from __future__ import annotations

import time
from enum import Enum, auto
from pathlib import Path

import pygame

from batterie.audio.engine import AudioEngine, init_mixer, load_kit
from batterie.config.settings import load_settings
from batterie.core.score import STYLES, Score, discover_scores, load_score
from batterie.core.transport import Transport
from batterie.input.keyboard import Keyboard, scancode_map_from_key_map
from batterie.ui.highway import HighwayView
from batterie.ui.kit_view import BACKGROUND_COLOR, KitView
from batterie.ui.menu import Menu, draw_menu

WINDOW_TITLE = "Batterie"
WINDOW_SIZE = (1280, 720)
TARGET_FPS = 60
INPUT_POLL_HZ = 500

DEFAULT_KIT_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "kits" / "default"
SCORES_DIR = Path(__file__).resolve().parent.parent.parent / "scores"

HIGHWAY_HEIGHT_FRACTION = 0.55

TEXT_COLOR = (230, 230, 235)
COUNT_IN_COLOR = (255, 205, 90)

HOME_FREE_PLAY = "Jeu libre"
HOME_SCORES = "Partitions"
HOME_ITEMS = [HOME_FREE_PLAY, HOME_SCORES]


class Mode(Enum):
    HOME = auto()
    FREE_PLAY = auto()
    STYLE_SELECT = auto()
    SCORE_SELECT = auto()
    PLAYING = auto()
    RESULT = auto()


def create_window() -> pygame.Surface:
    """Initialise pygame (audio avant fenêtre) et ouvre la fenêtre principale."""
    init_mixer()
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption(WINDOW_TITLE)
    return screen


def handle_events(events: list[pygame.event.Event]) -> bool:
    """Renvoie False si l'application doit s'arrêter (fermeture de la fenêtre)."""
    for event in events:
        if event.type == pygame.QUIT:
            return False
    return True


def _key_pressed(events: list[pygame.event.Event], key: int) -> bool:
    return any(event.type == pygame.KEYDOWN and event.key == key for event in events)


def _scores_for_style(style: str) -> list[Score]:
    scores = (load_score(path) for path in discover_scores(SCORES_DIR) if path.parent.name == style)
    return sorted(scores, key=lambda score: (score.difficulty, score.title))


def _draw_centered_text(
    screen: pygame.Surface,
    area: pygame.Rect,
    lines: list[tuple[str, int, tuple[int, int, int]]],
) -> None:
    y = area.centery - (len(lines) * 40) // 2
    for text, size, color in lines:
        font = pygame.font.SysFont("consolas", size, bold=True)
        surface = font.render(text, True, color)
        screen.blit(surface, surface.get_rect(center=(area.centerx, y)))
        y += size + 16


def run() -> None:
    """Boucle principale, jusqu'à la fermeture de la fenêtre."""
    screen = create_window()
    settings = load_settings()
    engine = AudioEngine(load_kit(DEFAULT_KIT_DIR), master_volume=settings.volume)
    keyboard = Keyboard(scancode_map_from_key_map(settings.key_map))
    kit_view = KitView()
    highway_view = HighwayView()

    mode = Mode.HOME
    home_menu: Menu[str] = Menu(items=HOME_ITEMS)
    style_menu: Menu[str] | None = None
    score_menu: Menu[Score] | None = None
    score: Score | None = None
    transport: Transport | None = None

    full_area = screen.get_rect()
    highway_height = int(WINDOW_SIZE[1] * HIGHWAY_HEIGHT_FRACTION)
    highway_area = pygame.Rect(0, 0, WINDOW_SIZE[0], highway_height)
    kit_area = pygame.Rect(0, highway_height, WINDOW_SIZE[0], WINDOW_SIZE[1] - highway_height)

    poll_clock = pygame.time.Clock()
    render_interval_s = 1.0 / TARGET_FPS
    next_render = time.perf_counter()

    running = True
    try:
        while running:
            events = pygame.event.get()
            running = handle_events(events)
            now_ns = time.perf_counter_ns()

            if mode == Mode.HOME:
                if _key_pressed(events, pygame.K_UP):
                    home_menu.move(-1)
                if _key_pressed(events, pygame.K_DOWN):
                    home_menu.move(1)
                if _key_pressed(events, pygame.K_RETURN):
                    if home_menu.selected == HOME_FREE_PLAY:
                        mode = Mode.FREE_PLAY
                    else:
                        style_menu = Menu(items=list(STYLES))
                        mode = Mode.STYLE_SELECT
                if _key_pressed(events, pygame.K_ESCAPE):
                    running = False

            elif mode == Mode.FREE_PLAY:
                for element_id in keyboard.poll(events):
                    engine.play(element_id)
                    kit_view.flash(element_id)
                if _key_pressed(events, pygame.K_ESCAPE):
                    mode = Mode.HOME

            elif mode == Mode.STYLE_SELECT:
                assert style_menu is not None
                if _key_pressed(events, pygame.K_UP):
                    style_menu.move(-1)
                if _key_pressed(events, pygame.K_DOWN):
                    style_menu.move(1)
                if _key_pressed(events, pygame.K_RETURN):
                    score_menu = Menu(items=_scores_for_style(style_menu.selected))
                    mode = Mode.SCORE_SELECT
                if _key_pressed(events, pygame.K_ESCAPE):
                    mode = Mode.HOME

            elif mode == Mode.SCORE_SELECT:
                assert score_menu is not None
                if _key_pressed(events, pygame.K_UP):
                    score_menu.move(-1)
                if _key_pressed(events, pygame.K_DOWN):
                    score_menu.move(1)
                if _key_pressed(events, pygame.K_RETURN) and score_menu.items:
                    score = score_menu.selected
                    transport = Transport(bpm=score.bpm, time_signature=score.time_signature)
                    transport.start(now_ns, count_in_beats=transport.beats_per_measure)
                    mode = Mode.PLAYING
                if _key_pressed(events, pygame.K_ESCAPE):
                    mode = Mode.STYLE_SELECT

            elif mode == Mode.PLAYING:
                assert transport is not None and score is not None
                if transport.is_paused:
                    if _key_pressed(events, pygame.K_RETURN):
                        transport.resume(now_ns)
                    if _key_pressed(events, pygame.K_ESCAPE):
                        mode = Mode.SCORE_SELECT
                else:
                    if _key_pressed(events, pygame.K_ESCAPE):
                        transport.pause(now_ns)
                    else:
                        for element_id in keyboard.poll(events):
                            engine.play(element_id)
                            kit_view.flash(element_id)
                        if transport.current_beat(now_ns) >= score.duration_beats:
                            mode = Mode.RESULT

            elif mode == Mode.RESULT:
                assert score is not None
                if _key_pressed(events, pygame.K_RETURN):
                    transport = Transport(bpm=score.bpm, time_signature=score.time_signature)
                    transport.start(now_ns, count_in_beats=transport.beats_per_measure)
                    mode = Mode.PLAYING
                if _key_pressed(events, pygame.K_ESCAPE):
                    mode = Mode.SCORE_SELECT

            now = time.perf_counter()
            if now >= next_render:
                _draw(
                    screen,
                    mode,
                    full_area,
                    highway_area,
                    kit_area,
                    kit_view,
                    highway_view,
                    home_menu,
                    style_menu,
                    score_menu,
                    score,
                    transport,
                    now_ns,
                )
                pygame.display.flip()
                next_render = now + render_interval_s

            poll_clock.tick(INPUT_POLL_HZ)
    finally:
        pygame.quit()


def _draw(
    screen: pygame.Surface,
    mode: Mode,
    full_area: pygame.Rect,
    highway_area: pygame.Rect,
    kit_area: pygame.Rect,
    kit_view: KitView,
    highway_view: HighwayView,
    home_menu: Menu[str],
    style_menu: Menu[str] | None,
    score_menu: Menu[Score] | None,
    score: Score | None,
    transport: Transport | None,
    now_ns: int,
) -> None:
    screen.fill(BACKGROUND_COLOR)

    if mode == Mode.HOME:
        draw_menu(screen, full_area, "Batterie", home_menu.items, home_menu.index)

    elif mode == Mode.FREE_PLAY:
        kit_view.draw(screen, full_area)

    elif mode == Mode.STYLE_SELECT and style_menu is not None:
        draw_menu(screen, full_area, "Choisis un style", style_menu.items, style_menu.index)

    elif mode == Mode.SCORE_SELECT and score_menu is not None:
        labels = [
            f"{s.title} — {int(s.bpm)} BPM — difficulté {s.difficulty}" for s in score_menu.items
        ]
        if not labels:
            labels = ["(aucune partition dans ce style)"]
        draw_menu(screen, full_area, "Choisis une partition", labels, score_menu.index)

    elif mode == Mode.PLAYING and transport is not None and score is not None:
        current_beat = transport.current_beat(now_ns)
        highway_view.draw(screen, highway_area, score, current_beat)
        kit_view.draw(screen, kit_area)
        if current_beat < 0:
            count = int(-current_beat) + 1
            _draw_centered_text(screen, highway_area, [(str(count), 96, COUNT_IN_COLOR)])
        if transport.is_paused:
            _draw_centered_text(
                screen,
                highway_area,
                [
                    ("PAUSE", 64, TEXT_COLOR),
                    ("Entrée : reprendre — Échap : quitter la partition", 24, TEXT_COLOR),
                ],
            )

    elif mode == Mode.RESULT and score is not None:
        _draw_centered_text(
            screen,
            full_area,
            [
                (f"Terminé : {score.title}", 48, TEXT_COLOR),
                ("Entrée : rejouer — Échap : retour à la liste", 24, TEXT_COLOR),
            ],
        )


def main() -> int:
    """Point d'entrée du script `batterie`."""
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
