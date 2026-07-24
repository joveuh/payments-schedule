"""Project recurring income/expenses forward and show the running daily balance.

CSV format: operation,frequency,amount,startDate,endDate
The endDate cell may carry a description after a '#'. An empty endDate (or one
before startDate) means the payment recurs indefinitely.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import math
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from io import StringIO
from typing import Iterator, NamedTuple

DATE_FORMAT = "%Y-%m-%d"

# Bounds the schedule size: an unbounded `days` from the API would build a list
# big enough to exhaust memory.
MAX_DAYS = 3650

FREQUENCIES = {
    "Y": "Yearly",
    "BY": "Bi-Yearly",
    "Q": "Quarterly",
    "M": "Monthly",
    "B": "Bi-Weekly",
    "SW": "Semi-Weekly",
    "W": "Weekly",
    "D": "Daily",
    "O": "One-time",
}

# Month-based frequencies step whole calendar months; the rest are fixed offsets.
_MONTH_STEP = {"M": 1, "Q": 3, "BY": 6, "Y": 12}
_FIXED_STEP = {"D": timedelta(days=1), "W": timedelta(weeks=1), "B": timedelta(weeks=2)}

SAMPLE_CSV = """operation,frequency,amount,startDate,endDate
in,B, 3000, 2024-10-01, # PAY
out,M, 1500, 2024-10-01, # Rent
out,M, 500, 2024-10-15, # Car Insurance
out,B, 500, 2024-10-15, 2025-10-15 # Car Payment
out,M, 300, 2024-10-01, # Insurance
out,B, 100, 2024-10-05, # Gym
out,BY, 50, 2024-10-01, # Microsoft
out,W, 50, 2024-10-01, # Gas"""


class Txn(NamedTuple):
    operation: str  # "in" or "out"
    frequency: str
    amount: float
    start: date
    end: date | None  # None means it never stops
    description: str


class Day(NamedTuple):
    date: date
    items: list[tuple[str, float]]  # (description, signed amount)
    total: float
    balance: float


def add_months(anchor: date, months: int) -> date:
    """Anchor plus N calendar months, clamped to the target month's last day.

    Always measured from the anchor, never from the previous occurrence, so a
    payment on the 31st survives February: Jan 31 -> Feb 28 -> Mar 31.
    """
    total = anchor.month - 1 + months
    year, month = anchor.year + total // 12, total % 12 + 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return anchor.replace(year=year, month=month, day=day)


def next_semiweekly(d: date) -> date:
    """Next Monday or Thursday after d."""
    if d.weekday() == 0:  # Monday -> Thursday
        return d + timedelta(days=3)
    if d.weekday() == 3:  # Thursday -> Monday
        return d + timedelta(days=4)
    return d + timedelta(days=(7 - d.weekday()) % 7)  # otherwise snap to Monday


def occurrences(txn: Txn, until: date) -> Iterator[date]:
    """Every date txn falls on, from its start up to (but excluding) until."""
    stop = until
    if txn.end is not None and txn.end < until:
        stop = txn.end + timedelta(days=1)  # endDate is inclusive

    if txn.frequency == "O":
        if txn.start < stop:
            yield txn.start
        return

    if txn.frequency in _MONTH_STEP:
        months = _MONTH_STEP[txn.frequency]
        n = 0
        while (d := add_months(txn.start, n * months)) < stop:
            yield d
            n += 1
        return

    delta = _FIXED_STEP.get(txn.frequency)  # None for SW, which steps Mon/Thu
    d = txn.start
    while d < stop:
        yield d
        d = d + delta if delta else next_semiweekly(d)


def make_txn(operation, frequency, amount, start, end, description="") -> Txn:
    """Validate and build a Txn from raw strings. Shared by the CSV and JSON paths."""
    operation = str(operation).strip().lower()
    if operation not in ("in", "out"):
        raise ValueError(f"operation must be 'in' or 'out', got {operation!r}")

    frequency = str(frequency).strip().upper()
    if frequency not in FREQUENCIES:
        raise ValueError(
            f"unknown frequency {frequency!r}, expected one of {', '.join(FREQUENCIES)}"
        )

    try:
        amount = round(float(amount), 2)
    except (TypeError, ValueError):
        raise ValueError(f"amount must be a number, got {amount!r}") from None
    if not math.isfinite(amount) or amount < 0:
        raise ValueError(f"amount must be a positive number, got {amount!r}")

    start_date = _parse_date(start, "startDate")
    end_date = _parse_date(end, "endDate") if str(end).strip() else None
    # An end before the start can't mean anything sensible, so treat it as "no end".
    # This is also what tolerates the 1970-01-01 "never ends" sentinel.
    if end_date is not None and end_date < start_date:
        end_date = None

    return Txn(
        operation, frequency, amount, start_date, end_date, str(description).strip()
    )


