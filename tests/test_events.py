"""Tests du modèle d'événement unifié (logique pure)."""

from batterie.core.events import HitEvent, Source


def test_hit_event_holds_its_fields():
    event = HitEvent(element_id="snare", velocity=0.8, t_ns=123, source=Source.VISION)
    assert event.element_id == "snare"
    assert event.velocity == 0.8
    assert event.t_ns == 123
    assert event.source is Source.VISION


def test_source_has_the_three_expected_values():
    assert {source.value for source in Source} == {"keyboard", "midi", "vision"}
