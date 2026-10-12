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


# --- Séance US7 : motif, attribution, critères (phase 04) ---------------------------

from batterie.input.vision.measure import (  # noqa: E402
    US7_PATTERN,
    US7_PLAN,
    count_attribution,
    hand_for_click,
    latency_to_sound_ms,
    us7_checks,
)

INTERVAL = US7_PLAN.beat_interval_s


def _pattern_hits(delay_s: float = 0.04) -> list[tuple[float, str]]:
    """Une séance parfaite : un coup par clic, sur le bon élément, ``delay_s`` après le clic."""
    return [
        (US7_PLAN.beat_time_s(index) + delay_s, US7_PLAN.expected_element(index))
        for index in range(US7_PLAN.hit_count)
    ]


def _vision_result(hits, *, first_beat_s: float = 10.0):
    recorder = SessionRecorder(plan=US7_PLAN, source=Source.VISION, first_beat_s=first_beat_s)
    for t_s, element_id in hits:
        recorder.add_hit(first_beat_s + t_s, element_id)
    return recorder.result()


def _keyboard_reference(delay_s: float = 0.0, *, first_beat_s: float = 10.0):
    recorder = SessionRecorder(plan=US7_PLAN, source=Source.KEYBOARD, first_beat_s=first_beat_s)
    for index in range(US7_PLAN.hit_count):
        recorder.add_hit(first_beat_s + US7_PLAN.beat_time_s(index) + delay_s)
    return recorder.result()


def _checks_by_label(result, reference=None):
    return {check.label: check for check in us7_checks(result, reference)}


def test_us7_plan_is_100_eighth_notes_at_90_bpm():
    assert US7_PLAN.hit_count == 100
    assert US7_PLAN.bpm == 90.0
    assert INTERVAL == pytest.approx(1 / 3)  # croches : deux clics par temps de 2/3 s
    assert US7_PLAN.detection_target == 0.95


def test_us7_pattern_is_eight_eighths_on_the_four_elements():
    assert len(US7_PATTERN) == 8
    assert set(US7_PATTERN) == {"hihat_closed", "snare", "tom_mid", "ride"}
    assert US7_PLAN.count_in_beats == 8  # un décompte d'une mesure de croches


def test_expected_element_repeats_the_pattern():
    assert [US7_PLAN.expected_element(i) for i in range(10)] == [*US7_PATTERN, *US7_PATTERN[:2]]
    assert US7_PLAN.expected_element(99) == US7_PATTERN[99 % 8]


def test_expected_element_is_none_without_a_pattern():
    assert PLAN.expected_element(0) is None


def test_hands_alternate_on_every_click():
    assert [hand_for_click(i) for i in range(4)] == ["left", "right", "left", "right"]
    assert hand_for_click(98) == "left" and hand_for_click(99) == "right"


def test_a_perfect_session_meets_every_us7_criterion():
    result = _vision_result(_pattern_hits(0.045))
    checks = _checks_by_label(result, _keyboard_reference())

    assert result.detected == 100 and result.extra == 0
    assert result.attributed == 100 and result.confusions == ()
    assert [check.met for check in checks.values()] == [True, True, True, True]


def test_latency_is_the_camera_delay_over_the_keyboard_plus_the_audio_engine():
    result = _vision_result(_pattern_hits(0.045))
    assert latency_to_sound_ms(result, _keyboard_reference(0.002)) == pytest.approx(48.0)


def test_latency_over_60_ms_fails_the_latency_criterion_only():
    result = _vision_result(_pattern_hits(0.060))
    checks = _checks_by_label(result, _keyboard_reference())

    assert latency_to_sound_ms(result, _keyboard_reference()) == pytest.approx(65.0)
    assert checks["Latence geste → son"].met is False
    assert checks["Coups détectés"].met is True


def test_latency_is_not_evaluable_without_the_keyboard_reference():
    checks = _checks_by_label(_vision_result(_pattern_hits()))
    assert checks["Latence geste → son"].met is None
    assert "clavier" in checks["Latence geste → son"].value


def test_detection_criterion_is_95_percent():
    hits = _pattern_hits()
    assert _checks_by_label(_vision_result(hits[:-5]))["Coups détectés"].met is True
    assert _checks_by_label(_vision_result(hits[:-6]))["Coups détectés"].met is False


def test_false_hit_criterion_is_2_percent_of_the_clicks():
    hits = _pattern_hits()
    two_extra = [*hits, (INTERVAL * 5 + 0.15, "snare"), (INTERVAL * 9 + 0.15, "snare")]
    three_extra = [*two_extra, (INTERVAL * 20 + 0.15, "ride")]

    # Un coup en plus dans la fenêtre d'un clic déjà touché est un faux coup.
    assert _checks_by_label(_vision_result(two_extra))["Faux coups"].met is True
    result = _vision_result(three_extra)
    assert result.extra == 3
    assert _checks_by_label(result)["Faux coups"].met is False


