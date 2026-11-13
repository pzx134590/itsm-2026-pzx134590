# ai-generated: 100% - Claude Code wrote this file from the slaclock docstrings; the student reviews it
import itertools
from datetime import datetime, timedelta

import pytest

import slaclock as s

MON = datetime(2026, 11, 16)  # a Monday
FRI = datetime(2026, 11, 20)
SAT = datetime(2026, 11, 21)
SUN = datetime(2026, 11, 22)


def at(day, h, m=0, sec=0, us=0):
    return day.replace(hour=h, minute=m, second=sec, microsecond=us)


# ---------- priority_of ----------
MATRIX = {
    (1, 1): "P1", (1, 2): "P2", (2, 1): "P2", (1, 3): "P3", (2, 2): "P3", (3, 1): "P3",
    (2, 3): "P4", (3, 2): "P4", (3, 3): "P4",
}


@pytest.mark.parametrize("cell", MATRIX)
def test_priority_matrix(cell):
    assert s.priority_of(*cell) == MATRIX[cell]
    assert s.priority_of(cell[0], cell[1], False) == MATRIX[cell]
    assert s.priority_of(cell[0], cell[1], vip=False) == MATRIX[cell]


@pytest.mark.parametrize("cell", MATRIX)
def test_priority_vip(cell):
    expected = "P2" if MATRIX[cell] in ("P3", "P4") else MATRIX[cell]
    assert s.priority_of(*cell, vip=True) == expected
    assert s.priority_of(cell[0], cell[1], True) == expected


@pytest.mark.parametrize("bad", [0, 4, -1, 2.0, True, False, "1", None, 1.5, 10])
def test_priority_invalid_impact(bad):
    with pytest.raises(ValueError):
        s.priority_of(bad, 1)
    with pytest.raises(ValueError):
        s.priority_of(bad, 1, vip=True)


@pytest.mark.parametrize("bad", [0, 4, -1, 2.0, True, False, "1", None, 1.5, 10])
def test_priority_invalid_urgency(bad):
    with pytest.raises(ValueError):
        s.priority_of(1, bad)
    with pytest.raises(ValueError):
        s.priority_of(3, bad, vip=True)


def test_priority_returns_str():
    assert type(s.priority_of(2, 2)) is str


# ---------- targets ----------
@pytest.mark.parametrize("p,t", [("P1", (15, 240)), ("P2", (60, 480)), ("P3", (240, 1440)), ("P4", (480, 4320))])
def test_targets(p, t):
    r = s.targets(p)
    assert tuple(r) == t
    assert r[0] == t[0] and r[1] == t[1]


@pytest.mark.parametrize("bad", ["p1", " P1", "P1 ", "P5", "P0", "", "P", "1", "P12", "P1\n"])
def test_targets_invalid(bad):
    with pytest.raises(ValueError):
        s.targets(bad)


# ---------- sla_state ----------
@pytest.mark.parametrize("elapsed,target,state", [
    (0, 15, "ok"), (11, 15, "ok"), (12, 15, "warning"), (14, 15, "warning"), (15, 15, "warning"),
    (16, 15, "breached"), (100, 15, "breached"),
    (0, 100, "ok"), (74, 100, "ok"), (75, 100, "warning"), (76, 100, "warning"),
    (99, 100, "warning"), (100, 100, "warning"), (101, 100, "breached"),
    (0, 1, "ok"), (1, 1, "warning"), (2, 1, "breached"),
    (2, 3, "ok"), (3, 4, "warning"), (2, 4, "ok"),
    (179, 240, "ok"), (180, 240, "warning"), (240, 240, "warning"), (241, 240, "breached"),
    (1079, 1440, "ok"), (1080, 1440, "warning"), (1440, 1440, "warning"), (1441, 1440, "breached"),
    (6, 7, "warning"), (5, 7, "ok"), (3, 4, "warning"), (6, 8, "warning"), (5, 8, "ok"),
    (10 ** 6, 10 ** 6, "warning"), (10 ** 6 + 1, 10 ** 6, "breached"), (750000, 10 ** 6, "warning"),
    (749999, 10 ** 6, "ok"),
])
def test_sla_state(elapsed, target, state):
    assert s.sla_state(elapsed, target) == state


