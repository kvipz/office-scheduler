"""Core scheduling logic — no I/O. Imported by app.py."""

import calendar
import datetime

_MANDATORY_THRESHOLDS = [
    (9.5, 6), (7.5, 7), (6.0, 8), (4.0, 9),
    (2.5, 10), (1.0, 11), (0.0, 12),
]

# Soft weekday preferences (0=Mon … 6=Sun). "Good to have but not mandatory" —
# explicit Planning to Go choices (Yes = office, No = WFH) always take priority.
VIPIN_PREFERRED_WEEKDAYS   = {0, 2, 4}  # Mon, Wed, Fri
HIMANGI_PREFERRED_WEEKDAYS = {1, 3, 4}  # Tue, Thu, Fri


def mandatory_days(total_absent: float) -> int:
    for threshold, days in _MANDATORY_THRESHOLDS:
        if total_absent >= threshold:
            return days
    return 12


def working_days_in_month(year: int, month: int, holiday_dates=None) -> list:
    holidays = set(holiday_dates or [])
    _, last_day = calendar.monthrange(year, month)
    return [
        datetime.date(year, month, d)
        for d in range(1, last_day + 1)
        if datetime.date(year, month, d).weekday() < 5
        and datetime.date(year, month, d) not in holidays
    ]


def _pick_evenly(pool: list, n: int) -> list:
    if n <= 0 or not pool:
        return []
    if n >= len(pool):
        return list(pool)
    step = len(pool) / n
    return [pool[int(i * step)] for i in range(n)]


def _pick_with_preference(pool: list, n: int, preferred_weekdays: set) -> list:
    """Pick n days from pool, favouring days whose weekday is in preferred_weekdays.
    Falls back to evenly-spaced picks from the rest of the pool when there
    aren't enough preferred days to cover n."""
    if n <= 0 or not pool:
        return []
    if n >= len(pool):
        return list(pool)
    preferred = [d for d in pool if d.weekday() in preferred_weekdays]
    other     = [d for d in pool if d.weekday() not in preferred_weekdays]
    if len(preferred) >= n:
        return _pick_evenly(preferred, n)
    rest = _pick_evenly(other, n - len(preferred))
    return sorted(preferred + rest)


def _schedule(remaining_days, vipin_blocked, himangi_blocked, vipin_need, himangi_need):
    """
    Assign office days minimising overlap.
    Forced overlaps go on Fridays first, then other days.
    vipin_blocked / himangi_blocked: dates each person cannot/will-not attend
    (leave days plus any "Work from home" preference days).
    """
    vipin_avail  = sorted(d for d in remaining_days if d not in vipin_blocked)
    himangi_avail = sorted(d for d in remaining_days if d not in himangi_blocked)
    both_avail   = sorted(d for d in remaining_days if d not in vipin_blocked and d not in himangi_blocked)

    # Minimum forced overlap (derived from capacity constraints)
    fo = vipin_need + himangi_need - len(vipin_avail) - len(himangi_avail) + len(both_avail)
    cap = min(vipin_need, himangi_need) if (vipin_need and himangi_need) else 0
    forced_overlap = max(0, min(fo, cap, len(both_avail)))

    # Pick overlap days: Fridays first
    both_sorted = sorted(both_avail, key=lambda d: (d.weekday() != 4, d))
    overlap = both_sorted[:forced_overlap]
    overlap_set = set(overlap)

    vipin_days   = set(overlap)
    himangi_days = set(overlap)
    v_remain = vipin_need   - forced_overlap
    h_remain = himangi_need - forced_overlap

    v_only = [d for d in vipin_avail  if d not in set(himangi_avail)]
    h_only = [d for d in himangi_avail if d not in set(vipin_avail)]
    both_remain = [d for d in both_avail if d not in overlap_set]

    # Each person exhausts their exclusive pool first, then draws from both_remain.
    # This prevents Vipin from consuming shared days that Himangi needs.
    v_from_excl = min(v_remain, len(v_only))
    h_from_excl = min(h_remain, len(h_only))
    v_from_both = v_remain - v_from_excl
    h_from_both = h_remain - h_from_excl

    for d in _pick_with_preference(v_only, v_from_excl, VIPIN_PREFERRED_WEEKDAYS):
        vipin_days.add(d)
    for d in _pick_with_preference(h_only, h_from_excl, HIMANGI_PREFERRED_WEEKDAYS):
        himangi_days.add(d)

    # Split both_remain: Himangi picks first (favouring her preferred weekdays),
    # Vipin gets the rest. This guarantees Himangi always finds enough days
    # even when she needs more.
    h_both_days = set(_pick_with_preference(both_remain, h_from_both, HIMANGI_PREFERRED_WEEKDAYS))
    v_both_pool = [d for d in both_remain if d not in h_both_days]
    for d in h_both_days:
        himangi_days.add(d)
    for d in _pick_with_preference(v_both_pool, v_from_both, VIPIN_PREFERRED_WEEKDAYS):
        vipin_days.add(d)

    return sorted(vipin_days), sorted(himangi_days)