def test_hits_during_the_count_in_or_after_the_session_are_ignored_not_false_hits():
    hits = [(-1.0, "snare"), *_pattern_hits(), (US7_PLAN.beat_time_s(100) + 1.0, "snare")]
    result = _vision_result(hits)
    assert result.extra == 0
    assert result.detected == 100


def _with_wrong_elements(count: int, got: str = "tom_mid"):
    """Les ``count`` premiers coups de caisse claire du motif sont attribués à ``got``."""
    hits = _pattern_hits()
    wrong = [i for i, (_, element) in enumerate(hits) if element == "snare"][:count]
    for index in wrong:
        hits[index] = (hits[index][0], got)
    return hits


def test_attribution_criterion_is_95_percent_of_detected_hits():
    five = _checks_by_label(_vision_result(_with_wrong_elements(5)))
    assert five["Attribués au bon élément"].met is True
    result = _vision_result(_with_wrong_elements(6))
    assert result.attributed == 94
    assert _checks_by_label(result)["Attribués au bon élément"].met is False


def test_attribution_is_counted_over_detected_hits_not_over_all_clicks():
    # 90 clics touchés sur 100, tous sur le bon élément : l'attribution est parfaite,
    # c'est la détection qui échoue.
    result = _vision_result(_pattern_hits()[:90])
    assert result.attribution_rate == 1.0
    assert _checks_by_label(result)["Coups détectés"].met is False


def test_confusions_are_listed_from_the_most_frequent():
    hits = _pattern_hits()
    swaps = {1: "tom_mid", 9: "tom_mid", 17: "tom_mid", 5: "snare"}  # 3 × snare→tom, 1 × ride→snare
    for index, got in swaps.items():
        hits[index] = (hits[index][0], got)

    result = _vision_result(hits)

    assert result.confusions == (("snare", "tom_mid", 3), ("ride", "snare", 1))


def test_the_hit_closest_to_the_click_decides_the_attribution():
    hits = _pattern_hits(0.04)
    # Sur le clic 1 (caisse claire), un coup parasite sur le ride, plus loin que le bon coup.
    hits.append((US7_PLAN.beat_time_s(1) + 0.12, "ride"))

    result = _vision_result(hits)

    assert result.attributed == 100
    assert result.extra == 1


def test_a_nearer_wrong_hit_takes_the_click_and_the_right_one_becomes_extra():
    hits = _pattern_hits(0.12)
    hits.append((US7_PLAN.beat_time_s(1) + 0.02, "ride"))  # plus proche du clic, mauvais élément

    result = _vision_result(hits)

    assert result.attributed == 99
    assert result.confusions == (("snare", "ride", 1),)
    assert result.extra == 1


def test_count_attribution_ignores_hits_without_an_element():
    hits = [(0.0, None), (INTERVAL, "snare")]
    assert count_attribution(US7_PLAN, hits) == (1, ())


def test_a_keyboard_session_has_no_attribution_nor_us7_checks():
    reference = _keyboard_reference()
    assert reference.attributed is None
    assert reference.attribution_rate is None
    assert us7_checks(reference) == []


def test_a_session_without_a_pattern_has_no_us7_checks():
    recorder = SessionRecorder(plan=PLAN, source=Source.VISION, first_beat_s=0.0)
    recorder.add_hit(0.0, "snare")
    result = recorder.result()
    assert result.attributed is None
    assert us7_checks(result) == []


def test_report_of_a_us7_session_lists_each_criterion_and_the_confusions():
    result = _vision_result(_with_wrong_elements(8))
    text = "\n".join(format_report(result, _keyboard_reference()))

    assert "100 coups à 90 BPM (croches)" in text
    assert "Critères US7 :" in text
    assert "Attribués au bon élément : 92 % (92 / 100) — critère ≥ 95 % : NON ATTEINT" in text
    assert "attendu Caisse claire, obtenu Tom médium : 8" in text
    assert "Latence geste → son : +45 ms — critère ≤ 60 ms : atteint" in text


def test_report_of_a_phase_03_session_is_unchanged():
    recorder = SessionRecorder(plan=PLAN, source=Source.VISION, first_beat_s=0.0)
    for index in range(4):
        recorder.add_hit(PLAN.beat_time_s(index) + 0.05)
    text = "\n".join(format_report(recorder.result()))

    assert "critère ≥ 90 % : atteint" in text
    assert "US7" not in text
    assert "bon élément" not in text