@pytest.mark.parametrize("elapsed,target", [(-1, 10), (-100, 10), (5, 0), (5, -1), (0, 0), (-1, 0), (-1, -1), (0, -5)])
def test_sla_state_invalid(elapsed, target):
    with pytest.raises(ValueError):
        s.sla_state(elapsed, target)


def test_sla_state_zero_elapsed_valid():
    assert s.sla_state(0, 1) == "ok"


# ---------- is_business_time ----------
@pytest.mark.parametrize("day", [MON, MON + timedelta(1), MON + timedelta(2), MON + timedelta(3), FRI])
def test_business_time_weekdays(day):
    for h, m, exp in [(0, 0, False), (7, 0, False), (7, 59, False), (8, 0, True), (8, 1, True), (12, 0, True),
                      (15, 59, True), (16, 0, False), (16, 1, False), (23, 59, False)]:
        assert s.is_business_time(at(day, h, m)) is exp, (day, h, m)


@pytest.mark.parametrize("day", [SAT, SUN])
def test_business_time_weekend(day):
    for h, m in [(0, 0), (8, 0), (12, 0), (15, 59), (16, 0)]:
        assert s.is_business_time(at(day, h, m)) is False


def test_business_time_seconds_ignored():
    assert s.is_business_time(at(MON, 15, 59, 59, 999999)) is True
    assert s.is_business_time(at(MON, 7, 59, 59)) is False
    assert s.is_business_time(at(MON, 16, 0, 0, 1)) is False
    assert s.is_business_time(at(MON, 8, 0, 0)) is True


def test_business_time_returns_bool():
    assert s.is_business_time(at(MON, 9)) is True
    assert s.is_business_time(at(MON, 20)) is False


# ---------- add_business_minutes ----------
def test_add_simple():
    assert s.add_business_minutes(at(MON, 9), 30) == at(MON, 9, 30)
    assert s.add_business_minutes(at(MON, 9), 1) == at(MON, 9, 1)
    assert s.add_business_minutes(at(MON, 8), 60) == at(MON, 9)
    assert s.add_business_minutes(at(MON, 9, 45), 30) == at(MON, 10, 15)


def test_add_zero():
    assert s.add_business_minutes(at(MON, 9, 17), 0) == at(MON, 9, 17)
    assert s.add_business_minutes(at(MON, 8), 0) == at(MON, 8)
    assert s.add_business_minutes(at(MON, 15, 59), 0) == at(MON, 15, 59)
    assert s.add_business_minutes(at(MON, 7), 0) == at(MON, 8)
    assert s.add_business_minutes(at(MON, 16), 0) == at(MON + timedelta(1), 8)
    assert s.add_business_minutes(at(FRI, 16), 0) == at(MON + timedelta(7), 8)
    assert s.add_business_minutes(at(SAT, 10), 0) == at(MON + timedelta(7), 8)
    assert s.add_business_minutes(at(SUN, 10), 0) == at(MON + timedelta(7), 8)


def test_add_ends_exactly_at_closing():
    assert s.add_business_minutes(at(MON, 15), 60) == at(MON, 16)
    assert s.add_business_minutes(at(MON, 8), 480) == at(MON, 16)
    assert s.add_business_minutes(at(FRI, 8), 480) == at(FRI, 16)
    assert s.add_business_minutes(at(MON, 15, 59), 1) == at(MON, 16)


