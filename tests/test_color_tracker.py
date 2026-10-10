"""Tests du suivi de couleur, sur des images synthétiques (pas de caméra)."""

import cv2
import numpy as np
import pytest

from batterie.input.vision.color_tracker import GREEN, ORANGE, ColorRange, find_marker

IMAGE_SIZE = 200


def _bgr_for_hsv(h: int, s: int, v: int) -> tuple[int, int, int]:
    pixel = np.uint8([[[h, s, v]]])
    bgr = cv2.cvtColor(pixel, cv2.COLOR_HSV2BGR)[0][0]
    return int(bgr[0]), int(bgr[1]), int(bgr[2])


def _frame_with_square(
    color_bgr: tuple[int, int, int], *, center: tuple[int, int], half_size: int
) -> np.ndarray:
    frame = np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
    cx, cy = center
    frame[cy - half_size : cy + half_size, cx - half_size : cx + half_size] = color_bgr
    return frame


def test_find_marker_locates_the_center_of_a_colored_square():
    green_bgr = _bgr_for_hsv(60, 200, 200)
    frame = _frame_with_square(green_bgr, center=(80, 120), half_size=15)

    point = find_marker(frame, GREEN)

    assert point is not None
    assert point.x == pytest.approx(80, abs=1)
    assert point.y == pytest.approx(120, abs=1)
    # cv2.contourArea mesure l'aire du polygone du contour, légèrement sous le carré rastérisé.
    assert point.area == pytest.approx(29 * 29, abs=5)


def test_find_marker_returns_none_on_a_blank_frame():
    frame = np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
    assert find_marker(frame, GREEN) is None


def test_find_marker_ignores_a_tiny_speck_of_the_right_color():
    green_bgr = _bgr_for_hsv(60, 200, 200)
    frame = _frame_with_square(green_bgr, center=(80, 120), half_size=2)  # 4x4 px, trop petit

    assert find_marker(frame, GREEN) is None


def test_find_marker_ignores_a_square_of_a_different_color():
    red_bgr = _bgr_for_hsv(0, 200, 200)
    frame = _frame_with_square(red_bgr, center=(80, 120), half_size=15)

    assert find_marker(frame, GREEN) is None


def test_find_marker_picks_the_largest_match_when_several_blobs():
    green_bgr = _bgr_for_hsv(60, 200, 200)
    frame = np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
    # Petite tache (bruit) + grande tache (le vrai embout).
    frame[10:15, 10:15] = green_bgr
    frame[150:180, 150:180] = green_bgr

    point = find_marker(frame, GREEN)

    assert point is not None
    assert point.x == pytest.approx(165, abs=1)
    assert point.y == pytest.approx(165, abs=1)


def test_find_marker_works_with_a_custom_color_range():
    blue_bgr = _bgr_for_hsv(110, 200, 200)
    custom = ColorRange(lower=(100, 80, 60), upper=(120, 255, 255))
    frame = _frame_with_square(blue_bgr, center=(50, 60), half_size=15)

    point = find_marker(frame, custom)

    assert point is not None
    assert point.x == pytest.approx(50, abs=1)
    assert point.y == pytest.approx(60, abs=1)


# --- Orange (main gauche, phase 04) ---

# Teintes de peau types en HSV OpenCV (H, S, V) : même teinte qu'un orange, saturation bien
# plus basse. Des valeurs synthétiques représentatives, pas des mesures : la vraie vérification
# se fait sur ta main avec ``vision_debug.py --target hands``.
SKIN_TONES_HSV = [
    (6, 90, 230),
    (8, 60, 180),
    (10, 120, 210),
    (12, 140, 190),
    (14, 100, 160),
    (16, 150, 200),
    (18, 80, 220),
    (20, 110, 130),
]
VIVID_ORANGE_HSV = (14, 230, 255)


def test_find_marker_tracks_a_vivid_orange_blob():
    frame = _frame_with_square(_bgr_for_hsv(*VIVID_ORANGE_HSV), center=(60, 70), half_size=12)
    point = find_marker(frame, ORANGE)
    assert point is not None
    assert point.x == pytest.approx(60, abs=1)
    assert point.y == pytest.approx(70, abs=1)


@pytest.mark.parametrize("skin_hsv", SKIN_TONES_HSV)
def test_orange_does_not_track_skin_tones(skin_hsv):
    frame = _frame_with_square(_bgr_for_hsv(*skin_hsv), center=(100, 100), half_size=40)
    assert find_marker(frame, ORANGE) is None


def test_pale_orange_is_deliberately_not_tracked():
    # Le prix de la parade contre la peau : un orange pâle n'est pas suivi (voir ORANGE).
    frame = _frame_with_square(_bgr_for_hsv(14, 110, 255), center=(100, 100), half_size=20)
    assert find_marker(frame, ORANGE) is None


def test_orange_and_green_ranges_do_not_pick_up_each_other():
    orange_frame = _frame_with_square(
        _bgr_for_hsv(*VIVID_ORANGE_HSV), center=(50, 50), half_size=15
    )
    green_frame = _frame_with_square(_bgr_for_hsv(60, 200, 200), center=(50, 50), half_size=15)
    assert find_marker(orange_frame, GREEN) is None
    assert find_marker(green_frame, ORANGE) is None
