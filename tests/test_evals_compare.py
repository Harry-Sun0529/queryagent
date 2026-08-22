"""Unit tests for result-set comparison (the eval methodology core)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from queryagent.evals.compare import normalize_value, rows_match


def test_order_insensitive() -> None:
    assert rows_match([(1, "a"), (2, "b")], [(2, "b"), (1, "a")])


def test_duplicates_are_multiset_not_set() -> None:
    assert not rows_match([(1,), (1,)], [(1,)])
    assert rows_match([(1,), (1,)], [(1,), (1,)])


def test_float_tolerance() -> None:
    assert rows_match([(0.1 + 0.2,)], [(0.3,)])
    assert rows_match([(1.00001,)], [(1.0,)])
    assert not rows_match([(1.01,)], [(1.0,)])


def test_int_matches_equal_float_and_decimal() -> None:
    # sqlite COUNT returns int, mysql SUM returns Decimal — same number matches
    assert rows_match([(3,)], [(3.0,)])
    assert rows_match([(Decimal("19.99"),)], [(19.99,)])


def test_datetime_matches_iso_text() -> None:
    # mysql returns datetime objects; sqlite stores ISO text
    assert rows_match(
        [(datetime(2026, 7, 1, 12, 30, 0),)],
        [("2026-07-01 12:30:00",)],
    )


def test_width_mismatch_fails() -> None:
    assert not rows_match([(1, "a")], [(1,)])


def test_none_and_bool_normalisation() -> None:
    assert normalize_value(None) is None
    assert normalize_value(True) == 1
    assert rows_match([(None, True)], [(None, 1)])


def test_empty_sets_match() -> None:
    assert rows_match([], [])
    assert not rows_match([(1,)], [])


def test_aware_datetimes_at_different_instants_differ() -> None:
    # 12:00 UTC and 12:00+08:00 are eight hours apart. Formatting without the
    # offset made them compare equal — in the comparison layer the whole
    # evaluation rests on.
    from datetime import timedelta, timezone

    utc_noon = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    shanghai_noon = datetime(2026, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=8)))
    assert not rows_match([(utc_noon,)], [(shanghai_noon,)])


def test_the_same_instant_in_two_zones_matches() -> None:
    from datetime import timedelta, timezone

    utc = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    shanghai = datetime(2026, 1, 1, 20, 0, tzinfo=timezone(timedelta(hours=8)))
    assert rows_match([(utc,)], [(shanghai,)])


def test_naive_datetimes_are_left_alone() -> None:
    # The three shipped dialects return naive values; guessing a zone for
    # them would invent information.
    a = datetime(2026, 7, 1, 12, 30, 0)
    assert rows_match([(a,)], [("2026-07-01 12:30:00",)])