def test_add_rolls_over_closing():
    assert s.add_business_minutes(at(MON, 15), 61) == at(MON + timedelta(1), 8, 1)
    assert s.add_business_minutes(at(MON, 15, 59), 2) == at(MON + timedelta(1), 8, 1)
    assert s.add_business_minutes(at(MON, 15), 90) == at(MON + timedelta(1), 8, 30)
    assert s.add_business_minutes(at(MON, 8), 481) == at(MON + timedelta(1), 8, 1)
    assert s.add_business_minutes(at(MON, 8), 960) == at(MON + timedelta(1), 16)
    assert s.add_business_minutes(at(MON, 8), 961) == at(MON + timedelta(2), 8, 1)


def test_add_over_weekend():
    assert s.add_business_minutes(at(FRI, 15), 120) == at(MON + timedelta(7), 9)
    assert s.add_business_minutes(at(FRI, 15), 60) == at(FRI, 16)
    assert s.add_business_minutes(at(FRI, 15), 61) == at(MON + timedelta(7), 8, 1)
    assert s.add_business_minutes(at(FRI, 8), 481) == at(MON + timedelta(7), 8, 1)
    assert s.add_business_minutes(at(FRI, 8), 960) == at(MON + timedelta(7), 16)
    assert s.add_business_minutes(at(FRI, 8), 5 * 480) == at(FRI + timedelta(6), 16)


def test_add_start_before_opening():
    assert s.add_business_minutes(at(MON, 7, 30), 10) == at(MON, 8, 10)
    assert s.add_business_minutes(at(MON, 0, 0), 10) == at(MON, 8, 10)
    assert s.add_business_minutes(at(MON, 7, 59), 480) == at(MON, 16)
    assert s.add_business_minutes(at(MON, 7, 59), 481) == at(MON + timedelta(1), 8, 1)


def test_add_start_after_closing():
    assert s.add_business_minutes(at(MON, 16), 10) == at(MON + timedelta(1), 8, 10)
    assert s.add_business_minutes(at(MON, 20), 10) == at(MON + timedelta(1), 8, 10)
    assert s.add_business_minutes(at(MON, 23, 59), 1) == at(MON + timedelta(1), 8, 1)
    assert s.add_business_minutes(at(MON, 16), 480) == at(MON + timedelta(1), 16)
    assert s.add_business_minutes(at(FRI, 17), 10) == at(MON + timedelta(7), 8, 10)


def test_add_start_on_weekend():
    for d in (SAT, SUN):
        for h in (0, 7, 9, 17):
            assert s.add_business_minutes(at(d, h), 10) == at(MON + timedelta(7), 8, 10)
        assert s.add_business_minutes(at(d, 9), 480) == at(MON + timedelta(7), 16)
        assert s.add_business_minutes(at(d, 9), 481) == at(MON + timedelta(8), 8, 1)


def test_add_seconds_ignored():
    assert s.add_business_minutes(at(MON, 9, 0, 59, 999), 5) == at(MON, 9, 5)
    assert s.add_business_minutes(at(MON, 9, 7, 30), 0) == at(MON, 9, 7)
    assert s.add_business_minutes(at(MON, 15, 59, 59), 1) == at(MON, 16)


def test_add_many_days():
    # 10 business days of 480 minutes from Monday 08:00 -> Friday of next week, 16:00
    assert s.add_business_minutes(at(MON, 8), 4800) == at(FRI + timedelta(7), 16)
    assert s.add_business_minutes(at(MON, 8), 4801) == at(MON + timedelta(14), 8, 1)
    assert s.add_business_minutes(at(MON, 10), 1440) == at(MON + timedelta(3), 10)


def test_add_negative():
    with pytest.raises(ValueError):
        s.add_business_minutes(at(MON, 9), -1)
    with pytest.raises(ValueError):
        s.add_business_minutes(at(SAT, 9), -5)


