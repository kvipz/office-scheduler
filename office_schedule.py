#!/usr/bin/env python3
"""
Office attendance scheduler for Vipin & Himangi.
Calculates mandatory office days and produces a calendar showing when each person should go.
"""

import calendar
import datetime
from typing import Optional

# Mandatory days step table: if total_absent >= threshold → mandatory = days
_MANDATORY_THRESHOLDS = [
    (9.5, 6), (7.5, 7), (6.0, 8), (4.0, 9),
    (2.5, 10), (1.0, 11), (0.0, 12),
]


def _mandatory_days(total_absent: float) -> int:
    for threshold, days in _MANDATORY_THRESHOLDS:
        if total_absent >= threshold:
            return days
    return 12


def _working_days_in_month(
    year: int, month: int, holiday_dates: Optional[list] = None
) -> list:
    holidays = set(holiday_dates or [])
    _, last_day = calendar.monthrange(year, month)
    return [
        datetime.date(year, month, d)
        for d in range(1, last_day + 1)
        if datetime.date(year, month, d).weekday() < 5
        and datetime.date(year, month, d) not in holidays
    ]


def _pick_evenly(pool: list, n: int) -> list:
    """Pick n evenly-spaced items from pool."""
    if n <= 0 or not pool:
        return []
    if n >= len(pool):
        return list(pool)
    step = len(pool) / n
    return [pool[int(i * step)] for i in range(n)]


def _schedule(remaining_days: list, vipin_need: int, himangi_need: int):
    """
    Assign remaining office days to Vipin and Himangi.
    - Minimise overlap.
    - When overlap is forced, prefer Fridays, then other days.
    """
    remaining_days = sorted(remaining_days)
    forced_overlap = max(0, vipin_need + himangi_need - len(remaining_days))

    fridays = [d for d in remaining_days if d.weekday() == 4]
    non_fridays = [d for d in remaining_days if d.weekday() != 4]

    # Assign overlap days (Fridays first)
    overlap = []
    for d in fridays:
        if len(overlap) >= forced_overlap:
            break
        overlap.append(d)
    for d in non_fridays:
        if len(overlap) >= forced_overlap:
            break
        overlap.append(d)

    overlap_set = set(overlap)
    vipin_days = set(overlap)
    himangi_days = set(overlap)

    vipin_need -= len(overlap)
    himangi_need -= len(overlap)

    # Available days for exclusive assignment
    exclusive = sorted(d for d in remaining_days if d not in overlap_set)

    # Alternate allocation: Vipin gets even-indexed, Himangi gets odd-indexed
    vipin_pool = [exclusive[i] for i in range(0, len(exclusive), 2)]
    himangi_pool = [exclusive[i] for i in range(1, len(exclusive), 2)]

    for d in _pick_evenly(vipin_pool, vipin_need):
        vipin_days.add(d)
    for d in _pick_evenly(himangi_pool, himangi_need):
        himangi_days.add(d)

    return sorted(vipin_days), sorted(himangi_days)


def _print_calendar(
    year: int,
    month: int,
    vipin_days: set,
    himangi_days: set,
    holiday_dates: set,
    today: datetime.date,
):
    month_name = calendar.month_name[month]
    header = f"  {'MON':>4} {'TUE':>4} {'WED':>4} {'THU':>4} {'FRI':>4} {'SAT':>4} {'SUN':>4}"
    print(f"\n{'─'*55}")
    print(f"  {month_name} {year}".center(55))
    print(f"{'─'*55}")
    print(f"  Legend:  V=Vipin  H=Himangi  B=Both  *=holiday/weekend")
    print(f"{'─'*55}")
    print(header)

    first_weekday, last_day = calendar.monthrange(year, month)  # Monday=0
    # first_weekday: 0=Mon ... 6=Sun
    cells = [""] * first_weekday  # padding before day 1
    for d in range(1, last_day + 1):
        date = datetime.date(year, month, d)
        if date.weekday() >= 5:
            cells.append(f"{d:2}*")
        elif date in holiday_dates:
            cells.append(f"{d:2}H*")
        else:
            v = date in vipin_days
            h = date in himangi_days
            marker = "B" if (v and h) else ("V" if v else ("H" if h else "  "))
            past = "<" if date < today else " "
            cells.append(f"{d:2}{marker}{past}")

    # Print in rows of 7
    print()
    row = []
    for i, cell in enumerate(cells):
        row.append(f"{cell:>5}")
        if (i + 1) % 7 == 0:
            print(" ", "  ".join(row))
            row = []
    if row:
        print(" ", "  ".join(row))
    print(f"{'─'*55}")


