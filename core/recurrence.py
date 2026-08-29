from datetime import date, datetime, time, timedelta

from dateutil.rrule import rrulestr


def _rule_start(rule, timezone):
    value = rule.get("dtstart")
    if value is None:
        return datetime(1970, 1, 1)
    if isinstance(value, datetime):
        start = value
    else:
        start = datetime.fromisoformat(value)
    if start.tzinfo is None:
        return start
    return start.astimezone(timezone).replace(tzinfo=None)


def rule_applies_on(rule, day, timezone):
    rrule_text = rule.get("rrule")
    if not rrule_text:
        return rule.get("weekday") == day.weekday()

    start = _rule_start(rule, timezone)
    recurrence = rrulestr(rrule_text, dtstart=start)
    day_start = datetime.combine(day, time.min)
    day_end = day_start + timedelta(days=1)
    if not recurrence.between(day_start, day_end, inc=True):
        return False

    excluded_dates = rule.get("exclude_dates") or []
    excluded = {date.fromisoformat(value) for value in excluded_dates}
    return day not in excluded