def test_add_max_days_limit():
    start = at(MON, 8)
    ok_end = at(MON + timedelta(366), 16)  # a Wednesday, 366 days after the start's date
    assert ok_end.weekday() < 5
    n = s.business_minutes_between(start, ok_end)
    assert s.add_business_minutes(start, n) == ok_end
    with pytest.raises(ValueError):
        s.add_business_minutes(start, n + 1)
    with pytest.raises(ValueError):
        s.add_business_minutes(start, n + 5000)
    mid = at(MON + timedelta(366), 12)
    m2 = s.business_minutes_between(start, mid)
    assert s.add_business_minutes(start, m2) == mid


def test_add_max_days_limit_from_later_time():
    start = at(MON, 15)
    ok_end = at(MON + timedelta(366), 8, 1)
    n = s.business_minutes_between(start, ok_end)
    assert s.add_business_minutes(start, n) == ok_end


def test_add_zero_from_weekend_beyond_nothing():
    assert s.add_business_minutes(at(SAT, 12), 1) == at(MON + timedelta(7), 8, 1)


# ---------- business_minutes_between ----------
def test_between_basic():
    assert s.business_minutes_between(at(MON, 9), at(MON, 9)) == 0
    assert s.business_minutes_between(at(MON, 9), at(MON, 9, 1)) == 1
    assert s.business_minutes_between(at(MON, 9), at(MON, 12)) == 180
    assert s.business_minutes_between(at(MON, 8), at(MON, 16)) == 480
    assert s.business_minutes_between(at(MON, 0), at(MON, 23, 59)) == 480
    assert s.business_minutes_between(at(MON, 0), at(MON + timedelta(1), 0)) == 480


def test_between_zero_outside_hours():
    assert s.business_minutes_between(at(MON, 7), at(MON, 8)) == 0
    assert s.business_minutes_between(at(MON, 16), at(MON, 20)) == 0
    assert s.business_minutes_between(at(MON, 16), at(MON + timedelta(1), 8)) == 0
    assert s.business_minutes_between(at(SAT, 0), at(SUN, 23, 59)) == 0
    assert s.business_minutes_between(at(FRI, 16), at(MON + timedelta(7), 8)) == 0
    assert s.business_minutes_between(at(SAT, 10), at(SAT, 10)) == 0


def test_between_half_open():
    assert s.business_minutes_between(at(MON, 15, 59), at(MON, 16)) == 1
    assert s.business_minutes_between(at(MON, 7, 59), at(MON, 8, 1)) == 1
    assert s.business_minutes_between(at(MON, 8), at(MON, 8, 1)) == 1
    assert s.business_minutes_between(at(MON, 16), at(MON, 16, 1)) == 0
    assert s.business_minutes_between(at(MON, 15, 59), at(MON + timedelta(1), 8)) == 1


def test_between_multi_day():
    assert s.business_minutes_between(at(MON, 15), at(MON + timedelta(1), 9)) == 120
    assert s.business_minutes_between(at(MON, 8), at(MON + timedelta(2), 16)) == 1440
    assert s.business_minutes_between(at(MON, 8), at(MON + timedelta(2), 8)) == 960
    assert s.business_minutes_between(at(MON, 9), at(MON + timedelta(2), 15)) == 420 + 480 + 420


def test_between_weekend_skipped():
    assert s.business_minutes_between(at(FRI, 15), at(MON + timedelta(7), 9)) == 120
    assert s.business_minutes_between(at(FRI, 8), at(MON + timedelta(7), 8)) == 480
    assert s.business_minutes_between(at(SAT, 9), at(MON + timedelta(7), 9)) == 60
    assert s.business_minutes_between(at(SUN, 9), at(MON + timedelta(7), 9)) == 60
    assert s.business_minutes_between(at(FRI, 9), at(SAT, 12)) == 420
    assert s.business_minutes_between(at(MON, 8), at(MON + timedelta(7), 8)) == 5 * 480
    assert s.business_minutes_between(at(MON, 8), at(MON + timedelta(14), 8)) == 10 * 480
    assert s.business_minutes_between(at(MON, 0), at(MON + timedelta(6), 0)) == 5 * 480


