"""Shelf-life logic: how long each food type stays safe, and how urgent a donation is."""

# Conservative safe-hours by category (food-safety rule of thumb)
SAFE_HOURS = {"cooked": 4, "dairy": 8, "bakery": 24, "produce": 48, "packaged": 240}


def safe_hours(category: str) -> int:
    return SAFE_HOURS.get(category, 4)


def hours_left(expiry, now) -> float:
    return (expiry - now).total_seconds() / 3600


def urgency_level(hours: float) -> str:
    if hours <= 0:
        return "expired"
    if hours <= 2:
        return "critical"
    if hours <= 6:
        return "high"
    if hours <= 24:
        return "medium"
    return "low"


def urgency_score(hours: float) -> float:
    """0 (plenty of time) to 1 (about to spoil). Used to weight the matcher."""
    return max(0.0, min(1.0, 1 - hours / 12))