def run():
    today = datetime.date.today()

    # ── Inputs ──────────────────────────────────────────────────────────────
    print("=== Office Attendance Scheduler ===\n")

    month_input = input(f"Month number [{today.month}]: ").strip()
    month = int(month_input) if month_input else today.month

    year_input = input(f"Year [{today.year}]: ").strip()
    year = int(year_input) if year_input else today.year

    hol_count_input = input("Number of public holidays this month [0]: ").strip()
    num_holidays = int(hol_count_input) if hol_count_input else 0

    holiday_dates: list = []
    if num_holidays > 0:
        print(f"Enter {num_holidays} holiday date(s) as DD (space-separated), or press Enter to skip dates:")
        dates_input = input("> ").strip()
        if dates_input:
            for tok in dates_input.split():
                try:
                    holiday_dates.append(datetime.date(year, month, int(tok)))
                except ValueError:
                    print(f"  Skipping invalid date: {tok}")

    vipin_leaves_input = input("Vipin's leaves this month [0]: ").strip()
    vipin_leaves = float(vipin_leaves_input) if vipin_leaves_input else 0.0

    himangi_leaves_input = input("Himangi's leaves this month [0]: ").strip()
    himangi_leaves = float(himangi_leaves_input) if himangi_leaves_input else 0.0

    # ── Working days ─────────────────────────────────────────────────────────
    all_working = _working_days_in_month(year, month, holiday_dates)
    total_working = len(all_working)

    # Past working days (before today)
    past_working = [d for d in all_working if d < today]
    remaining_working = [d for d in all_working if d >= today]

    # ── Mandatory days ───────────────────────────────────────────────────────
    vipin_absent = num_holidays + vipin_leaves
    himangi_absent = num_holidays + himangi_leaves

    vipin_mandatory = _mandatory_days(vipin_absent)
    himangi_mandatory = _mandatory_days(himangi_absent)

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'═'*55}")
    print(f"  {calendar.month_name[month]} {year}  |  Total working days: {total_working}")
    print(f"{'─'*55}")
    print(f"  {'':20} {'Vipin':>10} {'Himangi':>10}")
    print(f"  {'Leaves':20} {vipin_leaves:>10.1f} {himangi_leaves:>10.1f}")
    print(f"  {'Public holidays':20} {num_holidays:>10}  {num_holidays:>9}")
    print(f"  {'Total absent':20} {vipin_absent:>10.1f} {himangi_absent:>10.1f}")
    print(f"  {'Mandatory office days':20} {vipin_mandatory:>10} {himangi_mandatory:>10}")
    print(f"{'═'*55}")

    # ── Days already completed ────────────────────────────────────────────────
    print(f"\nWorking days elapsed so far: {len(past_working)}")

    vipin_done_input = input(f"Vipin's office days completed (max {min(vipin_mandatory, len(past_working))}): ").strip()
    vipin_done = int(vipin_done_input) if vipin_done_input else 0
    vipin_done = min(vipin_done, vipin_mandatory)

    himangi_done_input = input(f"Himangi's office days completed (max {min(himangi_mandatory, len(past_working))}): ").strip()
    himangi_done = int(himangi_done_input) if himangi_done_input else 0
    himangi_done = min(himangi_done, himangi_mandatory)

    vipin_need = max(0, vipin_mandatory - vipin_done)
    himangi_need = max(0, himangi_mandatory - himangi_done)

    print(f"\n  {'':20} {'Vipin':>10} {'Himangi':>10}")
    print(f"  {'Completed':20} {vipin_done:>10} {himangi_done:>10}")
    print(f"  {'Still needed':20} {vipin_need:>10} {himangi_need:>10}")
    print(f"  {'Remaining work days':20} {len(remaining_working):>10}")

    if vipin_need > len(remaining_working):
        print(f"\n  ⚠  Vipin needs {vipin_need} more days but only {len(remaining_working)} working days remain!")
    if himangi_need > len(remaining_working):
        print(f"  ⚠  Himangi needs {himangi_need} more days but only {len(remaining_working)} working days remain!")

    # ── Schedule ──────────────────────────────────────────────────────────────
    vipin_days, himangi_days = _schedule(remaining_working, vipin_need, himangi_need)

    overlap = sorted(set(vipin_days) & set(himangi_days))
    if overlap:
        overlap_on_friday = [d for d in overlap if d.weekday() == 4]
        overlap_other = [d for d in overlap if d.weekday() != 4]
        print(f"\n  Both in office on: ", end="")
        for d in overlap:
            tag = " (Fri)" if d.weekday() == 4 else ""
            print(f"{d.strftime('%d %b')}{tag}", end="  ")
        print()

    # ── Calendar ─────────────────────────────────────────────────────────────
    _print_calendar(
        year, month,
        set(vipin_days), set(himangi_days),
        set(holiday_dates), today
    )

    # Day-by-day list
    print("\n  Scheduled office days:")
    print(f"  {'Date':<14} {'Day':<10} {'Who'}")
    print(f"  {'─'*36}")
    all_assigned = sorted(set(vipin_days) | set(himangi_days))
    for d in all_assigned:
        v = d in set(vipin_days)
        h = d in set(himangi_days)
        who = "Both" if (v and h) else ("Vipin" if v else "Himangi")
        past = " ✓" if d < today else ""
        print(f"  {d.strftime('%d %b %Y'):<14} {calendar.day_name[d.weekday()]:<10} {who}{past}")

    print()


if __name__ == "__main__":
    run()