def test_between_seconds_ignored():
    assert s.business_minutes_between(at(MON, 9, 0, 59), at(MON, 9, 1, 0)) == 1
    assert s.business_minutes_between(at(MON, 9, 0, 0), at(MON, 9, 0, 59, 5)) == 0
    assert s.business_minutes_between(at(MON, 9, 0, 30), at(MON, 9, 1, 29)) == 1
    assert s.business_minutes_between(at(MON, 9, 0, 59), at(MON, 9, 0, 0)) == 0


def test_between_end_before_start():
    with pytest.raises(ValueError):
        s.business_minutes_between(at(MON, 9, 1), at(MON, 9))
    with pytest.raises(ValueError):
        s.business_minutes_between(at(MON + timedelta(1), 9), at(MON, 9))
    with pytest.raises(ValueError):
        s.business_minutes_between(at(SAT, 12), at(SAT, 11))


def test_between_end_before_start_same_minute_seconds_ok():
    # after truncation to minutes the two are equal, so this is not "end before start"
    assert s.business_minutes_between(at(MON, 9, 0, 40), at(MON, 9, 0, 10)) == 0


def test_between_max_days():
    start = at(MON, 8)
    assert s.business_minutes_between(start, at(MON + timedelta(366), 16)) > 0
    with pytest.raises(ValueError):
        s.business_minutes_between(start, at(MON + timedelta(367), 16))
    with pytest.raises(ValueError):
        s.business_minutes_between(start, at(MON + timedelta(367), 0))
    # the limit is counted in calendar dates, not in 24-hour spans
    assert s.business_minutes_between(at(MON, 23, 59), at(MON + timedelta(366), 0, 0)) >= 0
    assert s.business_minutes_between(at(MON, 0, 0), at(MON + timedelta(366), 23, 59)) > 0
    with pytest.raises(ValueError):
        s.business_minutes_between(at(MON, 23, 59), at(MON + timedelta(367), 0, 0))
    with pytest.raises(ValueError):
        s.business_minutes_between(at(MON, 0, 0), at(MON + timedelta(367), 23, 59))


def test_between_long_exact_value():
    # 366 days after a Monday: 52 full weeks (260 business days) plus Mon and Tue and Wed
    start = at(MON, 8)
    end = at(MON + timedelta(366), 16)
    assert s.business_minutes_between(start, end) == (260 + 3) * 480


@pytest.mark.parametrize("start", [
    at(MON, 8), at(MON, 9, 13), at(MON, 15, 59), at(MON, 16), at(MON, 7), at(FRI, 15, 30), at(FRI, 17),
    at(SAT, 10), at(SUN, 23, 59), at(MON, 0), at(MON + timedelta(3), 12, 7),
])
@pytest.mark.parametrize("minutes", [0, 1, 59, 60, 479, 480, 481, 960, 1000, 2400, 2401, 10000])
def test_roundtrip(start, minutes):
    due = s.add_business_minutes(start, minutes)
    assert s.business_minutes_between(start, due) == minutes
    assert due >= start


def test_roundtrip_all_minutes_in_a_day_span():
    start = at(FRI, 14, 30)
    prev = start
    for n in range(0, 1100, 7):
        due = s.add_business_minutes(start, n)
        assert s.business_minutes_between(start, due) == n
        assert due >= prev
        prev = due


# ---------- escalation_tier ----------
@pytest.mark.parametrize("p,base", [("P1", 1), ("P2", 1), ("P3", 0), ("P4", 0)])
def test_escalation_base(p, base):
    assert s.escalation_tier(p, False, 0) == base
    assert s.escalation_tier(p, False, 1) == base