def _parse_date(value, field: str) -> date:
    try:
        return datetime.strptime(str(value).strip(), DATE_FORMAT).date()
    except ValueError:
        raise ValueError(f"{field} must look like YYYY-MM-DD, got {value!r}") from None


def parse_row(row: list[str]) -> Txn:
    """One CSV row -> Txn. The endDate cell may carry '# description'."""
    if len(row) != 5:
        raise ValueError(
            "expected 5 columns (operation,frequency,amount,startDate,endDate), "
            f"got {len(row)}: {','.join(row)}"
        )
    operation, frequency, amount, start, end = (cell.strip() for cell in row)
    end, _, description = end.partition("#")
    return make_txn(operation, frequency, amount, start, end, description)


def parse_csv(rows: list[list[str]]) -> list[Txn]:
    txns = []
    for line_no, row in enumerate(rows, 1):
        if not row or not row[0].strip():
            continue  # blank line
        if row[0].strip().lower() == "operation":
            continue  # header
        try:
            txns.append(parse_row(row))
        except ValueError as e:
            raise ValueError(f"line {line_no}: {e}") from None
    if not txns:
        raise ValueError(
            "no transactions found: need a header line and at least one data line"
        )
    return txns


def parse_opening(value) -> float:
    """The balance the account starts at. Unlike an amount, this may be negative."""
    try:
        opening = round(float(value), 2)
    except (TypeError, ValueError):
        raise ValueError(f"opening balance must be a number, got {value!r}") from None
    if not math.isfinite(opening):
        raise ValueError(f"opening balance must be a real number, got {value!r}")
    return opening


def build_schedule(
    txns: list[Txn], days: int, today: date | None = None, opening: float = 0.0
) -> list[Day]:
    """Daily totals and running balance for the next `days` days."""
    if not 1 <= days <= MAX_DAYS:
        raise ValueError(f"days must be between 1 and {MAX_DAYS}, got {days}")

    today = today or date.today()
    until = today + timedelta(days=days)

    by_date: dict[date, list[tuple[str, float]]] = defaultdict(list)
    for txn in txns:
        signed = txn.amount if txn.operation == "in" else -txn.amount
        for d in occurrences(txn, until):
            if d >= today:  # occurrences before today are history, not schedule
                by_date[d].append((txn.description, signed))

    schedule, balance = [], parse_opening(opening)
    d = today
    while d < until:
        items = by_date.get(d, [])
        total = round(sum(amount for _, amount in items), 2)
        balance = round(balance + total, 2)
        schedule.append(Day(d, items, total, balance))
        d += timedelta(days=1)
    return schedule


def format_schedule(schedule: list[Day]) -> str:
    lines = []
    for day in schedule:
        date_str = f"Date: {day.date}"
        if day.items:
            payments = f"Payments: {[amount for _, amount in day.items]}"
            total = f"In/Out Total: {day.total}"
        else:
            payments = total = ""
        lines.append(
            f"{date_str:<20} {payments:<40} {total:<30} Balance: {day.balance}"
        )
    return "\n".join(lines)


def read_csv(path: str | None) -> list[list[str]]:
    if path is None:
        return list(csv.reader(StringIO(SAMPLE_CSV)))
    try:
        with open(path, newline="") as f:
            return list(csv.reader(f))
    except OSError as e:
        raise SystemExit(f"Could not read {path}: {e}") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "csvfile", nargs="?", help="CSV file (default: built-in sample)"
    )
    parser.add_argument(
        "days", nargs="?", type=int, default=100, help="days to project (default: 100)"
    )
    parser.add_argument("--save", action="store_true", help="also store to sqlite")
    parser.add_argument(
        "--opening",
        type=float,
        default=0.0,
        help="balance the account starts at (default: 0, may be negative)",
    )
    args = parser.parse_args(argv)

    rows = read_csv(args.csvfile)
    print("\nCSV contents:")
    print("\n".join(",".join(row) for row in rows))

    try:
        schedule = build_schedule(parse_csv(rows), args.days, opening=args.opening)
    except ValueError as e:
        raise SystemExit(f"Error: {e}") from None

    print("\nSummary of payments schedule")
    print(format_schedule(schedule))

    if args.save:
        from schedule_summary_db_ops import DB_Ops

        db = DB_Ops()
        db.create_table()
        db.insert_many([(d.date.isoformat(), d.total, d.balance) for d in schedule])
        db.close()
        print(f"\nSaved {len(schedule)} rows to the database.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
