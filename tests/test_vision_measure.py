"""Tests de la séance de mesure : comptage des coups et résumé des latences, sans caméra."""

import pytest

from batterie.core.events import Source
from batterie.input.vision.measure import (
    SessionPlan,
    SessionRecorder,
    format_report,
    match_hits,
    offset_vs_reference_ms,
    summarize,
)

PLAN = SessionPlan(bpm=120.0, hit_count=4, count_in_beats=2)  # un clic toutes les 0,5 s


def test_default_plan_is_the_phase_03_criterion():
    plan = SessionPlan()
    assert plan.hit_count == 50
    assert plan.bpm == 80.0
    assert plan.beat_interval_s == pytest.approx(0.75)


def test_plan_places_count_in_clicks_before_the_first_measured_beat():
    assert PLAN.beat_time_s(-2) == pytest.approx(-1.0)
    assert PLAN.beat_time_s(0) == 0.0
    assert PLAN.beat_time_s(3) == pytest.approx(1.5)
    assert PLAN.measured_duration_s == pytest.approx(1.75)


def test_summarize_returns_none_for_an_empty_series():
    assert summarize([]) is None


def test_summarize_reports_median_p95_and_max():
    summary = summarize([float(value) for value in range(1, 101)])
    assert summary is not None
    assert summary.count == 100
    assert summary.mean == pytest.approx(50.5)
    assert summary.median == pytest.approx(50.5)
    assert summary.p95 == 95.0
    assert summary.maximum == 100.0


def test_match_hits_pairs_each_hit_with_its_click():
    offsets_ms, extra = match_hits(PLAN, [0.02, 0.48, 1.03, 1.5])
    assert offsets_ms == pytest.approx([20.0, -20.0, 30.0, 0.0])
    assert extra == 0


def test_match_hits_leaves_a_click_without_hit_undetected():
    offsets_ms, extra = match_hits(PLAN, [0.0, 1.0, 1.5])
    assert len(offsets_ms) == 3
    assert extra == 0


def test_match_hits_counts_a_second_hit_on_the_same_click_as_extra():
    offsets_ms, extra = match_hits(PLAN, [0.1, 0.01, 0.5])
    # Le clic 0 garde le coup le plus proche (10 ms), l'autre est un faux coup.
    assert offsets_ms == pytest.approx([10.0, 0.0])
    assert extra == 1


def test_match_hits_counts_hits_outside_the_session_as_extra():
    offsets_ms, extra = match_hits(PLAN, [-0.6, 2.2])
    assert offsets_ms == []
    assert extra == 2


def test_recorder_ignores_warm_up_hits_during_the_count_in():
    recorder = SessionRecorder(plan=PLAN, source=Source.KEYBOARD, first_beat_s=100.0)
    recorder.add_hit(99.0)  # pendant le décompte
    recorder.add_hit(100.01)
    recorder.add_hit(102.0)  # après la fenêtre du dernier clic
    assert recorder.hit_count == 1

    result = recorder.result()
    assert result.detected == 1
    assert result.missed == 3
    assert result.extra == 0


def test_recorder_knows_when_the_session_is_over():
    recorder = SessionRecorder(plan=PLAN, source=Source.KEYBOARD, first_beat_s=100.0)
    assert not recorder.is_over(101.7)
    assert recorder.is_over(101.75)


def test_keyboard_result_has_no_camera_statistics():
    recorder = SessionRecorder(plan=PLAN, source=Source.KEYBOARD, first_beat_s=0.0)
    for t_s in (0.0, 0.5, 1.0, 1.5):
        recorder.add_hit(t_s)

    result = recorder.result()

    assert result.detection_rate == 1.0
    assert result.meets_target
    assert result.processing_ms is None
    assert result.frame_interval_ms is None
    assert result.tracked_ratio is None
    assert result.fps is None
    assert result.software_delay_ms is None


def test_vision_result_summarizes_frames():
    recorder = SessionRecorder(plan=PLAN, source=Source.VISION, first_beat_s=0.0)
    # 4 images à 20 ms d'intervalle, 2 ms de traitement, embout perdu sur la dernière.
    for index in range(4):
        recorder.add_frame(index * 0.020, processing_ms=2.0, tracked=index < 3)
    recorder.add_frame(-5.0, processing_ms=50.0, tracked=False)  # hors séance : ignorée

    result = recorder.result()

    assert result.processing_ms is not None and result.processing_ms.count == 4
    assert result.processing_ms.median == pytest.approx(2.0)
    assert result.frame_interval_ms is not None
    assert result.frame_interval_ms.median == pytest.approx(20.0)
    assert result.fps == pytest.approx(50.0)
    assert result.tracked_ratio == pytest.approx(0.75)
    # Demi-intervalle (10 ms) + traitement (2 ms).
    assert result.software_delay_ms == pytest.approx(12.0)


def test_detection_target_is_ninety_percent():
    plan = SessionPlan(bpm=120.0, hit_count=10)
    recorder = SessionRecorder(plan=plan, source=Source.VISION, first_beat_s=0.0)
    for index in range(9):
        recorder.add_hit(plan.beat_time_s(index))
    assert recorder.result().meets_target

    recorder = SessionRecorder(plan=plan, source=Source.VISION, first_beat_s=0.0)
    for index in range(8):
        recorder.add_hit(plan.beat_time_s(index))
    assert not recorder.result().meets_target


def _result_with_constant_offset(source: Source, offset_s: float):
    recorder = SessionRecorder(plan=PLAN, source=source, first_beat_s=0.0)
    for index in range(PLAN.hit_count):
        recorder.add_hit(PLAN.beat_time_s(index) + offset_s)
    return recorder.result()


def test_offset_vs_reference_cancels_what_both_sessions_share():
    keyboard = _result_with_constant_offset(Source.KEYBOARD, -0.030)  # anticipation naturelle
    vision = _result_with_constant_offset(Source.VISION, 0.040)
    assert offset_vs_reference_ms(vision, keyboard) == pytest.approx(70.0)


def test_offset_vs_reference_needs_hits_in_both_sessions():
    keyboard = _result_with_constant_offset(Source.KEYBOARD, 0.0)
    empty = SessionRecorder(plan=PLAN, source=Source.VISION, first_beat_s=0.0).result()
    assert offset_vs_reference_ms(empty, keyboard) is None


def test_format_report_states_the_count_and_the_verdict():
    lines = format_report(_result_with_constant_offset(Source.KEYBOARD, 0.010))
    text = "\n".join(lines)
    assert "clavier" in text
    assert "4 / 4" in text
    assert "atteint" in text and "non atteint" not in text
    assert "+10 ms" in text


def test_format_report_of_an_empty_session_does_not_crash():
    empty = SessionRecorder(plan=PLAN, source=Source.VISION, first_beat_s=0.0).result()
    text = "\n".join(format_report(empty))
    assert "0 / 4" in text
    assert "non atteint" in text


def test_format_report_compares_a_vision_session_with_its_reference():
    keyboard = _result_with_constant_offset(Source.KEYBOARD, -0.030)
    vision = _result_with_constant_offset(Source.VISION, 0.040)
    text = "\n".join(format_report(vision, reference=keyboard))
    assert "Retard par rapport au clavier : +70 ms" in text