def test_escalation_table():
    expected = {}
    for p in ("P1", "P2", "P3", "P4"):
        for breached in (False, True):
            for reopens in (0, 1, 2, 3, 10):
                t = 1 if p in ("P1", "P2") else 0
                if breached:
                    t += 2 if p == "P1" else 1
                if reopens >= 2:
                    t += 1
                expected[(p, breached, reopens)] = min(t, 3)
    for (p, b, r), e in expected.items():
        assert s.escalation_tier(p, b, r) == e, (p, b, r)


@pytest.mark.parametrize("p,b,r,e", [
    ("P1", True, 0, 3), ("P1", True, 2, 3), ("P1", False, 2, 2), ("P2", True, 0, 2), ("P2", True, 2, 3),
    ("P2", False, 2, 2), ("P3", True, 0, 1), ("P3", True, 2, 2), ("P3", False, 2, 1), ("P3", False, 1, 0),
    ("P4", True, 0, 1), ("P4", True, 5, 2), ("P4", False, 100, 1), ("P1", False, 0, 1), ("P1", False, 1, 1),
])
def test_escalation_cases(p, b, r, e):
    assert s.escalation_tier(p, b, r) == e


def test_escalation_truthy_breached():
    assert s.escalation_tier("P3", 1, 0) == 1
    assert s.escalation_tier("P3", 0, 0) == 0


@pytest.mark.parametrize("p", ["p1", "P5", "", " P1", "P0", "P1 "])
def test_escalation_unknown_priority(p):
    with pytest.raises(ValueError):
        s.escalation_tier(p, False, 0)
    with pytest.raises(ValueError):
        s.escalation_tier(p, True, 5)


@pytest.mark.parametrize("p", ["P1", "P2", "P3", "P4"])
def test_escalation_negative_reopens(p):
    with pytest.raises(ValueError):
        s.escalation_tier(p, False, -1)
    with pytest.raises(ValueError):
        s.escalation_tier(p, True, -10)


# ---------- parse_duration ----------
@pytest.mark.parametrize("text,minutes", [
    ("90m", 90), ("1m", 1), ("59m", 59), ("60m", 60), ("61m", 61), ("100m", 100), ("4h", 240), ("1h", 60),
    ("1h30m", 90), ("1h59m", 119), ("2d", 2880), ("1d", 1440), ("1d4h", 1680), ("1d0h5m", 1445),
    ("0h60m", 60), ("0d60m", 60), ("0d0h60m", 60), ("0d1h", 60), ("0h1m", 1), ("1d1m", 1441),
    ("2d3h4m", 2 * 1440 + 3 * 60 + 4), ("  90m", 90), ("90m  ", 90), ("\t1h\n", 60), (" 2d3h ", 2 * 1440 + 180),
    ("10d", 14400), ("12h", 720), ("24h", 1440), ("100h", 6000), ("007m", 7), ("01h", 60), ("0d1m", 1),
    ("1d59m", 1499), ("3h0m", 180), ("1d0m", 1440), ("2h5m", 125), ("1h01m", 61),
])
def test_parse_valid(text, minutes):
    assert s.parse_duration(text) == minutes


@pytest.mark.parametrize("text", [
    "", " ", "0m", "0h", "0d", "0d0h0m", "00m", "1.5h", "30m1h", "-5m", "+5m", "1 h", "1h 30m", "1d 4h",
    "1h60m", "1h61m", "1h99m", "1d60m", "1d0h60m", "2d90m", "1d1h60m", "1H", "1D", "5M", "90", "h", "m", "d",
    "1hh", "1h1h", "1m1m", "1d1d", "1m30s", "1w", "5 m", "abc", "1h30", "m5", "1h-5m", "1,5h", "1h30m5", "1h30mx",
    "x1h", "1d2h3m4m", "4h1d", "30m1h", "1m1d", "1h1d", "\u00a0", "1h\u00a030m",
])
def test_parse_invalid(text):
    with pytest.raises(ValueError):
        s.parse_duration(text)


def test_parse_returns_int():
    assert type(s.parse_duration("1h")) is int