def compute(
    month: int,
    year: int,
    holiday_days=None,          # list of day-of-month ints
    vipin_leave_days=None,      # list of day-of-month ints
    himangi_leave_days=None,
    vipin_attended_days=None,   # list of day-of-month ints (past days attended)
    himangi_attended_days=None,
    vipin_planned_days=None,    # list of day-of-month ints (future committed office days)
    himangi_planned_days=None,
    vipin_wfh_days=None,        # list of day-of-month ints (future WFH preference days)
    himangi_wfh_days=None,
    vipin_done_manual: int = 0,
    himangi_done_manual: int = 0,
) -> dict:
    today = datetime.date.today()
    _, last_day = calendar.monthrange(year, month)

    def to_dates(day_nums, weekdays_only=True):
        dates = set()
        for d in (day_nums or []):
            try:
                dt = datetime.date(year, month, int(d))
                if not weekdays_only or dt.weekday() < 5:
                    dates.add(dt)
            except (ValueError, TypeError):
                pass
        return dates

    hol_dates  = to_dates(holiday_days)
    v_leave    = to_dates(vipin_leave_days)   - hol_dates
    h_leave    = to_dates(himangi_leave_days) - hol_dates
    v_attended = to_dates(vipin_attended_days)
    h_attended = to_dates(himangi_attended_days)

    all_working       = working_days_in_month(year, month, hol_dates)
    all_working_set   = set(all_working)
    past_working      = [d for d in all_working if d < today]
    remaining_working = [d for d in all_working if d > today]   # today is not schedulable
    remaining_set     = set(remaining_working)

    # Absent count = holiday weekdays + personal leave weekdays (non-holiday)
    vipin_absent   = len(hol_dates) + len(v_leave)
    himangi_absent = len(hol_dates) + len(h_leave)

    vipin_mandatory   = mandatory_days(vipin_absent)
    himangi_mandatory = mandatory_days(himangi_absent)

    # Done: calendar attendance supersedes manual when any days are marked
    v_done_cal = len(v_attended & all_working_set)
    h_done_cal = len(h_attended & all_working_set)
    vipin_done   = max(v_done_cal, vipin_done_manual)
    himangi_done = max(h_done_cal, himangi_done_manual)
    vipin_done   = min(vipin_done,   vipin_mandatory)
    himangi_done = min(himangi_done, himangi_mandatory)

    vipin_need   = max(0, vipin_mandatory   - vipin_done)
    himangi_need = max(0, himangi_mandatory - himangi_done)

    # Planned (user-committed) future office days — filtered to valid working days
    v_planned = (to_dates(vipin_planned_days)   - v_leave - hol_dates) & remaining_set
    h_planned = (to_dates(himangi_planned_days) - h_leave - hol_dates) & remaining_set

    # WFH preference days — person does not want to be scheduled in office on
    # these future working days (a personal choice, not an absence/leave).
    v_wfh = to_dates(vipin_wfh_days)   & remaining_set
    h_wfh = to_dates(himangi_wfh_days) & remaining_set

    # Lock planned days first; schedule only the remaining gap
    v_still_need = max(0, vipin_need   - len(v_planned))
    h_still_need = max(0, himangi_need - len(h_planned))

    # Additional days are scheduled from days not already committed by either person
    already_planned = v_planned | h_planned
    days_for_algo   = [d for d in remaining_working if d not in already_planned]

    v_blocked = v_leave | v_wfh
    h_blocked = h_leave | h_wfh

    add_vipin, add_himangi = _schedule(days_for_algo, v_blocked, h_blocked, v_still_need, h_still_need)

    vipin_set   = v_planned | set(add_vipin)
    himangi_set = h_planned | set(add_himangi)
    overlap     = sorted(vipin_set & himangi_set)

    # Build assignment map — flag planned days so frontend can style them differently
    planned_dates = {d.isoformat() for d in v_planned | h_planned}
    assignment_map = {}
    for d in vipin_set | himangi_set:
        v, h = d in vipin_set, d in himangi_set
        assignment_map[d.isoformat()] = "both" if (v and h) else ("vipin" if v else "himangi")

    assigned = []
    for d in sorted(vipin_set | himangi_set):
        v, h = d in vipin_set, d in himangi_set
        assigned.append({
            "date":      d.isoformat(),
            "display":   d.strftime("%d %b %Y"),
            "weekday":   calendar.day_name[d.weekday()],
            "who":       "Both" if (v and h) else ("Vipin" if v else "Himangi"),
            "is_friday": d.weekday() == 4,
            "is_past":   d < today,
            "planned":   d.isoformat() in planned_dates,
        })

    return {
        "month":      month,
        "year":       year,
        "month_name": calendar.month_name[month],
        "today":      today.isoformat(),
        "total_working":     len(all_working),
        "past_working":      len(past_working),
        "remaining_working": len(remaining_working),
        "num_holidays":      len(hol_dates),
        "vipin": {
            "leaves":             len(v_leave),
            "absent":             vipin_absent,
            "mandatory":          vipin_mandatory,
            "done":               vipin_done,
            "done_from_calendar": v_done_cal > 0,
            "need":               vipin_need,
            "planned":            len(v_planned),
            "short": v_still_need > len([d for d in days_for_algo if d not in v_blocked]),
        },
        "himangi": {
            "leaves":             len(h_leave),
            "absent":             himangi_absent,
            "mandatory":          himangi_mandatory,
            "done":               himangi_done,
            "done_from_calendar": h_done_cal > 0,
            "need":               himangi_need,
            "planned":            len(h_planned),
            "short": h_still_need > len([d for d in days_for_algo if d not in h_blocked]),
        },
        "overlap_count":      len(overlap),
        "overlap_on_fridays": sum(1 for d in overlap if d.weekday() == 4),
        "planned_dates":      sorted(planned_dates),
        "assignment_map":     assignment_map,
        "assigned":           assigned,
    }
