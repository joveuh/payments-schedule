"""Run: python test_main.py"""

from datetime import date

from main import Txn, add_months, build_schedule, make_txn, occurrences, parse_csv

TODAY = date(2026, 1, 1)


def txn(freq, start, end=None, amount=100, operation="out"):
    return Txn(operation, freq, amount, start, end, "test")


def dates(freq, start, until, end=None):
    return list(occurrences(txn(freq, start, end), until))


def test_month_end_does_not_drift():
    # The old code added the current month's length, so Jan 31 + 31d = Mar 3 and
    # February was skipped entirely. Each occurrence is measured from the anchor.
    got = dates("M", date(2026, 1, 31), date(2026, 6, 1))
    assert got == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
        date(2026, 5, 31),
    ], got


def test_leap_year():
    assert date(2028, 2, 29) in dates("M", date(2028, 1, 29), date(2028, 4, 1))
    assert add_months(date(2028, 2, 29), 12) == date(2029, 2, 28)


def test_monthly_keeps_day_of_month():
    got = dates("M", date(2026, 1, 15), date(2026, 4, 1))
    assert got == [date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15)], got


def test_quarterly_biyearly_yearly():
    assert dates("Q", date(2026, 1, 15), date(2027, 1, 1)) == [
        date(2026, 1, 15),
        date(2026, 4, 15),
        date(2026, 7, 15),
        date(2026, 10, 15),
    ]
    assert dates("BY", date(2026, 1, 15), date(2027, 1, 1)) == [
        date(2026, 1, 15),
        date(2026, 7, 15),
    ]
    assert dates("Y", date(2026, 1, 15), date(2028, 1, 1)) == [
        date(2026, 1, 15),
        date(2027, 1, 15),
    ]


def test_weekly_biweekly_daily():
    assert dates("W", date(2026, 1, 1), date(2026, 1, 22)) == [
        date(2026, 1, 1),
        date(2026, 1, 8),
        date(2026, 1, 15),
    ]
    assert dates("B", date(2026, 1, 1), date(2026, 2, 1)) == [
        date(2026, 1, 1),
        date(2026, 1, 15),
        date(2026, 1, 29),
    ]
    assert len(dates("D", date(2026, 1, 1), date(2026, 1, 11))) == 10


def test_semiweekly_lands_on_mondays_and_thursdays():
    got = dates("SW", date(2026, 1, 5), date(2026, 1, 20))  # 2026-01-05 is a Monday
    assert all(d.weekday() in (0, 3) for d in got), got
    assert got == [
        date(2026, 1, 5),
        date(2026, 1, 8),
        date(2026, 1, 12),
        date(2026, 1, 15),
        date(2026, 1, 19),
    ], got


def test_one_time_fires_once():
    assert dates("O", date(2026, 3, 1), date(2027, 1, 1)) == [date(2026, 3, 1)]


def test_end_date_stops_recurrence_and_is_inclusive():
    got = dates("M", date(2026, 1, 15), date(2027, 1, 1), end=date(2026, 3, 15))
    assert got == [date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15)], got


def test_end_date_before_start_means_no_end():
    # The 1970-01-01 sentinel: taken literally it would silence every payment.
    t = make_txn("out", "M", 100, "2026-01-15", "1970-01-01")
    assert t.end is None
    assert len(list(occurrences(t, date(2026, 6, 1)))) == 5


def test_balance_accumulates_and_past_payments_are_excluded():
    txns = [
        make_txn("in", "M", 1000, "2025-06-01", ""),  # started before TODAY
        make_txn("out", "M", 400, "2026-01-01", ""),
    ]
    schedule = build_schedule(txns, 40, today=TODAY)
    assert schedule[0].date == TODAY
    assert schedule[0].total == 600  # 1000 in, 400 out, both land on the 1st
    assert schedule[0].balance == 600
    assert len(schedule) == 40  # Jan 1 .. Feb 9, so Feb 1 recurs once more
    assert schedule[31].date == date(2026, 2, 1)
    assert schedule[31].total == 600
    assert schedule[-1].balance == 1200


def test_opening_balance_seeds_the_running_balance():
    txns = [make_txn("out", "O", 100, "2026-01-05", "")]
    schedule = build_schedule(txns, 10, today=TODAY, opening=250)
    assert schedule[0].balance == 250  # before anything lands
    assert schedule[4].balance == 150  # the one-time bites on the 5th
    assert build_schedule(txns, 10, today=TODAY)[0].balance == 0  # defaults to zero


def test_opening_balance_may_be_negative():
    # An overdrawn account is a real starting state; unlike an amount, this is signed.
    schedule = build_schedule(
        [make_txn("in", "O", 50, "2026-01-02", "")], 5, today=TODAY, opening=-300
    )
    assert schedule[0].balance == -300
    assert schedule[1].balance == -250


def test_opening_balance_rejects_nonsense():
    txns = [make_txn("in", "M", 1, "2026-01-01", "")]
    for bad in ("abc", None, float("nan"), float("inf")):
        try:
            build_schedule(txns, 10, today=TODAY, opening=bad)
        except ValueError:
            continue
        raise AssertionError(f"should have been rejected: opening={bad!r}")


def test_rejects_bad_input():
    for bad in [
        ("sideways", "M", 100, "2026-01-01", ""),  # not in/out
        ("in", "ZZ", 100, "2026-01-01", ""),  # unknown frequency; used to hang
        ("in", "M", "abc", "2026-01-01", ""),  # not a number
        ("in", "M", -5, "2026-01-01", ""),  # negative
        ("in", "M", 100, "01/01/2026", ""),  # wrong date format
    ]:
        try:
            make_txn(*bad)
        except ValueError:
            continue
        raise AssertionError(f"should have been rejected: {bad}")


def test_days_is_bounded():
    t = [make_txn("in", "M", 1, "2026-01-01", "")]
    for bad_days in (0, -1, 10_000_000):
        try:
            build_schedule(t, bad_days, today=TODAY)
        except ValueError:
            continue
        raise AssertionError(f"should have been rejected: days={bad_days}")


def test_parse_csv_reads_description_and_skips_header():
    txns = parse_csv(
        [
            ["operation", "frequency", "amount", "startDate", "endDate"],
            [],
            ["in", "B", " 3000", " 2024-10-01", " 2025-10-01 # PAY"],
        ]
    )
    assert len(txns) == 1
    assert txns[0] == Txn(
        "in", "B", 3000.0, date(2024, 10, 1), date(2025, 10, 1), "PAY"
    )


def test_four_column_csv_fails_loudly():
    try:
        parse_csv([["in", "B", "3000", "2024-10-01 # PAY"]])
    except ValueError as e:
        assert "expected 5 columns" in str(e), e
        return
    raise AssertionError("4-column row should have been rejected")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} passed")
