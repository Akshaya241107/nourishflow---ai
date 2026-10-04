from .ml.expiry import hours_left, urgency_level
from .models import utcnow
from .schemas import ALL_CATEGORIES

LIVE = ("posted", "claimed", "picked_up")


def user_out(u):
    cats = [c for c in (u.accepted_categories or "").split(",") if c] or list(ALL_CATEGORIES)
    return {
        "id": u.id, "name": u.name, "email": u.email, "role": u.role,
        "organization": u.organization or "", "latitude": u.latitude, "longitude": u.longitude,
        "capacity_kg": u.capacity_kg or 0, "accepted_categories": cats,
    }


def donation_out(d, now=None, match=None):
    now = now or utcnow()
    h = hours_left(d.expiry_time, now)
    status = "expired" if d.status == "posted" and h <= 0 else d.status
    total_h = (d.expiry_time - d.created_at).total_seconds() / 3600 or 1
    live = status in LIVE
    return {
        "id": d.id, "food_name": d.food_name, "category": d.category,
        "quantity_kg": d.quantity_kg, "description": d.description or "",
        "expiry_time": d.expiry_time, "created_at": d.created_at,
        "latitude": d.latitude, "longitude": d.longitude, "status": status,
        "donor_id": d.donor_id, "donor_name": d.donor.organization or d.donor.name,
        "claimed_by_id": d.claimed_by_id,
        "claimed_by_name": (d.claimed_by.organization or d.claimed_by.name) if d.claimed_by else None,
        "hours_left": round(h, 2),
        "shelf_life_pct": round(max(0.0, min(1.0, h / total_h)), 3) if live else 0.0,
        "urgency": urgency_level(h) if live else "done",
        "match": match,
    }