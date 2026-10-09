"""Tests du suivi de couleur, sur des images synthétiques (pas de caméra)."""

import cv2
import numpy as np
import pytest

from batterie.input.vision.color_tracker import GREEN, ColorRange, find_marker

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
