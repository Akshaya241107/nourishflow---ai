"""Smart matching: scores how well an NGO fits a donation (0-100)."""
import math
from .expiry import hours_left, urgency_score

AVG_SPEED_KMH = 25      # average road speed used for travel-time estimates
RADIUS_KM = 30          # beyond this distance the distance score is zero
BUFFER_MIN = 15         # NGO needs this much spare time on top of travel


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def score_match(donation, ngo, active_load_kg, now):
    dist = haversine_km(donation.latitude, donation.longitude, ngo.latitude, ngo.longitude)
    travel_min = dist / AVG_SPEED_KMH * 60
    h_left = hours_left(donation.expiry_time, now)
    urg = urgency_score(h_left)

    free = max(0.0, (ngo.capacity_kg or 0) - active_load_kg)
    accepted = [c for c in (ngo.accepted_categories or "").split(",") if c]
    accepts = donation.category in accepted
    fits = free >= donation.quantity_kg
    reachable = (travel_min + BUFFER_MIN) / 60 < h_left

    dist_s = max(0.0, 1 - dist / RADIUS_KM)
    cap_s = min(1.0, free / donation.quantity_kg) if donation.quantity_kg > 0 else 0.0
    cat_s = 1.0 if accepts else 0.0

    # The more urgent the food, the more distance matters.
    w_dist = 0.45 + 0.15 * urg
    w_cap = 0.30
    w_cat = 1 - w_dist - w_cap
    score = 100 * (w_dist * dist_s + w_cap * cap_s + w_cat * cat_s)
    if not accepts:
        score *= 0.4
    if not reachable:
        score *= 0.3

    reasons = [f"{dist:.1f} km away, about {round(travel_min)} min drive"]
    reasons.append(f"Accepts {donation.category} food" if accepts else f"Does not usually take {donation.category} food")
    reasons.append(f"Has room for {donation.quantity_kg:g} kg" if fits else f"Only {free:g} kg free right now")
    if not reachable:
        reasons.append("Cannot get there before the food expires")

    return {
        "score": round(score, 1),
        "distance_km": round(dist, 1),
        "travel_minutes": round(travel_min),
        "reachable": reachable,
        "accepts_category": accepts,
        "fits_capacity": fits,
        "reasons": reasons,
    }