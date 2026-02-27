from datetime import date, timedelta


def resolve_time_window(time_window: str) -> tuple[date | None, date | None]:
    """Return (start_date, end_date) for the given time-window key."""
    today = date.today()

    if time_window == "last_7_days":
        return (today - timedelta(days=7), today)
    elif time_window == "last_30_days":
        return (today - timedelta(days=30), today)
    elif time_window == "this_month":
        return (today.replace(day=1), today)
    elif time_window == "this_year":
        return (today.replace(month=1, day=1), today)
    elif time_window == "all_time":
        return (None, None)
    else:
        return (None, None)
